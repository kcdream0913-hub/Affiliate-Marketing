"""Bandit-Allocator (component 10): Thompson Sampling over offer×creative arms.

Posterior: Beta(α, β) on conversion rate; α += conversions, β += (clicks − conversions).
Allocation: sample each live arm's posterior, weight ∝ sample × value_per_conversion
(refund-adjusted commission) → posting-cadence weights.

GUARDRAILS (ARCHITECTURE.md + risk register):
- Forced exploration floor: an arm may NOT be killed until it has
  ≥ FLOOR_CLICKS clicks OR ≥ FLOOR_CONVERSIONS conversions.
- Never kill on EPC alone before the floor; refund lag means kills use
  refund-adjusted revenue-per-1k-views (discount by category refund rate).
- Non-stationarity hedge: optional decay keeps old evidence from dominating.

Stdlib-only (random.betavariate); persisted via the bandit_state table.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

FLOOR_CLICKS = 1000
FLOOR_CONVERSIONS = 30
DEFAULT_RPM_KILL_THRESHOLD = 5.0   # $/1k views breakeven — tune with real data
DECAY = 0.99                       # per-update evidence decay (1.0 = off)


@dataclass
class Arm:
    arm_id: str                    # "offer_id:creative_id"
    alpha: float = 1.0             # Beta prior α=β=1 (uniform)
    beta: float = 1.0
    clicks: int = 0
    conversions: int = 0
    killed: bool = False
    # economics for value-weighting + kill decisions
    commission_per_conversion: float = 0.0   # $ net expected
    refund_rate: float = 0.10                # category prior until 'api' data
    views: int = 0
    revenue: float = 0.0                     # gross attributed $

    @property
    def past_floor(self) -> bool:
        return self.clicks >= FLOOR_CLICKS or self.conversions >= FLOOR_CONVERSIONS

    @property
    def refund_adjusted_rpm(self) -> Optional[float]:
        """$ per 1k views, discounted by refund rate. None if no view data."""
        if self.views <= 0:
            return None
        return (self.revenue * (1.0 - self.refund_rate)) / self.views * 1000.0

    def record(self, clicks: int = 0, conversions: int = 0, views: int = 0,
               revenue: float = 0.0, decay: float = DECAY) -> None:
        if conversions > clicks:
            raise ValueError("conversions cannot exceed clicks in an update")
        if decay < 1.0:
            self.alpha = 1.0 + (self.alpha - 1.0) * decay
            self.beta = 1.0 + (self.beta - 1.0) * decay
        self.alpha += conversions
        self.beta += max(0, clicks - conversions)
        self.clicks += clicks
        self.conversions += conversions
        self.views += views
        self.revenue += revenue

    def sample(self, rng: random.Random) -> float:
        return rng.betavariate(self.alpha, self.beta)


@dataclass
class BanditState:
    arms: Dict[str, Arm] = field(default_factory=dict)
    rpm_kill_threshold: float = DEFAULT_RPM_KILL_THRESHOLD

    def add_arm(self, arm: Arm) -> None:
        self.arms[arm.arm_id] = arm

    # ---------------- kill logic (floor-guarded) ----------------
    def evaluate_kills(self) -> List[str]:
        """Returns arm_ids newly killed. NEVER kills below the exploration floor.
        Weekly human review of kills is a separate checkpoint (risk register)."""
        newly = []
        for arm in self.arms.values():
            if arm.killed or not arm.past_floor:
                continue
            rpm = arm.refund_adjusted_rpm
            if rpm is not None and rpm < self.rpm_kill_threshold:
                arm.killed = True
                newly.append(arm.arm_id)
        return newly

    def hard_kill(self, arm_id: str, reason: str = "") -> None:
        """Bypass floor only for external hard kills (refund>15%, network flag,
        compliance HIGH) — mirrors Offer-Scoring kill flags, not performance."""
        if arm_id in self.arms:
            self.arms[arm_id].killed = True

    # ---------------- allocation ----------------
    def allocate(self, seed: Optional[int] = None, samples: int = 200) -> Dict[str, float]:
        """Posting-cadence weights over live arms (sum = 1.0).

        Averages `samples` Thompson draws × value-per-conversion so weights are
        stable enough for a daily cadence plan while preserving exploration.
        New arms (α=β=1) sample wide → guaranteed exploration share.
        """
        rng = random.Random(seed)
        live = [a for a in self.arms.values() if not a.killed]
        if not live:
            return {}
        scores = {a.arm_id: 0.0 for a in live}
        for _ in range(samples):
            for a in live:
                value = a.commission_per_conversion * (1.0 - a.refund_rate) or 1.0
                scores[a.arm_id] += a.sample(rng) * value
        total = sum(scores.values()) or 1.0
        return {k: v / total for k, v in scores.items()}

    def cadence_plan(self, posts_per_day: int, seed: Optional[int] = None) -> Dict[str, int]:
        """Integer posts/day per arm honoring the warming cap upstream."""
        weights = self.allocate(seed=seed)
        plan = {k: int(round(w * posts_per_day)) for k, w in weights.items()}
        # guarantee at least the top arm posts if rounding zeroed everything
        if plan and sum(plan.values()) == 0:
            top = max(weights, key=weights.get)
            plan[top] = 1
        return plan

    # ---------------- persistence shapes ----------------
    def to_rows(self) -> List[dict]:
        return [{
            "arm_id": a.arm_id, "alpha": a.alpha, "beta": a.beta,
            "clicks": a.clicks, "conversions": a.conversions, "killed": a.killed,
        } for a in self.arms.values()]

    @classmethod
    def from_rows(cls, rows: List[dict], **kw) -> "BanditState":
        st = cls(**kw)
        for r in rows:
            st.add_arm(Arm(
                arm_id=r["arm_id"], alpha=float(r.get("alpha", 1)), beta=float(r.get("beta", 1)),
                clicks=int(r.get("clicks", 0)), conversions=int(r.get("conversions", 0)),
                killed=bool(r.get("killed", False)),
                commission_per_conversion=float(r.get("commission_per_conversion", 0.0)),
                refund_rate=float(r.get("refund_rate", 0.10)),
            ))
        return st

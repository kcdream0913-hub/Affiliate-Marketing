"""Offer-Scoring agent (component 8): rubric as code.

score = 0.30·EPC_norm + 0.20·refund_score + 0.15·commission_norm
      + 0.15·demo_coherence + 0.10·demand_velocity + 0.10·payout_reliability

KILL CRITERIA (any one → reject regardless of score):
  refund_rate > 15% | gravity < 8 (CB) | HIGH claim-risk | Net-90/holdback>60d
  | cookie < 14 days | commission resets on downgrade (SaaS)

Every input field carries provenance: feed | scrape | api | manual.
Live offers re-score with actual EPC/refunds from earnings APIs ('api'
provenance overrides feed/scrape estimates).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

WEIGHTS = {
    "epc": 0.30,
    "refund": 0.20,
    "commission": 0.15,
    "demo_coherence": 0.15,
    "demand_velocity": 0.10,
    "payout_reliability": 0.10,
}

# Normalization benchmarks (tune with own data; docs/research/01 §1.2)
EPC_BENCHMARK = 1.00          # $1 EPC baseline aspiration
COMMISSION_BENCHMARK = 50.0   # $/conversion incl. rebills considered "full marks"

REFUND_KILL = 0.15
GRAVITY_MIN = 8.0
GRAVITY_MAX = 150.0           # liveness band upper bound (saturation guard)
COOKIE_MIN_DAYS = 14
BAD_PAYOUT_TERMS = {"net-90", "net90"}
HOLDBACK_MAX_DAYS = 60


@dataclass
class OfferInput:
    name: str
    network: str                                   # clickbank|digistore24|partnerstack|impact|rewardful
    category: str = ""
    epc: Optional[float] = None                    # $/click
    refund_rate: Optional[float] = None            # 0-1
    commission_per_conversion: Optional[float] = None  # $ incl rebills/upsells
    demo_coherence: float = 0.5                    # 0-1, manual/LLM judgment
    demand_velocity: float = 0.5                   # 0-1, trend slope normalized
    payout_reliability: float = 0.5                # 0-1, manual constant
    gravity: Optional[float] = None                # ClickBank only
    cookie_days: Optional[int] = None
    payout_terms: str = ""                         # 'NET15','NET-90',...
    holdback_days: int = 0
    claim_risk: str = "LOW"                        # from Compliance-Gate on draft angle
    commission_resets_on_downgrade: bool = False   # SaaS
    has_sales_history: bool = True                 # DS24: no history = kill
    provenance: dict = field(default_factory=dict)


@dataclass
class ScoreResult:
    score: float                # 0-100; 0 if killed
    killed: bool
    kill_flags: List[str]
    components: dict
    provenance: dict

    def to_offer_update(self) -> dict:
        return {
            "rubric_score": self.score,
            "kill_flags": self.kill_flags,
            "status": "killed" if self.killed else "candidate",
            "source": self.provenance,
        }


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def kill_flags(o: OfferInput) -> List[str]:
    flags: List[str] = []
    if o.refund_rate is not None and o.refund_rate > REFUND_KILL:
        flags.append("refund>15%")
    if o.network == "clickbank":
        if o.gravity is None or o.gravity < GRAVITY_MIN:
            flags.append("gravity<8")
        elif o.gravity > GRAVITY_MAX:
            flags.append("gravity>150_saturated")
    if o.network == "digistore24" and not o.has_sales_history:
        flags.append("no_sales_history")
    if o.claim_risk.upper() == "HIGH":
        flags.append("claim_risk_HIGH")
    if o.payout_terms.replace(" ", "").lower() in BAD_PAYOUT_TERMS:
        flags.append("net90_payout")
    if o.holdback_days > HOLDBACK_MAX_DAYS:
        flags.append("holdback>60d")
    if o.cookie_days is not None and o.cookie_days < COOKIE_MIN_DAYS:
        flags.append("cookie<14d")
    if o.commission_resets_on_downgrade:
        flags.append("commission_resets_on_downgrade")
    return flags


def score_offer(o: OfferInput) -> ScoreResult:
    flags = kill_flags(o)
    components = {
        # Missing data scores conservatively at 0 — incentivizes filling provenance.
        "epc": _clamp((o.epc or 0.0) / EPC_BENCHMARK),
        "refund": _clamp(1.0 - (o.refund_rate if o.refund_rate is not None else 0.10) / REFUND_KILL),
        "commission": _clamp((o.commission_per_conversion or 0.0) / COMMISSION_BENCHMARK),
        "demo_coherence": _clamp(o.demo_coherence),
        "demand_velocity": _clamp(o.demand_velocity),
        "payout_reliability": _clamp(o.payout_reliability),
    }
    raw = sum(WEIGHTS[k] * v for k, v in components.items())
    killed = bool(flags)
    return ScoreResult(
        score=0.0 if killed else round(raw * 100, 1),
        killed=killed,
        kill_flags=flags,
        components=components,
        provenance=o.provenance,
    )


def rank_candidates(offers: List[OfferInput], top_n: int = 10) -> List[tuple]:
    """[(name, ScoreResult)] — survivors ranked by score desc."""
    scored = [(o.name, score_offer(o)) for o in offers]
    survivors = [(n, r) for n, r in scored if not r.killed]
    survivors.sort(key=lambda t: t[1].score, reverse=True)
    return survivors[:top_n]

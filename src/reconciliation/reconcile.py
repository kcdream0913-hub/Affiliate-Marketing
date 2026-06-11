"""Reconcile attributed conversions (our postbacks) vs network-truth earnings.

Rule (ARCHITECTURE.md Rec. 6): if network earnings exceed tracked conversions
by > LEAKAGE_THRESHOLD (15%), flag attribution leakage and FREEZE bandit kill
decisions until resolved.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

LEAKAGE_THRESHOLD = 0.15


@dataclass
class ReconciliationReport:
    period: str
    by_network: Dict[str, dict] = field(default_factory=dict)
    leakage_flags: List[str] = field(default_factory=list)
    freeze_bandit_kills: bool = False

    def summary(self) -> str:
        lines = [f"Reconciliation {self.period}:"]
        for net, d in sorted(self.by_network.items()):
            lines.append(
                f"  {net}: tracked ${d['tracked']:.2f} vs network ${d['network']:.2f} "
                f"(gap {d['gap_pct']:+.1%}){' ⚠ LEAKAGE' if net in self.leakage_flags else ''}"
            )
        if self.freeze_bandit_kills:
            lines.append("  ACTION: bandit kill decisions FROZEN until leakage resolved.")
        return "\n".join(lines)


def reconcile(conversions: List[dict], earnings: List[dict], period: str,
              threshold: float = LEAKAGE_THRESHOLD) -> ReconciliationReport:
    """conversions: rows from our postback table (commission, network, is_refund).
    earnings: normalized poller rows (commission, refunds, network)."""
    tracked: Dict[str, float] = {}
    for c in conversions:
        if c.get("is_refund"):
            continue
        net = c.get("network", "?")
        tracked[net] = tracked.get(net, 0.0) + float(c.get("commission") or 0)

    network_truth: Dict[str, float] = {}
    for e in earnings:
        net = e.get("network", "?")
        network_truth[net] = network_truth.get(net, 0.0) + float(e.get("commission") or 0) + float(e.get("rebills") or 0)

    report = ReconciliationReport(period=period)
    for net in sorted(set(tracked) | set(network_truth)):
        t, n = tracked.get(net, 0.0), network_truth.get(net, 0.0)
        gap_pct = ((n - t) / n) if n > 0 else 0.0
        report.by_network[net] = {"tracked": t, "network": n, "gap_pct": gap_pct}
        if n > 0 and gap_pct > threshold:
            report.leakage_flags.append(net)
    report.freeze_bandit_kills = bool(report.leakage_flags)
    return report

"""Compliance-Gate: tiered FTC claim-risk classifier.

Pipeline position: runs FIRST, before any asset spend (images/video/posting).
Verdicts:
  HIGH   -> hard block, human review. Never auto-soften.
  MEDIUM -> allowed only after softening + forced disclosure (Script agent retries).
  LOW    -> pass with standard disclosure.

Stdlib-only by design (portable to n8n Code node / VPS). A semantic LLM pass can
be layered on top in Sprint 3; this lexicon layer is the hard floor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .rules import (
    AI_LABEL_TEXT,
    ESCALATED_CATEGORIES,
    FTC_DISCLOSURE_ACCEPTED,
    FTC_DISCLOSURE_INSUFFICIENT,
    HIGH_RULES,
    MEDIUM_RULES,
)

VERDICT_HIGH = "HIGH"
VERDICT_MEDIUM = "MEDIUM"
VERDICT_LOW = "LOW"


@dataclass
class ComplianceResult:
    verdict: str
    blocked: bool
    matched_rules: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    escalated: bool = False

    def to_log_row(self, video_id: Optional[str] = None, stage: str = "compliance_gate") -> dict:
        """Row shape for the compliance_logs table."""
        return {
            "video_id": video_id,
            "stage": stage,
            "verdict": "BLOCK" if self.blocked else self.verdict,
            "matched_rules": self.matched_rules,
            "notes": "; ".join(self.notes),
        }


def classify_text(text: str, offer_category: str = "") -> ComplianceResult:
    """Classify a script/caption for FTC claim risk.

    offer_category: offers.category — health/finance/income categories escalate
    MEDIUM verdicts to HIGH (FTC active-enforcement priorities).
    """
    matched_high = [rid for rid, rx in HIGH_RULES if rx.search(text)]
    matched_medium = [rid for rid, rx in MEDIUM_RULES if rx.search(text)]
    escalated_cat = offer_category.strip().lower() in ESCALATED_CATEGORIES

    if matched_high:
        return ComplianceResult(
            verdict=VERDICT_HIGH,
            blocked=True,
            matched_rules=matched_high,
            notes=["HIGH-risk claim: hard block, route to human review."],
            escalated=escalated_cat,
        )

    if matched_medium:
        if escalated_cat:
            return ComplianceResult(
                verdict=VERDICT_HIGH,
                blocked=True,
                matched_rules=matched_medium,
                notes=[f"MEDIUM claims escalated to HIGH: category '{offer_category}' is an FTC enforcement priority."],
                escalated=True,
            )
        return ComplianceResult(
            verdict=VERDICT_MEDIUM,
            blocked=False,
            matched_rules=matched_medium,
            notes=["MEDIUM: soften phrasing + force disclosure before proceeding."],
        )

    return ComplianceResult(verdict=VERDICT_LOW, blocked=False, notes=["LOW: standard disclosure required."])


def check_disclosure(caption: str) -> ComplianceResult:
    """Enforce FTC disclosure in the caption. Caption must START with #ad
    (or contain an accepted phrase); 'affiliate link'-style wording alone is
    insufficient per FTC guidance."""
    notes: List[str] = []
    matched: List[str] = []
    ok = bool(FTC_DISCLOSURE_ACCEPTED.search(caption))

    if not ok:
        matched.append("missing_ftc_disclosure")
        notes.append("Caption lacks accepted disclosure ('#ad' at start / 'paid link' / 'sponsored').")
    if FTC_DISCLOSURE_INSUFFICIENT.search(caption) and not ok:
        matched.append("insufficient_disclosure_wording")
        notes.append("'affiliate link'-style wording is insufficient per FTC.")

    if matched:
        return ComplianceResult(verdict=VERDICT_HIGH, blocked=True, matched_rules=matched, notes=notes)
    return ComplianceResult(verdict=VERDICT_LOW, blocked=False, notes=["Disclosure OK."])


def check_ai_labeling(
    *,
    platform_toggle_set: bool,
    onscreen_text: str,
    c2pa_present: bool,
    is_realistic_ai_media: bool = True,
) -> ComplianceResult:
    """AI-disclosure auto-labeler checks (component 12).

    Required for realistic AI media (TikTok + Meta policy): platform toggle ON,
    visible on-screen label, C2PA metadata never stripped. AI-assisted text alone
    is exempt (is_realistic_ai_media=False).
    """
    if not is_realistic_ai_media:
        return ComplianceResult(verdict=VERDICT_LOW, blocked=False, notes=["Text-only AI assist: labeling exempt."])

    matched: List[str] = []
    notes: List[str] = []
    if not platform_toggle_set:
        matched.append("ai_toggle_off")
        notes.append("Platform AI self-disclosure toggle must be ON.")
    if AI_LABEL_TEXT.lower() not in onscreen_text.lower():
        matched.append("missing_onscreen_ai_label")
        notes.append(f"Visible on-screen '{AI_LABEL_TEXT}' label required.")
    if not c2pa_present:
        matched.append("c2pa_stripped")
        notes.append("C2PA metadata missing — never strip Content Credentials.")

    if matched:
        return ComplianceResult(verdict=VERDICT_HIGH, blocked=True, matched_rules=matched, notes=notes)
    return ComplianceResult(verdict=VERDICT_LOW, blocked=False, notes=["AI labeling OK."])


def gate(
    script: str,
    caption: str,
    offer_category: str = "",
    *,
    platform_toggle_set: bool = False,
    onscreen_text: str = "",
    c2pa_present: bool = False,
    is_realistic_ai_media: bool = True,
) -> ComplianceResult:
    """Full pre-post gate: claim risk (script + caption) + FTC disclosure + AI labeling.

    Returns the worst result; blocked=True halts the pipeline.
    """
    results = [
        classify_text(script, offer_category),
        classify_text(caption, offer_category),
        check_disclosure(caption),
        check_ai_labeling(
            platform_toggle_set=platform_toggle_set,
            onscreen_text=onscreen_text,
            c2pa_present=c2pa_present,
            is_realistic_ai_media=is_realistic_ai_media,
        ),
    ]
    order = {VERDICT_HIGH: 2, VERDICT_MEDIUM: 1, VERDICT_LOW: 0}
    worst = max(results, key=lambda r: (r.blocked, order[r.verdict]))
    combined = ComplianceResult(
        verdict=worst.verdict,
        blocked=any(r.blocked for r in results),
        matched_rules=[rid for r in results for rid in r.matched_rules],
        notes=[n for r in results for n in r.notes],
        escalated=any(r.escalated for r in results),
    )
    return combined

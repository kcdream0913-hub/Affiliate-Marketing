"""Tiered FTC claim-risk rule tables for the Compliance-Gate.

Design rule (ARCHITECTURE.md): HIGH patterns are intentionally over-broad —
zero false-negatives prioritized over false-positives. Anything HIGH is
hard-blocked and routed to human review; never auto-softened.

Each rule: (rule_id, compiled_regex). Patterns are case-insensitive.
"""
from __future__ import annotations

import re
from typing import List, Tuple

_flags = re.IGNORECASE


def _c(pattern: str):
    return re.compile(pattern, _flags)


# HIGH — hard block (FTC enforcement priorities + platform-ban triggers)
HIGH_RULES: List[Tuple[str, "re.Pattern"]] = [
    ("disease_cure", _c(r"\b(cure[sd]?|heal(s|ed|ing)?|reverse[sd]?|eliminat\w+)\b.{0,60}\b(diabetes|cancer|arthritis|anxiety|depression|adhd|disease|illness|infection|inflammation|pain|insomnia|hypertension|alzheimer'?s?)\b")),
    ("disease_treat", _c(r"\b(treat[s]?|prevent[s]?|fight[s]?)\b.{0,40}\b(diabetes|cancer|arthritis|disease|covid|infection|alzheimer'?s?|dementia)\b")),
    ("clinical_unbacked", _c(r"\b(clinically proven|doctors? (hate|recommend|swear)|studies show|scientifically proven|fda.approved)\b")),
    ("weight_loss_specific", _c(r"\b(lose|lost|shed|drop(ped)?|melt(s|ed)?)\b.{0,25}\b\d+\s*(lbs?|pounds?|kgs?|kilos?|inches)\b")),
    ("before_after", _c(r"\b(before\s*(and|&|/)?\s*after|transformation photo|body transformation)\b")),
    ("income_amount", _c(r"[$€£]\s?\d[\d,.]*\s*k?\s*(/|per\s*|a\s*)?(day|week|month|year|hr|hour)s?\b")),
    ("income_promise", _c(r"\b(make|earn|generate|pull in)\b.{0,30}\b(money|income|[$€£]\s?\d|passive income|six figures?|7.figures?)\b")),
    ("quit_job", _c(r"\b(quit (your|my) job|fire your boss|financial freedom guaranteed|get rich)\b")),
    ("guarantee", _c(r"\b(guaranteed? (results?|success|to work|weight loss|income)|100% (works|effective|guaranteed)|risk.free results)\b")),
    ("no_effort_outcome", _c(r"\b(without (diet|exercise|work(ing)?|effort)|while you sleep|overnight (results|success))\b")),
]

# MEDIUM — allow only with softening + forced disclosure context
MEDIUM_RULES: List[Tuple[str, "re.Pattern"]] = [
    ("structure_function", _c(r"\b(supports?|boosts?|promotes?|enhances?|improves?)\b.{0,30}\b(energy|focus|immunity|immune|metabolism|sleep|mood|digestion|skin|hair|recovery)\b")),
    ("testimonial", _c(r"\b(it (changed|saved) my life|i (couldn'?t|can'?t) believe|best (purchase|decision)\b.{0,10}ever)\b")),
    ("urgency_scarcity", _c(r"\b(only \d+ left|selling out|won'?t last|act now|limited time)\b")),
    ("superlative_absolute", _c(r"\b(the only \w+ you('?ll)? ever need|nothing else works|better than (everything|anything))\b")),
    ("implied_health_outcome", _c(r"\b(fall asleep faster|wake up refreshed|all.day energy|melt stress away)\b")),
]

# Offer categories that escalate scrutiny (FTC active enforcement priorities)
ESCALATED_CATEGORIES = {
    "health", "supplements", "weight-loss", "fitness", "medical",
    "finance", "income", "make-money", "biz-opp", "investing", "crypto",
}

# FTC: clear, conspicuous, adjacent. '#ad' / 'paid link' acceptable;
# 'affiliate link' / 'commissionable link' insufficient.
FTC_DISCLOSURE_ACCEPTED = _c(r"^\s*#ad\b|\b(paid link|paid partnership|sponsored)\b")
FTC_DISCLOSURE_INSUFFICIENT = _c(r"\b(affiliate link|commissionable link|aff link)\b")

# Required AI on-screen label text (Video-Assembly burns this in)
AI_LABEL_TEXT = "AI-generated"

# FTC caption disclosure templates (caption MUST start with #ad)
DISCLOSURE_TEMPLATES = {
    "caption_prefix": "#ad ",
    "caption_suffix": " | Paid link in bio",
    "audio_line": "Quick note: this is a paid recommendation.",
    "onscreen": "#ad · AI-generated",
}

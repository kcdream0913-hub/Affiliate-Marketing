"""Sprint 0 gate: HIGH/MEDIUM/LOW corpus. Acceptance: ZERO HIGH false-negatives."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.compliance import (  # noqa: E402
    VERDICT_HIGH,
    VERDICT_LOW,
    VERDICT_MEDIUM,
    check_ai_labeling,
    check_disclosure,
    classify_text,
    gate,
)

# --- HIGH corpus: every one MUST block (zero false-negatives) ---------------
HIGH_CORPUS = [
    "This tea cures diabetes in 30 days",
    "Heal your chronic pain naturally with this device",
    "Clinically proven to reverse inflammation",
    "She lost 20 lbs in two weeks with this",
    "Insane before and after results!",
    "Make $10,000/month on autopilot",
    "Earn passive income while you sleep",
    "Quit your job with this side hustle",
    "Guaranteed results or your money back",
    "Lose weight without diet or exercise",
    "Doctors hate this one trick",
    "$500 a day with this app",
]

# --- MEDIUM corpus: flagged but not blocked (neutral category) ---------------
MEDIUM_CORPUS = [
    "This supplement supports energy and focus",
    "It boosts metabolism naturally",
    "Honestly the best purchase I've ever made",
    "Only 50 left in stock, selling out fast",
    "Helps you fall asleep faster",
]

# --- LOW corpus: must pass clean ---------------------------------------------
LOW_CORPUS = [
    "This phone stand folds flat and fits in your pocket",
    "I love the matte finish on this notebook",
    "It comes in three colors and ships free",
    "Here's how I organize my desk in under a minute",
    "The app has a built-in dark mode",
]


def test_high_corpus_zero_false_negatives():
    misses = []
    for text in HIGH_CORPUS:
        r = classify_text(text)
        if r.verdict != VERDICT_HIGH or not r.blocked:
            misses.append((text, r.verdict))
    assert not misses, f"HIGH false-negatives (account-death risk): {misses}"


def test_medium_corpus_flagged_not_blocked():
    for text in MEDIUM_CORPUS:
        r = classify_text(text)
        assert r.verdict == VERDICT_MEDIUM, f"{text!r} -> {r.verdict}"
        assert not r.blocked


def test_low_corpus_passes():
    for text in LOW_CORPUS:
        r = classify_text(text)
        assert r.verdict == VERDICT_LOW, f"{text!r} -> {r.verdict} ({r.matched_rules})"
        assert not r.blocked


def test_category_escalation_medium_to_high():
    r = classify_text("This supplement supports energy and focus", offer_category="supplements")
    assert r.verdict == VERDICT_HIGH and r.blocked and r.escalated


def test_category_escalation_only_for_priority_categories():
    r = classify_text("This supplement supports energy and focus", offer_category="home-office")
    assert r.verdict == VERDICT_MEDIUM and not r.blocked


def test_disclosure_accepts_ad_prefix():
    assert not check_disclosure("#ad This desk organizer changed my setup").blocked


def test_disclosure_blocks_missing():
    r = check_disclosure("Check the link in my bio!")
    assert r.blocked and "missing_ftc_disclosure" in r.matched_rules


def test_disclosure_blocks_insufficient_wording():
    r = check_disclosure("affiliate link in bio")
    assert r.blocked


def test_ai_labeling_all_required():
    r = check_ai_labeling(platform_toggle_set=True, onscreen_text="#ad · AI-generated", c2pa_present=True)
    assert not r.blocked


def test_ai_labeling_blocks_stripped_c2pa():
    r = check_ai_labeling(platform_toggle_set=True, onscreen_text="AI-generated", c2pa_present=False)
    assert r.blocked and "c2pa_stripped" in r.matched_rules


def test_ai_labeling_text_only_exempt():
    r = check_ai_labeling(platform_toggle_set=False, onscreen_text="", c2pa_present=False, is_realistic_ai_media=False)
    assert not r.blocked


def test_full_gate_clean_creative_passes():
    r = gate(
        script="Here's how I organize my desk in under a minute with this tray.",
        caption="#ad Desk tray that folds flat | Paid link in bio",
        offer_category="home-office",
        platform_toggle_set=True,
        onscreen_text="#ad · AI-generated",
        c2pa_present=True,
    )
    assert not r.blocked and r.verdict == VERDICT_LOW


def test_full_gate_blocks_income_claim_even_with_disclosure():
    r = gate(
        script="Make $10,000/month with this app",
        caption="#ad link in bio",
        platform_toggle_set=True,
        onscreen_text="#ad · AI-generated",
        c2pa_present=True,
    )
    assert r.blocked and r.verdict == VERDICT_HIGH


def test_gate_log_row_shape():
    r = classify_text("This tea cures diabetes")
    row = r.to_log_row(video_id="00000000-0000-0000-0000-000000000000")
    assert row["verdict"] == "BLOCK" and row["stage"] == "compliance_gate"

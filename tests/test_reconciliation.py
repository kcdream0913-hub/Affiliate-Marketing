"""Sprint 5 gate: mocked poller integration + reconciliation/leakage fixtures."""
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.reconciliation import (  # noqa: E402
    import_amazon_csv,
    poll_clickbank,
    poll_digistore24,
    poll_impact,
    poll_partnerstack,
    reconcile,
)

START, END = date(2026, 6, 1), date(2026, 6, 7)


def test_clickbank_poller_normalizes():
    def fake(url, headers):
        assert "analytics/affiliate/subid" in url and ":" in headers["Authorization"]
        return json.dumps({"rows": [{"vendor": "sleepwell", "trackingId": "abc123",
                                     "saleAmount": 87.20, "refundAmount": 12.0, "rebillAmount": 5.0}]})
    rows = poll_clickbank("DEV", "CLERK", START, END, fetch_fn=fake)
    assert rows[0]["network"] == "clickbank" and rows[0]["subid"] == "abc123"
    assert rows[0]["commission"] == 87.20 and rows[0]["refunds"] == 12.0


def test_ds24_poller_splits_refunds():
    def fake(url, headers):
        assert "listTransactions" in url and headers["X-DS-API-KEY"] == "KEY"
        return json.dumps({"data": {"transaction_list": [
            {"transaction_type": "payment", "product_id": 12345, "sid1": "vidA",
             "affiliate_amount": 24.95, "transaction_date": "2026-06-03 10:00"},
            {"transaction_type": "refund", "product_id": 12345, "sid1": "vidA",
             "affiliate_amount": 24.95, "transaction_date": "2026-06-05 10:00"},
        ]}})
    rows = poll_digistore24("KEY", START, END, fetch_fn=fake)
    assert rows[0]["commission"] == 24.95 and rows[0]["refunds"] == 0.0
    assert rows[1]["commission"] == 0.0 and rows[1]["refunds"] == 24.95
    assert rows[0]["period"] == "2026-06-03"


def test_impact_range_cap_enforced():
    try:
        poll_impact("SID", "TOK", date(2026, 1, 1), date(2026, 6, 1), fetch_fn=lambda u, h: "{}")
        assert False
    except ValueError:
        pass


def test_impact_poller_reversed_state():
    def fake(url, headers):
        assert headers["Authorization"].startswith("Basic ")
        return json.dumps({"Actions": [
            {"CampaignId": 9, "SubId1": "vidB", "Payout": "14.10", "State": "APPROVED", "EventDate": "2026-06-02T01:00:00Z"},
            {"CampaignId": 9, "SubId1": "vidB", "Payout": "14.10", "State": "REVERSED", "EventDate": "2026-06-04T01:00:00Z"},
        ]})
    rows = poll_impact("SID", "TOK", START, END, fetch_fn=fake)
    assert rows[0]["commission"] == 14.10 and rows[1]["refunds"] == 14.10


def test_partnerstack_cents_and_recurring():
    def fake(url, headers):
        assert headers["Authorization"] == "Bearer PSKEY"
        return json.dumps({"data": {"items": [
            {"amount": 1410, "reward_type": "recurring", "reversed_at": None,
             "group": {"slug": "saas-tool"}, "metadata": {"subid": "vidC"}},
        ]}})
    rows = poll_partnerstack("PSKEY", START, END, fetch_fn=fake)
    assert rows[0]["commission"] == 14.10 and rows[0]["rebills"] == 14.10
    assert rows[0]["offer_external_id"] == "saas-tool"


def test_amazon_csv_import():
    csv_text = "Tracking ID,ASIN,Product Title,Items Shipped,Ad Fees($)\nkc-20,B0TEST,Desk Tray,3,4.52\n"
    rows = import_amazon_csv(csv_text, period="2026-06-07")
    assert rows[0]["network"] == "amazon" and rows[0]["subid"] == "kc-20"
    assert rows[0]["commission"] == 4.52 and rows[0]["offer_external_id"] == "B0TEST"


def test_reconcile_clean_no_flags():
    convs = [{"network": "digistore24", "commission": 100.0, "is_refund": False}]
    earns = [{"network": "digistore24", "commission": 105.0, "rebills": 0.0}]
    rep = reconcile(convs, earns, "2026-W23")
    assert rep.leakage_flags == [] and not rep.freeze_bandit_kills
    assert abs(rep.by_network["digistore24"]["gap_pct"] - 0.0476) < 0.001


def test_reconcile_flags_leakage_and_freezes_kills():
    convs = [{"network": "clickbank", "commission": 50.0, "is_refund": False}]
    earns = [{"network": "clickbank", "commission": 80.0, "rebills": 0.0}]
    rep = reconcile(convs, earns, "2026-W23")
    assert rep.leakage_flags == ["clickbank"] and rep.freeze_bandit_kills
    assert "LEAKAGE" in rep.summary() and "FROZEN" in rep.summary()


def test_reconcile_ignores_refund_conversions_in_tracked():
    convs = [
        {"network": "clickbank", "commission": 50.0, "is_refund": False},
        {"network": "clickbank", "commission": 50.0, "is_refund": True},
    ]
    earns = [{"network": "clickbank", "commission": 55.0, "rebills": 0.0}]
    rep = reconcile(convs, earns, "2026-W23")
    assert rep.by_network["clickbank"]["tracked"] == 50.0

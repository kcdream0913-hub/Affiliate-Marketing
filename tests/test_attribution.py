"""Sprint 1 gate: subID round-trip, redirect builders, postback parsing + signatures."""
import hashlib
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.attribution import (  # noqa: E402
    build_redirect,
    clickbank_hoplink,
    conversion_row_to_db,
    digistore24_link,
    ds24_signature_valid,
    generic_sublink,
    hash_ip,
    parse_clickbank,
    parse_ds24,
    video_subid,
)

VID = "0b6c9c4e-8a1d-4f3a-9d2e-7c5b4a3f2e1d"


def test_subid_deterministic_and_safe():
    s1, s2 = video_subid(VID), video_subid(VID)
    assert s1 == s2 and len(s1) <= 24 and s1.isalnum()


def test_subid_rejects_junk():
    try:
        video_subid("not-a-uuid")
        assert False, "should raise"
    except ValueError:
        pass


def test_clickbank_hoplink_carries_tid():
    url = clickbank_hoplink("kcnick", "vendorx", VID)
    assert url.startswith("https://kcnick.vendorx.hop.clickbank.net/?tid=")
    assert video_subid(VID) in url


def test_ds24_link_carries_sid1_and_cid():
    url = build_redirect("digistore24", VID, click_id="abc123", product_id="12345", affiliate_id="KCaff")
    assert "checkout-ds24.com/redir/12345/KCaff" in url
    assert f"sid1={video_subid(VID)}" in url and "cid=abc123" in url


def test_generic_sublink_appends_param():
    url = generic_sublink("https://partner.example.com/r/kc?src=ps", VID)
    assert url.endswith(f"subid={video_subid(VID)}") and "&" in url


def test_build_redirect_unknown_network_raises():
    try:
        build_redirect("amazonia", VID)
        assert False
    except ValueError:
        pass


def test_ip_hash_salted_no_raw_ip():
    h = hash_ip("203.0.113.7", "salt1")
    assert "203" not in h and h != hash_ip("203.0.113.7", "salt2")


# --- Digistore24 postback -----------------------------------------------------
def _ds24_params(passphrase="pp"):
    params = {
        "event": "on_payment",
        "order_id": "ABC-123",
        "amount_brutto": "49.90",
        "amount_affiliate": "24.95",
        "sid1": video_subid(VID),
        "cid": "click123",
    }
    keys = sorted(k for k in params if params[k] not in (None, "", "false"))
    payload = "".join(f"{k}={params[k]}{passphrase}" for k in keys)
    params["sha_sign"] = hashlib.sha512(payload.encode()).hexdigest().upper()
    return params


def test_ds24_signature_roundtrip():
    p = _ds24_params()
    assert ds24_signature_valid(p, "pp")
    assert not ds24_signature_valid(p, "wrong")


def test_ds24_parse_sale_money_in_cents():
    row = parse_ds24(_ds24_params())
    assert row["type"] == "sale" and not row["is_refund"]
    assert row["gross_cents"] == 4990 and row["commission_cents"] == 2495
    assert row["subid"] == video_subid(VID) and row["click_id"] == "click123"


def test_ds24_parse_refund():
    p = _ds24_params()
    p["event"] = "on_refund"
    row = parse_ds24(p)
    assert row["is_refund"] and row["type"] == "refund"


# --- ClickBank postback ---------------------------------------------------------
CB_SALE = {
    "transactionType": "SALE",
    "receipt": "R-XYZ",
    "totalOrderAmount": 37.00,
    "trackingCodes": [video_subid(VID)],
    "lineItems": [{"accountAmount": 18.50}],
}


def test_cb_parse_sale():
    row = parse_clickbank(CB_SALE)
    assert row["type"] == "sale" and row["subid"] == video_subid(VID)
    assert row["gross_cents"] == 3700 and row["commission_cents"] == 1850


def test_cb_parse_refund():
    n = dict(CB_SALE, transactionType="RFND")
    row = parse_clickbank(n)
    assert row["is_refund"] and row["type"] == "refund"


def test_cb_rebill():
    n = dict(CB_SALE, transactionType="BILL")
    assert parse_clickbank(n)["type"] == "rebill"


def test_conversion_db_row_shape():
    db = conversion_row_to_db(parse_ds24(_ds24_params()), video_id=VID)
    assert db["gross"] == 49.90 and db["commission"] == 24.95
    assert db["network"] == "digistore24" and db["video_id"] == VID
    assert str(uuid.UUID(db["video_id"])) == VID

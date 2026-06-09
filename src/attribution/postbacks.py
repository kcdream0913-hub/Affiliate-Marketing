"""S2S postback parsers → rows for the conversions table.

Digistore24: form-encoded IPN to /postback/digistore24 (sha512 signature).
ClickBank:  INS v6+ JSON to /postback/clickbank (AES-256-CBC encrypted body;
            decryption requires the INS secret — handled at the server layer;
            this module parses the decrypted/notification dict).
Money convention (CLAUDE.md): integer cents internally.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Mapping, Optional


def _cents(amount: object) -> Optional[int]:
    if amount is None or amount == "":
        return None
    return round(float(str(amount).replace(",", "")) * 100)


# ---------------------------------------------------------------------------
# Digistore24
# ---------------------------------------------------------------------------
DS24_REFUND_EVENTS = {"on_refund", "on_chargeback", "refund", "chargeback"}

def ds24_signature_valid(params: Mapping[str, str], passphrase: str) -> bool:
    """Digistore24 IPN: sha_sign = SHA512 over sorted key=value pairs (non-empty,
    excluding sha_sign), each value followed by the passphrase."""
    provided = params.get("sha_sign", "")
    if not provided or not passphrase:
        return False
    keys = sorted(k for k in params if k != "sha_sign" and params[k] not in (None, "", "false"))
    payload = "".join(f"{k}={params[k]}{passphrase}" for k in keys)
    digest = hashlib.sha512(payload.encode()).hexdigest().upper()
    return hmac.compare_digest(digest, provided.upper())


def parse_ds24(params: Mapping[str, str]) -> dict:
    """Map a Digistore24 IPN to a conversions row."""
    event = (params.get("event") or "").lower()
    is_refund = event in DS24_REFUND_EVENTS
    ctype = "refund" if is_refund else ("rebill" if "rebill" in event else "sale")
    return {
        "network": "digistore24",
        "subid": params.get("sid1") or params.get("custom") or "",
        "click_id": params.get("cid") or "",
        "order_id": params.get("order_id") or "",
        "gross_cents": _cents(params.get("amount_brutto") or params.get("transaction_amount")),
        "commission_cents": _cents(params.get("amount_affiliate") or params.get("affiliate_amount")),
        "type": ctype,
        "is_refund": is_refund,
        "raw": dict(params),
    }


# ---------------------------------------------------------------------------
# ClickBank (INS v6+ decrypted notification)
# ---------------------------------------------------------------------------
CB_REFUND_TYPES = {"RFND", "CGBK", "INSF"}

def parse_clickbank(n: Mapping[str, object]) -> dict:
    """Map a decrypted ClickBank INS notification to a conversions row.

    TID surfaces as trackingCodes[0] (the per-video subID).
    """
    ttype = str(n.get("transactionType", "")).upper()
    codes = n.get("trackingCodes") or []
    subid = str(codes[0]) if codes else ""
    totals = n.get("totalOrderAmount")
    aff_amount = None
    for li in n.get("lineItems") or []:
        amt = li.get("accountAmount") if isinstance(li, Mapping) else None
        if amt is not None:
            aff_amount = (aff_amount or 0) + round(float(amt) * 100)
    is_refund = ttype in CB_REFUND_TYPES
    return {
        "network": "clickbank",
        "subid": subid,
        "click_id": "",
        "order_id": str(n.get("receipt", "")),
        "gross_cents": _cents(totals),
        "commission_cents": aff_amount,
        "type": "refund" if is_refund else ("rebill" if ttype == "BILL" else "sale"),
        "is_refund": is_refund,
        "raw": dict(n),
    }


def conversion_row_to_db(row: dict, video_id: Optional[str] = None) -> dict:
    """Shape for Supabase conversions insert (numeric dollars in DB; cents kept
    in raw for exactness)."""
    return {
        "video_id": video_id,
        "subid": row["subid"],
        "network": row["network"],
        "order_id": row["order_id"],
        "gross": (row["gross_cents"] or 0) / 100 if row["gross_cents"] is not None else None,
        "commission": (row["commission_cents"] or 0) / 100 if row["commission_cents"] is not None else None,
        "type": row["type"],
        "is_refund": row["is_refund"],
        "raw": row["raw"],
    }

"""Earnings-Reconciliation pollers (component 11): network-truth earnings.

Networks (ARCHITECTURE.md Finding 2 / §7.5):
  ClickBank   — Analytics API, 'DEV:CLERK' key header, paginated 100 rows.
  Digistore24 — listTransactions (API key, readonly scope OK).
  Impact      — Partner API, Basic Auth (AccountSID:AuthToken), 45-day range cap.
  PartnerStack— Partner API, Bearer key, GET /api/v2/rewards.
  Amazon      — NO earnings API: import_amazon_csv() for report files.

Each poller normalizes to `earnings` rows:
  {network, offer_external_id, subid, period, commission, refunds, rebills, raw}
HTTP layer is injectable (fetch_fn) so integration tests run fully mocked.
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request
from datetime import date
from typing import Callable, List, Optional

FetchFn = Callable[[str, dict], str]   # (url, headers) -> response text


def _default_fetch(url: str, headers: dict) -> str:
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=30).read().decode()


# ---------------------------------------------------------------------------
# ClickBank — Analytics API (affiliate role)
# ---------------------------------------------------------------------------
def poll_clickbank(dev_key: str, clerk_key: str, start: date, end: date,
                   fetch_fn: FetchFn = _default_fetch) -> List[dict]:
    url = (f"https://api.clickbank.com/rest/1.3/analytics/affiliate/subid"
           f"?startDate={start.isoformat()}&endDate={end.isoformat()}&select=SALE_COUNT,SALE_AMOUNT,REFUND_AMOUNT,REBILL_AMOUNT")
    raw = fetch_fn(url, {"Authorization": f"{dev_key}:{clerk_key}", "Accept": "application/json"})
    data = json.loads(raw)
    rows = []
    for r in data.get("rows", []):
        d = r if isinstance(r, dict) else {}
        rows.append({
            "network": "clickbank",
            "offer_external_id": d.get("vendor", ""),
            "subid": d.get("trackingId") or d.get("subId") or "",
            "period": end.isoformat(),
            "commission": float(d.get("saleAmount", 0) or 0),
            "refunds": float(d.get("refundAmount", 0) or 0),
            "rebills": float(d.get("rebillAmount", 0) or 0),
            "raw": d,
        })
    return rows


# ---------------------------------------------------------------------------
# Digistore24 — listTransactions
# ---------------------------------------------------------------------------
def poll_digistore24(api_key: str, start: date, end: date,
                     fetch_fn: FetchFn = _default_fetch) -> List[dict]:
    url = (f"https://www.digistore24.com/api/call/listTransactions"
           f"?from={start.isoformat()}&to={end.isoformat()}")
    raw = fetch_fn(url, {"X-DS-API-KEY": api_key, "Accept": "application/json"})
    data = json.loads(raw)
    rows = []
    for t in (data.get("data", {}) or {}).get("transaction_list", []):
        ttype = (t.get("transaction_type") or "").lower()
        commission = float(t.get("affiliate_amount", 0) or 0)
        rows.append({
            "network": "digistore24",
            "offer_external_id": str(t.get("product_id", "")),
            "subid": t.get("sid1") or t.get("custom") or "",
            "period": (t.get("transaction_date") or end.isoformat())[:10],
            "commission": commission if ttype not in ("refund", "chargeback") else 0.0,
            "refunds": commission if ttype in ("refund", "chargeback") else 0.0,
            "rebills": commission if ttype == "rebill" else 0.0,
            "raw": t,
        })
    return rows


# ---------------------------------------------------------------------------
# Impact — Partner API (45-day range cap enforced by caller schedule)
# ---------------------------------------------------------------------------
def poll_impact(account_sid: str, auth_token: str, start: date, end: date,
                fetch_fn: FetchFn = _default_fetch) -> List[dict]:
    if (end - start).days > 45:
        raise ValueError("Impact Actions API: max 45-day range — split the window")
    import base64
    basic = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    url = (f"https://api.impact.com/Mediapartners/{account_sid}/Actions"
           f"?StartDate={start.isoformat()}T00:00:00Z&EndDate={end.isoformat()}T23:59:59Z&PageSize=1000")
    raw = fetch_fn(url, {"Authorization": f"Basic {basic}", "Accept": "application/json"})
    data = json.loads(raw)
    rows = []
    for a in data.get("Actions", []):
        state = (a.get("State") or "").upper()
        payout = float(a.get("Payout", 0) or 0)
        rows.append({
            "network": "impact",
            "offer_external_id": str(a.get("CampaignId", "")),
            "subid": a.get("SubId1") or "",
            "period": (a.get("EventDate") or end.isoformat())[:10],
            "commission": payout if state != "REVERSED" else 0.0,
            "refunds": payout if state == "REVERSED" else 0.0,
            "rebills": 0.0,
            "raw": a,
        })
    return rows


# ---------------------------------------------------------------------------
# PartnerStack — Partner API (Bearer; epoch-ms timestamps)
# ---------------------------------------------------------------------------
def poll_partnerstack(api_key: str, start: date, end: date,
                      fetch_fn: FetchFn = _default_fetch) -> List[dict]:
    start_ms = int(__import__("time").mktime(start.timetuple()) * 1000)
    end_ms = int(__import__("time").mktime(end.timetuple()) * 1000) + 86_399_999
    url = f"https://api.partnerstack.com/api/v2/rewards?created_at_min={start_ms}&created_at_max={end_ms}&limit=250"
    raw = fetch_fn(url, {"Authorization": f"Bearer {api_key}", "Accept": "application/json"})
    data = json.loads(raw)
    items = data.get("data", {}).get("items", []) if isinstance(data.get("data"), dict) else data.get("rewards", [])
    rows = []
    for r in items:
        amount = float(r.get("amount", 0) or 0) / 100.0   # PS amounts in cents
        reversed_ = bool(r.get("reversed_at"))
        rows.append({
            "network": "partnerstack",
            "offer_external_id": str((r.get("group") or {}).get("slug") or r.get("offer_key") or ""),
            "subid": (r.get("metadata") or {}).get("subid", ""),
            "period": end.isoformat(),
            "commission": 0.0 if reversed_ else amount,
            "refunds": amount if reversed_ else 0.0,
            "rebills": amount if (r.get("reward_type") == "recurring" and not reversed_) else 0.0,
            "raw": r,
        })
    return rows


# ---------------------------------------------------------------------------
# Amazon — CSV report import (no API exists)
# ---------------------------------------------------------------------------
def import_amazon_csv(csv_text: str, period: Optional[str] = None) -> List[dict]:
    """Associates Central 'Earnings report' CSV → earnings rows.
    Tolerant of column-name drift: matches lowercase contains."""
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("﻿")))
    rows = []
    for r in reader:
        low = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        def col(*needles):
            for k, v in low.items():
                if all(n in k for n in needles):
                    return v
            return ""
        fees = col("fee") or col("earnings") or "0"
        try:
            commission = float(fees.replace("$", "").replace(",", "") or 0)
        except ValueError:
            commission = 0.0
        rows.append({
            "network": "amazon",
            "offer_external_id": col("asin") or col("product"),
            "subid": col("tracking"),
            "period": period or date.today().isoformat(),
            "commission": commission,
            "refunds": 0.0,
            "rebills": 0.0,
            "raw": dict(r),
        })
    return rows

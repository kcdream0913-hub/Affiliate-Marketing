"""ClickBank Marketplace XML feed (v2) ingester.

Feed: https://accounts.clickbank.com/feeds/marketplace_feed_v2.xml.zip (daily).
NO marketplace REST API exists (ARCHITECTURE.md Finding 2) — this feed is the
only bulk source of gravity / Avg$/sale for not-yet-promoted offers.

Source-health rule (risk register): verify on EVERY run — fetch may 404 if
ClickBank moves the feed. fail-soft: raise FeedUnavailable, caller falls back
to last-good cache + alerts. Provenance for all fields here: 'feed'.
"""
from __future__ import annotations

import io
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from typing import List, Optional

FEED_URL = "https://accounts.clickbank.com/feeds/marketplace_feed_v2.xml.zip"


class FeedUnavailable(Exception):
    """Feed missing/moved/unparseable — alert + use last-good cache."""


@dataclass
class CBListing:
    external_id: str
    name: str
    category: str
    gravity: Optional[float] = None
    avg_dollar_per_sale: Optional[float] = None
    initial_dollar_per_sale: Optional[float] = None
    percent_per_sale: Optional[float] = None
    percent_per_rebill: Optional[float] = None
    has_recurring: bool = False
    activate_date: str = ""
    provenance: dict = field(default_factory=lambda: {
        "gravity": "feed", "avg_dollar_per_sale": "feed",
        "commission_pct": "feed", "category": "feed",
    })

    def to_offer_row(self) -> dict:
        """Shape for the offers table (network=clickbank)."""
        return {
            "network": "clickbank",
            "external_id": self.external_id,
            "name": self.name,
            "category": self.category,
            "commission_pct": self.percent_per_sale,
            "avg_dollar_per_sale": self.avg_dollar_per_sale,
            "gravity": self.gravity,
            "cookie_days": 60,           # ClickBank standard (manual constant)
            "source": {**self.provenance, "cookie_days": "manual"},
            "status": "candidate",
        }


def _num(el: Optional[ET.Element]) -> Optional[float]:
    if el is None or el.text in (None, ""):
        return None
    try:
        return float(el.text)
    except ValueError:
        return None


def parse_feed_xml(xml_text: str) -> List[CBListing]:
    """Parse marketplace feed v2 XML → listings. Tolerant of unknown tags;
    raises FeedUnavailable if the structure is unrecognizable (schema drift)."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise FeedUnavailable(f"XML parse error: {e}") from e

    listings: List[CBListing] = []

    def walk(node: ET.Element, category_path: List[str]):
        name_el = node.find("Name")
        cat_name = name_el.text.strip() if (name_el is not None and name_el.text) else ""
        path = category_path + ([cat_name] if cat_name else [])
        for site in node.findall("Site"):
            sid = site.findtext("Id", "").strip()
            if not sid:
                continue
            listings.append(CBListing(
                external_id=sid,
                name=(site.findtext("Title") or "").strip(),
                category=" > ".join(path),
                gravity=_num(site.find("Gravity")),
                avg_dollar_per_sale=_num(site.find("AverageEarningsPerSale")),
                initial_dollar_per_sale=_num(site.find("InitialEarningsPerSale")),
                percent_per_sale=_num(site.find("PercentPerSale")),
                percent_per_rebill=_num(site.find("PercentPerRebill")),
                has_recurring=(site.findtext("HasRecurringProducts", "false").strip().lower() == "true"),
                activate_date=(site.findtext("ActivateDate") or "").strip(),
            ))
        for child in node.findall("Category"):
            walk(child, path)

    for top in root.findall(".//Category"):
        # walk only top-level categories (avoid double-walking nested ones)
        pass
    # Walk from root: handles <Catalog><Category>... and nested categories.
    for top in root.findall("Category"):
        walk(top, [])
    if not listings and root.findall(".//Site"):
        # structure changed (Sites not under Category) — still try flat parse
        for site in root.findall(".//Site"):
            sid = site.findtext("Id", "").strip()
            if sid:
                listings.append(CBListing(
                    external_id=sid,
                    name=(site.findtext("Title") or "").strip(),
                    category="",
                    gravity=_num(site.find("Gravity")),
                    avg_dollar_per_sale=_num(site.find("AverageEarningsPerSale")),
                ))
    if not listings:
        raise FeedUnavailable("no <Site> listings found — schema drift or empty feed")
    return listings


def fetch_feed(url: str = FEED_URL, timeout: int = 60) -> List[CBListing]:
    """Download + unzip + parse the daily feed. Raises FeedUnavailable on any
    failure (caller: alert + fall back to last-good cache)."""
    try:
        raw = urllib.request.urlopen(url, timeout=timeout).read()
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            xml_name = next(n for n in zf.namelist() if n.endswith(".xml"))
            xml_text = zf.read(xml_name).decode("utf-8", errors="replace")
    except Exception as e:
        raise FeedUnavailable(f"feed fetch failed ({url}): {e}") from e
    return parse_feed_xml(xml_text)

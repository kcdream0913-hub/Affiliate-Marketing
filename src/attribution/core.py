"""Attribution core: subID generation + network redirect URL builders.

Pure functions, stdlib-only — fully unit-testable, portable to the VPS service.
Pattern (ARCHITECTURE.md §3): go.domain.com/v/{video_id} → log click → 302 to
network link carrying the subID (tid for ClickBank, cid+sid1 for Digistore24).
"""
from __future__ import annotations

import hashlib
import re
import uuid
from urllib.parse import quote, urlencode

# ClickBank TID: alphanumeric, max 24 chars (appears in commission reports).
_CB_TID_SAFE = re.compile(r"[^a-zA-Z0-9]")
# Digistore24 sid: letters/digits/-/_ are safest; docs warn on charset+length.
_DS_SID_SAFE = re.compile(r"[^a-zA-Z0-9_-]")

SUBID_MAX = 24


def video_subid(video_id: str) -> str:
    """Deterministic, network-safe subID from a video UUID.

    Uses the UUID's hex (no dashes) truncated to 24 chars — round-trippable
    against the clicks table (store full video_id alongside subid).
    """
    vid = uuid.UUID(video_id)  # raises ValueError on junk input
    return vid.hex[:SUBID_MAX]


def clickbank_hoplink(nickname: str, vendor: str, video_id: str) -> str:
    """https://NICKNAME.VENDOR.hop.clickbank.net/?tid=SUBID"""
    tid = _CB_TID_SAFE.sub("", video_subid(video_id))[:SUBID_MAX]
    return f"https://{quote(nickname)}.{quote(vendor)}.hop.clickbank.net/?tid={tid}"


def digistore24_link(product_id: str, affiliate_id: str, video_id: str, campaignkey: str = "") -> str:
    """https://www.checkout-ds24.com/redir/PRODUCT/AFFILIATE/CAMPAIGNKEY?sid1=SUBID

    cid (click id) is appended by the redirect service per-click; sid1 carries
    the stable per-video subID.
    """
    sid1 = _DS_SID_SAFE.sub("", video_subid(video_id))
    base = f"https://www.checkout-ds24.com/redir/{quote(product_id)}/{quote(affiliate_id)}"
    if campaignkey:
        base += f"/{quote(campaignkey)}"
    return f"{base}?{urlencode({'sid1': sid1})}"


def generic_sublink(base_url: str, video_id: str, param: str = "subid") -> str:
    """SaaS/Impact/PartnerStack links: append subid param to a program link."""
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}{urlencode({param: video_subid(video_id)})}"


def build_redirect(network: str, video_id: str, *, click_id: str = "", **kw) -> str:
    """Dispatch: network name → final 302 target URL."""
    network = network.lower()
    if network == "clickbank":
        return clickbank_hoplink(kw["nickname"], kw["vendor"], video_id)
    if network == "digistore24":
        url = digistore24_link(kw["product_id"], kw["affiliate_id"], video_id, kw.get("campaignkey", ""))
        if click_id:
            url += f"&{urlencode({'cid': click_id})}"
        return url
    if network in {"impact", "partnerstack", "rewardful", "generic"}:
        return generic_sublink(kw["base_url"], video_id, kw.get("param", "subid"))
    raise ValueError(f"unknown network: {network}")


def hash_ip(ip: str, salt: str) -> str:
    """GDPR-lean click logging: store salted hash, never the raw IP."""
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:32]


def new_click_id() -> str:
    return uuid.uuid4().hex

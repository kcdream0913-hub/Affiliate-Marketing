"""CLI for n8n Execute Command nodes.

Usage:
  echo '{"script":"...","caption":"...","offer_category":"...",
        "platform_toggle_set":true,"onscreen_text":"#ad · AI-generated",
        "c2pa_present":true}' | python3 -m src.compliance.cli

stdout: JSON {verdict, blocked, matched_rules, notes, escalated}
exit code: 0 = pass/medium, 2 = BLOCKED (n8n IF node routes on this or on .blocked)
"""
from __future__ import annotations

import json
import sys

from .classifier import gate


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    result = gate(
        script=payload.get("script", ""),
        caption=payload.get("caption", ""),
        offer_category=payload.get("offer_category", ""),
        platform_toggle_set=bool(payload.get("platform_toggle_set", False)),
        onscreen_text=payload.get("onscreen_text", ""),
        c2pa_present=bool(payload.get("c2pa_present", False)),
        is_realistic_ai_media=bool(payload.get("is_realistic_ai_media", True)),
    )
    print(json.dumps({
        "verdict": result.verdict,
        "blocked": result.blocked,
        "matched_rules": result.matched_rules,
        "notes": result.notes,
        "escalated": result.escalated,
    }))
    return 2 if result.blocked else 0


if __name__ == "__main__":
    sys.exit(main())

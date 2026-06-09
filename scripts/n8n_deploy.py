#!/usr/bin/env python3
"""Deploy a workflow JSON to n8n via the public REST API (no UI editing).

Usage:
  python scripts/n8n_deploy.py workflows/02-script-copy.json [--activate]

Env: N8N_URL (e.g. https://n8n.yourdomain.com), N8N_API_KEY
Behavior: upsert by workflow name — if a workflow with the same name exists,
it is updated (PUT), else created (POST). Credentials are never in the JSON;
n8n credential references are bound by name in the instance (HUMAN-CHECKPOINT).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

STRIP_KEYS = {"id", "versionId", "meta", "tags", "pinData", "active", "staticData", "shared"}


def _req(method: str, path: str, body: dict | None = None) -> dict:
    url = os.environ["N8N_URL"].rstrip("/") + "/api/v1" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "X-N8N-API-KEY": os.environ["N8N_API_KEY"],
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or "{}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} on {method} {path}: {e.read().decode()[:500]}", file=sys.stderr)
        raise


def load_workflow(path: str) -> dict:
    with open(path) as f:
        wf = json.load(f)
    payload = {k: v for k, v in wf.items() if k not in STRIP_KEYS}
    payload.setdefault("settings", {})
    for node in payload.get("nodes", []):
        # safety: refuse to deploy if anything looks like an inline secret
        blob = json.dumps(node.get("parameters", {})).lower()
        for needle in ("api_key=", "apikey\":", "secret", "password", "bearer "):
            if needle in blob and "credential" not in blob:
                raise SystemExit(f"refusing deploy: possible inline secret in node '{node.get('name')}' ({needle})")
    return payload


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    path = sys.argv[1]
    activate = "--activate" in sys.argv
    wf = load_workflow(path)

    existing = {w["name"]: w["id"] for w in _req("GET", "/workflows?limit=250").get("data", [])}
    if wf["name"] in existing:
        wid = existing[wf["name"]]
        _req("PUT", f"/workflows/{wid}", wf)
        print(f"updated '{wf['name']}' (id {wid})")
    else:
        created = _req("POST", "/workflows", wf)
        wid = created.get("id")
        print(f"created '{wf['name']}' (id {wid})")

    if activate:
        _req("POST", f"/workflows/{wid}/activate")
        print(f"activated '{wf['name']}'")
    else:
        print("not activated (staging default; use --activate after HUMAN-CHECKPOINT)")


if __name__ == "__main__":
    main()

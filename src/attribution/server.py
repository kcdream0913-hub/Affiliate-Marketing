"""Attribution redirect service — stdlib-only, zero dependencies.

Runs on the Hetzner VPS behind Caddy (go.{DOMAIN} → :8080).
Endpoints:
  GET  /health                     → 200 ok
  GET  /v/{video_id}               → log click (async) + 302 to network URL
  POST /postback/digistore24       → verify sha_sign, insert conversion
  POST /postback/clickbank         → decrypt INS (AES-256-CBC), insert conversion

Click logging is fire-and-forget via a background queue so the 302 is never
blocked by Supabase latency (target: <50ms p50).

Env: SUPABASE_URL, SUPABASE_SERVICE_KEY, IP_SALT, DS24_IPN_PASSPHRASE,
     CB_INS_SECRET, OFFERS_CONFIG (path to offers.json routing map).
"""
from __future__ import annotations

import json
import os
import queue
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .core import build_redirect, hash_ip, new_click_id, video_subid
from .postbacks import conversion_row_to_db, ds24_signature_valid, parse_clickbank, parse_ds24

_log_q: "queue.Queue[tuple[str, dict]]" = queue.Queue(maxsize=10000)


def _supabase_insert(table: str, row: dict) -> None:
    url = os.environ["SUPABASE_URL"].rstrip("/") + f"/rest/v1/{table}"
    req = urllib.request.Request(
        url,
        data=json.dumps(row).encode(),
        headers={
            "apikey": os.environ["SUPABASE_SERVICE_KEY"],
            "Authorization": "Bearer " + os.environ["SUPABASE_SERVICE_KEY"],
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method="POST",
    )
    urllib.request.urlopen(req, timeout=10).read()


def _log_worker() -> None:
    while True:
        table, row = _log_q.get()
        try:
            _supabase_insert(table, row)
        except Exception as e:  # never crash the worker; alert via stderr
            print(f"[log_worker] insert failed: {e}", flush=True)
        finally:
            _log_q.task_done()


def load_offers_config() -> dict:
    """offers.json: {video_id: {network, nickname/vendor | product_id/affiliate_id | base_url}}"""
    path = os.environ.get("OFFERS_CONFIG", "offers.json")
    with open(path) as f:
        return json.load(f)


class Handler(BaseHTTPRequestHandler):
    offers: dict = {}

    def log_message(self, *a):  # quiet default access log
        pass

    def _send(self, code: int, body: bytes = b"", location: str = ""):
        self.send_response(code)
        if location:
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self._send(200, b"ok")
        if parsed.path.startswith("/v/"):
            video_id = parsed.path[3:].strip("/")
            cfg = self.offers.get(video_id)
            if not cfg:
                return self._send(404, b"unknown video")
            click_id = new_click_id()
            try:
                target = build_redirect(cfg["network"], video_id, click_id=click_id, **cfg.get("params", {}))
            except (KeyError, ValueError):
                return self._send(500, b"bad offer config")
            ip = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
            try:
                _log_q.put_nowait(("clicks", {
                    "video_id": video_id,
                    "subid": video_subid(video_id),
                    "ip_hash": hash_ip(ip, os.environ.get("IP_SALT", "")),
                    "ua": self.headers.get("User-Agent", "")[:300],
                    "country": self.headers.get("CF-IPCountry", ""),
                }))
            except queue.Full:
                print("[clicks] queue full — dropping log, redirect continues", flush=True)
            return self._send(302, location=target)
        return self._send(404, b"not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        if self.path == "/postback/digistore24":
            params = {k: v[0] for k, v in parse_qs(body.decode(errors="replace")).items()}
            if not ds24_signature_valid(params, os.environ.get("DS24_IPN_PASSPHRASE", "")):
                return self._send(403, b"bad signature")
            row = parse_ds24(params)
            _log_q.put(("conversions", conversion_row_to_db(row)))
            return self._send(200, b"OK")
        if self.path == "/postback/clickbank":
            try:
                notification = json.loads(_decrypt_cb_ins(body))
            except Exception:
                return self._send(400, b"bad payload")
            row = parse_clickbank(notification)
            _log_q.put(("conversions", conversion_row_to_db(row)))
            return self._send(200, b"OK")
        return self._send(404, b"not found")


def _decrypt_cb_ins(body: bytes) -> str:
    """ClickBank INS v6+: AES-256-CBC, key = sha1(secret)[:32], iv in payload.
    Requires `cryptography` on the VPS (the one prod-only dependency); imported
    lazily so the rest of the service stays stdlib-only for tests."""
    payload = json.loads(body)
    from base64 import b64decode
    from hashlib import sha1

    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # type: ignore

    secret = os.environ["CB_INS_SECRET"]
    key = sha1(secret.encode()).hexdigest()[:32].encode()
    iv = b64decode(payload["iv"])
    data = b64decode(payload["notification"])
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    dec = cipher.decryptor()
    out = dec.update(data) + dec.finalize()
    return out[: -out[-1]].decode()  # strip PKCS#7 padding


def main() -> None:
    threading.Thread(target=_log_worker, daemon=True).start()
    Handler.offers = load_offers_config()
    port = int(os.environ.get("PORT", "8080"))
    print(f"attribution service on :{port} ({len(Handler.offers)} routes)", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()

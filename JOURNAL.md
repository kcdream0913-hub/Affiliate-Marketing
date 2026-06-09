# JOURNAL

## [SPRINT-1] 2026-06-09 — Attribution layer
### What changed
- src/attribution/: core.py (subID gen + ClickBank/DS24/SaaS redirect builders), postbacks.py (DS24 sha512 IPN verify + ClickBank INS parse, money in cents), server.py (stdlib HTTP service: /health, /v/{id} 302 + async click log queue, /postback/* ingesters).
- deploy/: docker-compose.yml (Postgres + n8n + attribution + Caddy), Caddyfile (n8n. + go. hosts, auto-TLS), .env.example, offers.json routing map.
- tests/test_attribution.py (14 tests), .gitignore.
### Decisions
- Stdlib-only service (no FastAPI): zero deps = testable everywhere, tiny RAM footprint on CPX11; `cryptography` is the single prod-only dep (ClickBank INS AES decrypt), lazily imported.
- Click log is fire-and-forget queue: 302 never blocks on Supabase; queue-full drops the log, never the redirect.
- IPs stored only as salted SHA256 (GDPR-lean).
### Metrics
- tests: 28/28 passed (compliance 14 + attribution 14)
- redirect smoke: 302 correct (sid1 + cid present); p50 3.7ms / p95 5.0ms local (n=20) — gate <50ms ✓
### Open questions / TODO
- HUMAN-CHECKPOINT: KC pushes repo to GitHub (sandbox proxy blocks push); commands provided in chat.
- HUMAN-CHECKPOINT: Hetzner VPS provisioning + DNS (n8n./go. subdomains) + .env secrets.
- HUMAN-CHECKPOINT: configure DS24 IPN + ClickBank INS endpoints (needs network accounts).
- offers.json contains sample routes — replace after Sprint 2 offer approval.
### Verification
- gates: [tests ✓] [smoke ✓ + latency ✓] [lint pending local] [deploy dry-run pending VPS]

## [SPRINT-0] 2026-06-09 — Repo scaffold + Compliance-Gate
### What changed
- Repo skeleton created (src/, tests/, scripts/, workflows/, supabase/, docs/).
- Research docs filed under docs/research/; ARCHITECTURE.md installed as source of truth.
- Supabase initial schema migration written (supabase/migrations/001_initial_schema.sql).
- Compliance-Gate classifier (src/compliance/) with tiered HIGH/MEDIUM/LOW rules, category escalation, disclosure enforcement, AI-disclosure tagger checks.
- Test corpus + unit tests (tests/test_compliance.py).
### Decisions
- Python (stdlib-only classifier core) — runs anywhere incl. n8n Code node port later; LLM semantic pass is a pluggable second stage (Sprint 3, OpenRouter).
- HIGH rules are regex lexicon, intentionally over-broad: zero false-negatives prioritized over false-positives (human reviews HIGH flags).
- Health/finance/income offer categories auto-escalate MEDIUM verdicts to HIGH-review.
### Metrics
- tests: 14/14 passed (HIGH corpus: 12/12 blocked, zero false-negatives)
- smoke: PASS (gate blocks HIGH creative, passes clean creative)
- migration: 8 tables, 7 indexes, syntax-sane (full dry-run pending live Supabase)
### Open questions / TODO
- HUMAN-CHECKPOINT: KC legal review of HIGH ruleset before first live post.
- HUMAN-CHECKPOINT: apply migration to live Supabase project (account/keys).
- Verify ClickBank Marketplace XML feed URL still live before Sprint 2.
### Verification
- gates: [tests ✓] [lint n/a — no pip in sandbox, run locally] [smoke ✓] [migration dry-run pending live Supabase]

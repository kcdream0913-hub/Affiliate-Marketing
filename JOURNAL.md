# JOURNAL

## [SPRINT-3] 2026-06-09 — Content pipeline as code (n8n workflows)
### What changed
- workflows/: 01-trend-discovery (Apify→LLM rank→Supabase), 02-script-copy (LLM script→Compliance Gate CLI→IF block/save + Telegram HIGH alert), 03-image-generation (Nano Banana, 3-6 varied prompts, randomized compositions), 04-video-assembly (voice rotation→video_assembly.sh→ai_labeled/c2pa flags), 05-posting-approval (Warming Guard→Telegram sendAndWait approval→Upload-Post with is_ai_generated→mark posted).
- scripts/n8n_deploy.py: upsert-by-name via n8n REST API, refuses inline secrets, --activate behind HUMAN-CHECKPOINT.
- src/compliance/cli.py: stdin JSON → verdict JSON, exit 2 on block (n8n Execute Command integration).
- scripts/video_assembly.sh: edge-tts (rate/pitch jitter) + FFmpeg Ken Burns 1080x1920 + burned "#ad" and "AI-generated" overlays.
- tests/test_workflows.py: 8 structural/guardrail tests.
### Decisions
- Credentials exist only as n8n name-references ("Supabase Service Auth" etc.) bound in the instance — JSON stays clean for git (enforced by test + deploy script).
- Compliance gate runs BEFORE any asset spend: 02 saves drafts only after PASS; HIGH routes to Telegram alert, never to image gen.
- Warming guard hard-throws at >3 posts/day or <2h spacing — code-level enforcement of the account-warming rule.
### Metrics
- tests: 51/51 passed (compliance 14, attribution 14, offers 15, workflows 8)
- CLI smoke: HIGH creative → blocked, exit 2 ✓
### Open questions / TODO
- DoD "end-to-end draft video in staging queue" requires live n8n → pending VPS (HUMAN-CHECKPOINT).
- n8n credential setup at deploy: Apify, OpenRouter, Gemini, Supabase, Telegram, Upload-Post (HUMAN-CHECKPOINT).
- Verify Upload-Post API field names against their current docs at integration time.
### Verification
- gates: [tests ✓] [workflow integrity ✓] [n8n import dry-run pending VPS]

## [SPRINT-2] 2026-06-09 — Offer-Scoring (partial: feed + rubric)
### What changed
- src/offers/feed_clickbank.py: Marketplace XML v2 ingester (nested-category walk, fail-soft FeedUnavailable for schema drift/moved feed, provenance=feed, cookie_days=60 manual constant).
- src/offers/scorer.py: 6-factor weighted rubric + all kill criteria from ARCHITECTURE.md (refund>15%, gravity<8 CB-only, gravity>150 saturation guard, HIGH claim-risk, Net-90, holdback>60d, cookie<14d, SaaS downgrade-reset, DS24 no-history). rank_candidates() for shortlists.
- tests/test_offers.py (15 tests, feed fixture + kill/rank assertions).
### Decisions
- Missing metric data scores 0, never average — conservative bias incentivizes provenance completion before approving offers.
- Feed URL responds (HTTP OK) but binary content unverifiable from sandbox; ingester has built-in source-health failure mode per risk register.
### Metrics
- tests: 43/43 passed (compliance 14 + attribution 14 + offers 15)
### Open questions / TODO
- Remaining Sprint 2: Digistore24 marketplace scraper + SaaS program-page ingester (semi-manual) — needs live page structures; deferred until KC has network accounts (HUMAN-CHECKPOINT: account signups).
- Run live feed pull on VPS at deploy to verify gravity/Avg$ fields present.
### Verification
- gates: [tests ✓] [smoke ✓] [feed live-pull pending VPS]

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

# Project: autonomous-affiliate

Autonomous affiliate marketing pipeline. Source of truth: `ARCHITECTURE.md`. Deep references: `docs/agent-guides/`, `docs/research/`.

## Commands (exact)
- test: `python -m pytest tests/ -q`
- lint: `ruff check src/ tests/`
- smoke: `./scripts/smoke.sh` (compliance gate on sample corpus + SQL syntax check)
- n8n deploy (Sprint 3+): `python scripts/n8n_deploy.py <workflow.json>`

## Conventions
- All money math in integer cents. UTC everywhere.
- Provenance tag on every offer-data field: `feed | scrape | api | manual`.
- Workflows live as JSON in `/workflows`, deployed via n8n REST API — never hand-edited in the UI.
- Every script/caption MUST pass the Compliance-Gate (`src/compliance/`) before any asset spend (images, video, posting).
- Captions always start with `#ad`. Videos always carry a visible AI-disclosure overlay + burned "#ad". CTA always drives to link-in-bio (no links in captions — platform rule).

## Architecture
- 12 components: 7 original agents + Compliance-Gate (0), Offer-Scoring (8), Attribution (9), Bandit-Allocator (10), Earnings-Reconciliation (11), AI-Disclosure labeler (12). See ARCHITECTURE.md.
- Infra: Hetzner CPX11 (n8n via Docker Compose + Postgres + Caddy; attribution redirect service on same box). Supabase for pipeline data. Nano Banana images ($0.039/img). edge-tts + FFmpeg local. Upload-Post/Blotato for posting.
- Offer data: ClickBank Marketplace XML feed + Digistore24 scrape (NO marketplace APIs exist); own EPC/refunds via earnings APIs post-launch.

## NEVER
- Never post live content, deploy prod, spend money, or commit credentials without a HUMAN-CHECKPOINT tag.
- Never generate HIGH-risk claims (disease/cure, income/earnings, before-after, "guaranteed") — Compliance-Gate hard-blocks; do not soften and retry HIGH.
- Never strip C2PA metadata or skip the platform AI-disclosure toggle.
- Never post more than 1–3×/day per account in the first 2–3 weeks (warming), spaced 2–4h apart.

## Definition of done
All gates green (tests, lint, smoke, migration dry-run) + JOURNAL.md updated.

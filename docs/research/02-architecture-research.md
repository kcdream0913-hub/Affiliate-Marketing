# ARCHITECTURE.md — Autonomous Affiliate Marketing Platform (Source of Truth)
**Owner:** KC (solo dev/operator) · **Date:** 2026-06-09 · **Build mode:** AI-agent loop (Claude Code) with pre-granted permissions + human checkpoints

## TL;DR
- Build it on the existing stack. The architecture extends the 7-agent n8n pipeline with five new components (Compliance-Gate, Offer-Scoring, Attribution layer, Bandit-Allocator, Earnings-Reconciliation) plus an AI-disclosure auto-labeler, all driven by a Supabase schema; host the click-redirect layer on the **Hetzner VPS (Caddy + tiny Go/Python service)**, not Vercel edge, because it gives sub-50ms 302s with zero cold start and no per-invocation cost.
- The live rules changed and matter: TikTok Shop US affiliate self-apply needs **1,000 followers** (5,000 for full Product Marketplace), creators are put in a **30-day Pilot with a 3-shoppable-videos/day cap**, and a **daily shoppable-content posting limit takes effect May 11, 2026**; AI content must be self-labeled and TikTok auto-detects via C2PA (it has labeled **over 1.3 billion videos to date**, per TikTok Newsroom) — labeled AI content stays monetizable, so keep TikTok Shop a deferred third arm and lead with Digistore24/ClickBank links.
- A hard data constraint defines the Offer-Scoring agent: **neither ClickBank nor Digistore24 exposes marketplace gravity/EPC via their affiliate REST API**. Gravity/Avg$ come from ClickBank's daily **Marketplace XML feed** (+ CBEngine/CBSnooper for trend); Digistore24 marketplace KPIs are UI-only and must be scraped. Only *your own* post-promotion EPC/refunds are API-pullable. Build the agent around feed-ingest + scrape, not a nonexistent marketplace API.

## Key Findings

### 1. TikTok Shop & AI-labeling (live, June 2026) — changes flagged
- **Eligibility (US):** Affiliate Creator self-apply = **1,000 followers**; Product Marketplace (promote other sellers) effectively requires **5,000 followers**; Official/Marketing creators bound to a seller = **0 followers**. 18+, US address, identity verification (driver's license/state ID/passport) required after first commission for those who registered for e-commerce permissions from July 2025.
- **Pilot Program:** Creators with 1,000–4,999 followers enter a **30-day Early-Stage Pilot** with a **3 shoppable videos/day** cap and no campaign eligibility. Graduation requires hitting 5,000 followers, a Creator Health Rating above ~176, and generating ~10 organic orders.
- **NEW (changed from prior state):** Effective **May 11, 2026**, TikTok Shop introduces **daily posting limits for shoppable content for all US merchants and creators**. This directly throttles an automated high-volume posting strategy on TikTok Shop.
- **Commissions:** Open Collaboration typically 10–15%; Targeted (invite) 18–50%; platform-wide standard range cited 5–20%. Payouts settle ~15–30 days post-delivery.
- **Returns/SPS:** From **March 10, 2026**, Non-Buyer-Fault Return/Refund Rate (NBFR) is used only for Shop Performance Score, not product-level enforcement; refund-without-return auto-enabled for products **≤$10** (was $25). New **ISRR** metric target ≤20% (30% familiarization). Seller-Fault Return/Refund Rate target <1.0%; SFCR ≤2.5%. These are seller-side, relevant only if KC ever runs a Shop.
- **Insurance mandate:** As of 2026, insurance is **NOT yet mandatory for every seller**, but TikTok runs an Insurance Center, strongly recommends Commercial General Liability (~$1M/occurrence), and can freeze payouts / delist if a claim arises uncovered. Budget ~$29/mo if KC ever becomes a Shop seller. Irrelevant to a pure-affiliate (creator) posture.
- **AI labeling — TikTok:** Self-disclosure toggle required for realistic AI media; TikTok integrated **C2PA Content Credentials on May 9, 2024** (first video-sharing platform to do so, per TikTok Newsroom and NBC News — *note: several secondary trackers misdate this to Jan 2025; the primary TikTok announcement is May 2024*). It auto-labels content carrying AI metadata (Veo, Sora, Kling, Grok, Dreamina all embed C2PA). **Labeled AI content remains monetizable**; unlabeled-but-detected content can be auto-labeled, down-ranked, or removed; repeat violations risk losing commission-withdrawal privileges or bans. AI-assisted *text* (scripts, captions, hashtags) is exempt. Self-labeling is strictly better than auto-detection (auto-detect can trigger extra moderation review).
- **AI labeling — Meta/Instagram Reels:** Meta auto-applies "AI Info" labels to images via C2PA/IPTC metadata; AI-generated **video/audio must be manually disclosed** with Meta's tools. May 2026 added an **opt-in "AI creator" profile label** (does not affect distribution). EU AI Act Article 50 machine-readable labeling obligation lands **Aug 2, 2026** (plus California SB 942 same date).
- **FTC:** Material-connection disclosure must be clear, conspicuous, and adjacent to the link ("paid link" acceptable; "affiliate link"/"commissionable link" insufficient); platform toggles alone are NOT sufficient. In video, disclosure must be in both visual and audio. Health/wellness/income claims are active enforcement priorities → reinforces the HIGH-risk hard-block classifier.

### 2. Offer-data access (defines the Product-Selection/Offer-Scoring agent)
- **ClickBank:** REST API (Products, Analytics, Quickstats) is **account-scoped only** — the Products API is seller-only and returns no gravity/EPC. There is **no marketplace-browse API**. The legitimate bulk route is ClickBank's **daily Marketplace XML feed** (`accounts.clickbank.com/feeds/marketplace_feed_v2.xml.zip`) carrying listings + gravity, Avg$/Initial$ per conversion, %/sale, category, rank. **Verify the feed URL/fields are still live before building** (ClickBank migrated its help center). Supplement with third-party trackers **CBEngine** (weekly history) and **CBSnooper** (daily history) for gravity momentum and refund estimates — these are web/RSS/feed tools, none offers a clean public REST API. *Your own* post-promotion EPC/refunds come from the Analytics API (Clerk key).
- **Digistore24:** API (`dev.digistore24.com`) is **account/order-scoped only** (`listTransactions`, `listPurchases`, `listProducts` = own products). **No marketplace-listing endpoint.** Marketplace KPIs (Net earnings/sale, Earnings/order-form visitor (EPC), Cart conversion, Cancellation rate, sales rank) are **UI-only → must be scraped**. Cookie window is **180 days**. Own cancellation/refund data via `listTransactions` after partnering.
- **Recurring SaaS (PartnerStack/Impact/Rewardful):** PartnerStack runs a marketplace directory (market.partnerstack.com) — its own pages cite **80,000+ active partners across 300+ programs** (one feature page states 65,000+) — with browsable programs (e.g., WebinarJam/EverWebinar 40% recurring 12 mo, Thryv 15% LTV). Impact has an ML-driven marketplace; Rewardful has no marketplace (per-program signup). Enumeration is **semi-manual**: browse marketplace → apply per program (many auto-approve) → pull earnings via PartnerStack Partner API / Impact Partner API / Rewardful REST API. Commission terms are mostly read off the program page (scrape/manual), not a unified API.
- **Buildability verdict:** The rubric is executable but **gravity, EPC, refund rate, and commission for not-yet-promoted offers are NOT API-pullable** for either primary network. The Offer-Scoring agent must: (a) ingest ClickBank XML feed, (b) scrape Digistore24 marketplace + SaaS program pages, (c) manually seed payout-reliability/cookie constants, (d) backfill *actual* EPC/refunds from earnings APIs once an offer is live. Mark each rubric field's provenance in the schema (`source` enum: feed | scrape | api | manual).

### 3. Attribution host decision → **Hetzner VPS (Caddy + tiny service)**
| Option | Cold start | 302 latency | Cost @ 10k–100k clicks/mo | S2S webhook host | Verdict |
|---|---|---|---|---|---|
| **Hetzner VPS (Caddy/nginx + Go/FastAPI)** | None (persistent) | **~10–40ms** | $0 marginal (already paying ~$5–6/mo CPX11) | Same box, persistent | **CHOSEN** |
| Vercel Edge Middleware | low but variable | ~tens of ms; **Hobby = non-commercial, 100GB/1M req hard cap that pauses** | Pro $20/mo to be commercial-legal | OK | Rejected (cost + commercial-use rule + pause behavior) |
| Supabase Edge Functions | **~400ms median cold**, 125ms warm | poor for redirects | Free 500k invocations/mo then $2/M | Good | Rejected for redirect; OK for postbacks |

**Reasoning:** every millisecond before the 302 leaks clicks; the VPS gives the lowest, most predictable latency, zero cold start, no per-invocation billing, trivial custom-domain via Caddy auto-TLS, and KC already operates it. Supabase Edge Functions' ~400ms median cold start makes them wrong for the redirect hop but fine for S2S postback ingestion (warm webhooks, signature verify, DB write). Vercel Hobby's non-commercial restriction and hard-cap pause behavior disqualify it for revenue-bearing redirects. **Pattern:** `go.domain.com/v/{video_id}` → VPS service logs click to Supabase (async, fire-and-forget) → 302 to network link with subID (`tid` for ClickBank, `cid`+`sid1-5` for Digistore24). S2S postbacks hit either a VPS `/postback` route or a Supabase Edge Function; both write to `conversions`.

### 4. Loop-build best practices (2025–2026)
- **The core rule (Anthropic/Boris Cherny):** always give the agent a check it can run (tests/build/lint/smoke) so "the loop closes on its own." Without a verifiable gate, "looks done" is the only signal and the human becomes the verification loop.
- **CLAUDE.md:** keep it lean — only commands, conventions, architecture the agent genuinely lacks; treat every code-review correction as a new rule. Put deep references in `docs/agent-guides/`. Fragile ops (migrations, deploys) get exact commands; flexible ops get principles.
- **Decompose** into endpoint/sprint-sized tasks each with its own external gate; "one giant task rarely converges." Use git checkpoint/rollback before each agent turn.
- **Permissions:** allowlist tightly (`Bash(npm run *)`, `Edit(/src/**)`), use sandbox/`/permissions` wildcards rather than `--dangerously-skip-permissions`. Never silent-commit; always emit evidence (test output, screenshots).
- **n8n as code:** n8n supports Git source control (push/pull workflow JSON + credential stubs; native on Enterprise, or community tooling like **n8n-gitops** CLI and the public n8n API for programmatic import/activate). The agent builds workflows as JSON in the repo and deploys via the n8n REST API (`POST /workflows`, `PATCH .../activate`) — no manual UI. Credentials are excluded from JSON by design and injected via env/secrets (human checkpoint).

## Details

### System overview (text component diagram)
```
                    ┌──────────────────────────────────────────────┐
                    │  n8n (Hetzner CPX11) — orchestrator/cron       │
                    └──────────────────────────────────────────────┘
   (1) Trend-Discovery → (2) Offer-Scoring/Vetting → (0) Compliance-Gate
            │                      │                        │ HIGH=block
            ▼                      ▼                        ▼
   (3) Script/Copy ──► (AI-Disclosure tagger) ──► (4) Image-Gen (Nano Banana $0.039/img)
            │                                              │
            ▼                                              ▼
   (5) Video-Assembly (FFmpeg + edge-tts) ──► (6) Posting (Upload-Post/Blotato)
            │                                   │  human approval gate (Stage 0-2)
            ▼                                   ▼
   Vercel/Supabase frontend (dashboards)    TikTok / IG Reels (C2PA + AI label)
            ▲                                   │
            │                          go.domain.com/v/{id}
   ┌────────┴─────────┐   click 302    ┌────────▼─────────┐
   │  Supabase (PG)   │◄───────────────│ Attribution svc  │ (Caddy + Go/FastAPI on VPS)
   │  offers, videos, │   log click    └────────┬─────────┘
   │  clicks, convs,  │                          │ 302 + subID (tid / cid+sid)
   │  earnings, bandit│◄── S2S postback ─────────┘   to ClickBank/Digistore24/SaaS
   │  compliance_logs │
   └────────┬─────────┘
            │ pollers
   (7) Performance-Analysis ─► (8) Bandit-Allocator (Thompson) ─► (9) Earnings-Reconciliation
                                  feeds offer×creative weights        (network API pollers)
```

### Revised agent architecture (12 components)
**Original 7 (retained):**
1. **Trend-Discovery** — pulls trending topics/sounds/angles; writes candidate themes.
2. **Script/Copy** — PAS/AIDA/Hook-Story-Offer/demonstration templates as prompt files; outputs script + caption + on-screen text. Calls AI-disclosure tagger.
3. **Image-Generation** — Nano Banana (Gemini 2.5 Flash Image) @ **$0.039/image** (Google Developers Blog: "$30.00 per 1 million output tokens with each image being 1290 output tokens ($0.039 per image)").
4. **Video-Assembly** — FFmpeg compositing + edge-tts VO. Embeds visible "AI-generated" on-screen text + retains C2PA metadata.
5. **Posting** — Upload-Post (~$16/mo) or Blotato unified API; sets platform AI toggle ON. Human approval gate in Stages 0–2.
6. **Performance-Analysis** — pulls platform metrics + click/conv data; computes per-creative EPC.
7. **(implicit) Product-Selection** — now formalized as Offer-Scoring below.

**New components:**
0. **Compliance-Gate agent (runs FIRST, before any asset spend).** Tiered FTC claim-risk classifier: **HIGH = hard block** (disease/cure, income/earnings, before-after, "guaranteed"); **MEDIUM = soften + force disclosure**; **LOW = pass**. Inputs: script text, offer category, claim phrases. Writes `compliance_logs` row with verdict + matched rule; HIGH halts the pipeline and flags for human. Health/finance categories auto-escalate scrutiny (FTC priority). Also enforces presence of FTC disclosure string in caption and AI label.
8. **Offer-Scoring/Vetting agent** — rubric as code: `score = 0.30·EPC_norm + 0.20·refund_score + 0.15·commission_norm + 0.15·demo_coherence + 0.10·demand_velocity + 0.10·payout_reliability`. **Hard kill** if refund >15%, gravity <8, HIGH claim-risk, Net-90 payouts, or cookie <14 days. Data sources per field tagged (`feed|scrape|api|manual`) per Finding 2. Re-scores live offers with *actual* EPC/refunds from earnings APIs.
9. **Attribution layer** — VPS redirect service + click logger + S2S postback ingester + Supabase schema (below). Generates per-video subIDs and edge redirects.
10. **Bandit-Allocator agent** — Thompson Sampling over offer×creative arms. Beta(α,β) posterior on conversion; α += conversions, β += (clicks−conversions). **Forced exploration floor:** no arm killed until ≥1,000 clicks OR ≥30 conversions. Allocation weights feed Posting cadence. Guard against **noise-kills** (see risk register).
11. **Earnings-Reconciliation agent** — pollers: ClickBank Analytics API (Clerk key), Digistore24 `listTransactions`, Impact Partner API, PartnerStack Partner API; Rewardful REST API. **Amazon has NO earnings API** → manual CSV import path. Reconciles `conversions` (postback) vs `earnings` (network truth); flags attribution leakage.
12. **AI-Disclosure auto-labeler** — ensures (a) platform AI toggle set on post, (b) visible on-screen "AI-generated" text, (c) C2PA metadata preserved (never stripped), (d) FTC "paid link/#ad" disclosure in caption + audio mention. Writes `compliance_logs`.

### Supabase schema draft (DDL sketch)
```sql
-- networks & offers
create table offers (
  id uuid primary key default gen_random_uuid(),
  network text not null,            -- clickbank|digistore24|partnerstack|impact|rewardful|amazon
  external_id text,                 -- sku / product id
  name text, category text,
  commission_pct numeric, avg_dollar_per_sale numeric,
  gravity numeric, epc_observed numeric,
  refund_rate numeric, cancellation_rate numeric,
  cookie_days int, payout_terms text,        -- e.g. 'NET15','twice-weekly'
  payout_reliability numeric,        -- manual constant 0-1
  source jsonb,                      -- {gravity:'feed', epc:'api', refund:'scrape', ...}
  rubric_score numeric, kill_flags text[],   -- e.g. {'refund>15','gravity<8'}
  status text default 'candidate',   -- candidate|approved|live|killed
  created_at timestamptz default now(), updated_at timestamptz default now()
);
create table videos (
  id uuid primary key default gen_random_uuid(),
  offer_id uuid references offers(id),
  platform text, post_id text,       -- tiktok|instagram + remote id
  script text, caption text, hook_type text,  -- PAS|AIDA|HSO|demo
  ai_labeled bool default false, ftc_disclosed bool default false,
  c2pa_present bool, status text default 'draft', -- draft|approved|posted|removed
  posted_at timestamptz, created_at timestamptz default now()
);
create table clicks (
  id bigserial primary key,
  video_id uuid references videos(id),
  subid text not null,               -- tid / cid+sid composite
  ip_hash text, ua text, country text,
  ts timestamptz default now()
);
create table conversions (
  id bigserial primary key,
  video_id uuid references videos(id),
  subid text, network text, order_id text,
  gross numeric, commission numeric, type text,  -- sale|rebill|refund|chargeback
  is_refund bool default false, ts timestamptz default now(),
  raw jsonb                          -- full postback payload
);
create table earnings (                -- network-truth, from reconciliation pollers
  id bigserial primary key,
  network text, offer_external_id text, subid text,
  period date, commission numeric, refunds numeric, rebills numeric,
  pulled_at timestamptz default now(), raw jsonb
);
create table compliance_logs (
  id bigserial primary key,
  video_id uuid references videos(id),
  stage text,                        -- compliance_gate|ai_labeler
  verdict text,                      -- HIGH|MEDIUM|LOW|PASS|BLOCK
  matched_rules text[], notes text, ts timestamptz default now()
);
create table bandit_state (
  arm_id text primary key,           -- offer_id:creative_id
  offer_id uuid, video_id uuid,
  alpha numeric default 1, beta numeric default 1,
  clicks int default 0, conversions int default 0,
  killed bool default false, last_update timestamptz default now()
);
create table agent_journal (          -- machine-written changelog
  id bigserial primary key, sprint text, agent text,
  action text, decision text, metric jsonb, ts timestamptz default now()
);
```
Add indexes on `clicks(subid)`, `conversions(subid)`, `bandit_state(offer_id)`. Enable RLS; service-role key only in n8n/VPS env (never client).

### Loop-build operating model
**CLAUDE.md structure (repo root):**
```
# Project: autonomous-affiliate
## Commands (exact)
- test: pytest -q   | lint: ruff check . | typecheck: mypy src
- smoke: ./scripts/smoke.sh  (hits /v/health, runs 1 offer-score, 1 mock postback)
- n8n deploy: python scripts/n8n_deploy.py <workflow.json>
## Conventions
- All money math in integer cents. UTC everywhere. Provenance tag on every offer field.
## Architecture
- See ARCHITECTURE.md (this file) + docs/agent-guides/*
## NEVER
- Never post live content, deploy prod, spend money, or commit credentials without a HUMAN-CHECKPOINT tag.
## Definition of done = all gates green + JOURNAL.md updated.
```
**Pre-granted (agent-autonomous) permissions:**
- Create/edit files in `/src`, `/workflows`, `/docs`, `/tests`, `/scripts`.
- Run tests, lint, typecheck, local smoke tests, build.
- Deploy to **staging** n8n instance + staging Supabase branch.
- Read marketplace feeds, run scrapers against public pages (rate-limited).
- Open draft PRs; write JOURNAL.md and agent_journal rows.
- Git commit/rollback on feature branches.

**HUMAN-CHECKPOINT (agent must pause):**
- Entering any account credentials / API keys / OAuth (ClickBank Clerk key, Digistore24 key, Upload-Post, network logins).
- Any spend (paid API tiers, VPS upsize, ad spend).
- Production deploys (prod n8n activate, prod DNS, prod Supabase migration on live data).
- **Posting live content** to TikTok/Instagram (Stages 0–2 mandatory; Stage 3+ may auto-post only LOW-risk, AI-labeled, FTC-disclosed creatives within a daily cap).
- Any creative the Compliance-Gate flags **HIGH**, or MEDIUM that can't be auto-softened.
- Legal/ToS signoffs (network terms, platform automation policy).

**Verification gates (run before any task is "done"):** unit tests green → lint/type clean → schema migration dry-run → smoke test (health 302 <50ms, one offer scored, one mock S2S postback writes a conversion row) → JOURNAL entry appended. A Stop-hook script blocks turn-end until gates pass.

### Sprint plan (Sprint 0 → 6)
- **Sprint 0 — Compliance gate + repo scaffold (Stage 0).** Tasks: CLAUDE.md, repo skeleton, Supabase schema migration, Compliance-Gate classifier + rule tables, AI-disclosure tagger, FTC disclosure templates. **DoD:** classifier unit tests cover HIGH/MEDIUM/LOW corpus; HIGH blocks pipeline; migration applies clean. **Gate:** tests + migration dry-run. **Autonomy:** full. **Checkpoint:** review HIGH ruleset (legal).
- **Sprint 1 — Attribution layer (Stage 1).** VPS Caddy + redirect service, click logger, subID generator, S2S postback ingester, Supabase writes. **DoD:** `/v/{id}` 302 <50ms; mock postbacks write conversions; subID round-trips. **Gate:** smoke + latency test. **Checkpoint:** prod DNS + network postback config (needs account login).
- **Sprint 2 — Offer-Scoring + barbell portfolio (Stage 2).** ClickBank XML feed ingester, Digistore24 + SaaS scrapers, rubric scorer, kill-criteria, provenance tags. **DoD:** scores 3–5 digital + 3–5 recurring SaaS offers; kill flags fire correctly; provenance recorded. **Gate:** scorer unit tests vs fixtures. **Checkpoint:** approve final offer shortlist; enter network keys.
- **Sprint 3 — Content pipeline wiring (n8n as code).** Build Trend→Script→Image→Video→Posting workflows as JSON; deploy via n8n API to staging. **DoD:** end-to-end produces one labeled, disclosed draft video to staging queue. **Gate:** workflow import + dry-run execution. **Checkpoint:** first live post is manual-approve.
- **Sprint 4 — Bandit-Allocator (Stage 3).** Thompson Sampling, exploration floor, allocation→cadence. **DoD:** simulated traffic shows correct exploration floor + convergence; no arm killed before threshold. **Gate:** bandit sim tests. **Checkpoint:** enable auto-posting only for LOW-risk labeled creatives within daily cap.
- **Sprint 5 — Earnings-Reconciliation (Stage 4).** Pollers for all networks + Amazon CSV import; reconcile conversions vs earnings; leakage alerts. **DoD:** reconciliation report matches fixtures; leakage flag triggers. **Gate:** poller integration tests (mocked). **Checkpoint:** live API keys.
- **Sprint 6 — Hardening + observability.** Dashboards, alerting (account health, API deprecation watch), backup/restore, Supabase keep-alive, cost dashboard. **DoD:** alert fires on simulated account-death + attribution gap. **Gate:** chaos smoke. **Checkpoint:** prod cutover.

### JOURNAL.md convention
```
## [SPRINT-N] YYYY-MM-DD — <component>
### What changed
- <files/workflows touched, why>
### Decisions
- <decision> · rationale · alternatives rejected
### Metrics
- tests: X passed · latency p50/p95 · offers scored · conv rows written
### Open questions / TODO
- <blockers, human-checkpoints pending>
### Verification
- gates: [tests ✓] [lint ✓] [smoke ✓] [migration ✓]
```
Mirror key rows into `agent_journal` table for queryable history.

### Cost model (monthly, steady-state)
| Item | Cost |
|---|---|
| Hetzner CPX11 VPS (n8n + attribution svc) | ~$5–6 |
| Upload-Post (unified posting) | ~$16 |
| Supabase | $0 free tier (→ $25 Pro if DB/MAU exceeded) |
| Vercel (dashboards) | $0 Hobby for personal dashboards; Pro $20 if commercial frontend |
| Nano Banana images | $0.039/img × volume (e.g. 300 imgs = ~$11.70) |
| edge-tts / FFmpeg | $0 |
| ClickBank/Digistore24/SaaS network APIs | $0 |
| TikTok seller insurance | $0 (creator-only); ~$29 if Shop seller |
| **Baseline total** | **~$22–40/mo** + image volume |

New components add **near-zero** marginal cost (attribution on existing VPS; pollers in n8n; bandit in Supabase). First scale cost is Supabase Pro ($25) when clicks/DB exceed free tier (~100k clicks/mo is comfortably within free egress but watch row counts).

### Risk register (autonomous-operation specific)
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Account death** (TikTok/IG ban from automation/AI-policy/posting-cap breach) | High | High | Self-label all AI; respect May-11-2026 daily cap; keep posting human-gated until Stage 3; multiple accounts; don't put TikTok Shop on critical path; lead with link-in-bio to Digistore24/ClickBank. |
| **Attribution leakage** (clicks lost, subID stripped, postback missed) | Med | High | VPS persistent redirect (no cold start); async non-blocking click log; reconcile conversions vs earnings API nightly; alert if earnings>>tracked conversions. |
| **Bandit noise-kills** (arm killed on small-sample variance) | Med | Med | Hard exploration floor (≥1,000 clicks OR ≥30 conv); Beta priors α=β=1; never kill on EPC alone before threshold; weekly human review of kills. |
| **API deprecation** (network changes feed/endpoint; ClickBank help-center migration may move XML feed) | Med | High | Provenance tags + source-health check job; verify feed URL on each run; fail-soft to manual entry; version-pin scrapers; deprecation-watch alert. |
| **Scraper breakage / blocking** (Digistore24, SaaS pages) | High | Med | Rate-limit, cache last-good, alert on parse failure; manual fallback path; never hard-depend on scrape for kill decisions. |
| **Compliance miss** (HIGH claim slips through) | Low | Very High | Hard block + human checkpoint on HIGH; keyword + semantic classifier; FTC health/income priority escalation; audit log. |
| **Agent runaway** (loops, prod changes, spend) | Med | High | Tight allowlist; staging-only autonomy; Stop-hook gates; git checkpoint/rollback; HUMAN-CHECKPOINT tags on spend/prod/post. |
| **Supabase free-tier pause** (7-day inactivity / caps) | Low | Med | Daily keep-alive ping; monitor row counts/egress; upgrade trigger at 40k MAU / 400MB DB. |

## Recommendations
1. **Build in the staged order (Sprint 0→6); do not skip Compliance-Gate first.** It is the cheapest insurance against the highest-impact risk (account death + FTC). Benchmark to advance: classifier passes a labeled HIGH/MEDIUM/LOW corpus with zero HIGH false-negatives.
2. **Host attribution on the VPS now.** Threshold to revisit: if p95 redirect latency >100ms or VPS CPU sustained >70%, move redirect to a second small VPS or Cloudflare Worker (not Vercel Hobby — commercial-use rule).
3. **Treat TikTok Shop as deferred.** Until KC clears 5,000 followers AND the daily-posting-cap economics are validated, run TikTok/IG as top-of-funnel driving to link-in-bio → VPS redirect → Digistore24/ClickBank. Re-evaluate when an account graduates the Pilot and a creative shows >4% CVR.
4. **Engineer the Offer-Scoring agent around feed+scrape, not an API that doesn't exist.** Ship ClickBank XML-feed ingest first (highest-fidelity, lowest-effort), Digistore24 scrape second, SaaS semi-manual third. Backfill real EPC/refunds from earnings APIs once offers go live; let those override feed/scrape estimates in the rubric.
5. **Keep posting human-gated through Stage 2.** Only enable auto-posting in Stage 3 for LOW-risk, AI-labeled, FTC-disclosed creatives within the platform daily cap. Threshold to widen autonomy: 30 consecutive clean human-approved posts with zero compliance flags.
6. **Run reconciliation from day one of live traffic.** If network-reported earnings exceed tracked conversions by >15%, treat as attribution leakage and freeze bandit kill decisions until resolved.

## Caveats
- **Fast-moving rules:** TikTok Shop eligibility, the May-11-2026 daily posting cap, insurance status, and AI-labeling enforcement change quarterly; several figures (follower thresholds, CHR ~176, pilot caps) come from secondary trackers, not all from TikTok's primary policy pages — re-verify against TikTok Seller Center before relying on them. The C2PA integration date is **May 9, 2024** per TikTok's own newsroom (some trackers wrongly cite Jan 2025). The EU AI Act Art. 50 and California SB 942 (both Aug 2, 2026) add machine-readable labeling obligations if KC targets EU/CA audiences.
- **ClickBank XML feed:** its existence/URL is corroborated by ClickBank forum posts and third-party tools but is not prominently documented on the migrated help center; confirm it is still live and that gravity/Avg$ fields are present before architecting the scorer around it. CBEngine refund figures are estimates, not official.
- **PartnerStack scale:** partner-count figures vary across PartnerStack's own pages (65,000–80,000+ active partners, 300+ programs) and third-party blogs cite higher numbers; treat the marketplace as a real but imperfectly-quantified discovery surface, not a precise database.
- **Scraping fragility & ToS:** Digistore24/SaaS marketplace scraping can break or violate terms; keep a manual-entry fallback and rate-limit politely. None of this is legal advice — network/platform ToS and FTC compliance should get a human/legal signoff (a defined checkpoint).
- **n8n source control:** native Git source control is an Enterprise feature; the community path (n8n-gitops CLI / public API import) works for a solo operator but is a workaround, not first-class GitOps — expect some manual credential re-entry on deploys.
- **Bandit assumptions:** Thompson Sampling assumes roughly stationary conversion rates; viral spikes and seasonality violate this — the exploration floor and weekly human review exist precisely to prevent over-confident kills on noisy, non-stationary data.
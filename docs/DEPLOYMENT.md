# DEPLOYMENT — Step-by-step (Stage 0 → live staging)
<!-- 2026-06-09: VPS switched Hetzner → DigitalOcean (Hetzner signup friction).
     Stack is provider-agnostic; only §2 changed. Cost baseline +$6/mo vs CPX11. -->

Status: Supabase DONE ✓ (project `affiliate-pipeline`, ref `ecvmubsvtbranzwviepp`,
url `https://ecvmubsvtbranzwviepp.supabase.co`, 8 tables, RLS on).
Everything below is HUMAN-CHECKPOINT work — accounts, payments, secrets.

## 1. Domain (~$10/yr)
Buy any cheap domain (Namecheap/Cloudflare/Porkbun). You need two subdomains:
- `n8n.<domain>` → n8n editor/webhooks
- `go.<domain>`  → click redirect service (this appears in your link-in-bio)
Pick something short/neutral — `go.` links are user-visible.

## 2. DigitalOcean VPS (~$12/mo) — replaces Hetzner (signup friction)
1. Sign up at digitalocean.com (Google login or card/PayPal works instantly).
2. Create → Droplets:
   - Region: **New York (NYC1/NYC3)** — closest to Supabase us-east-1.
   - Image: **Ubuntu 24.04 LTS**.
   - Size: Basic → Regular → **2 GB / 1 vCPU ($12/mo)** (FFmpeg needs the 2GB headroom).
   - Authentication: **SSH key** → on Windows run `ssh-keygen -t ed25519` in PowerShell
     (Enter through prompts), then paste the contents of `C:\Users\Prabh\.ssh\id_ed25519.pub`.
     (Password auth also works if you prefer — pick "Password" and set a strong one.)
3. Note the Droplet's IP. At your DNS provider create two A records:
   `n8n` → <droplet IP>, `go` → <droplet IP> (proxy/CDN OFF — Caddy needs direct TLS).

## 3. Server bootstrap (run via SSH: `ssh root@<IP>`)
```bash
apt update && apt upgrade -y
apt install -y docker.io docker-compose-v2 git ufw
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
git clone https://github.com/kcdream0913-hub/Affiliate-Marketing.git /opt/affiliate
cd /opt/affiliate/deploy
cp .env.example .env
nano .env        # fill every value — see §4
docker compose up -d
docker compose ps  # all 4 services should be healthy
```
Smoke checks:
- `https://n8n.<domain>` loads the n8n setup screen (create owner account).
- `curl -I https://go.<domain>/health` → 200.

## 4. .env values
| Var | Where to get it |
|---|---|
| DOMAIN | your domain, e.g. `kcgo.io` |
| POSTGRES_PASSWORD / N8N_ENCRYPTION_KEY / IP_SALT | generate: `openssl rand -hex 24` |
| SUPABASE_URL | `https://ecvmubsvtbranzwviepp.supabase.co` |
| SUPABASE_SERVICE_KEY | Supabase Dashboard → Project Settings → API keys → `service_role` (NEVER commit) |
| DS24_IPN_PASSPHRASE | you invent it; set the same value in Digistore24 IPN settings (§6) |
| CB_INS_SECRET | you invent it (16+ chars); set same in ClickBank INS settings (§6) |

## 5. Accounts & API keys (free/cheap tiers)
| Service | Purpose | Step |
|---|---|---|
| Telegram | approval gate | Message @BotFather → /newbot → save token. Message your bot once, then GET `api.telegram.org/bot<TOKEN>/getUpdates` for your chat_id |
| OpenRouter | LLM (scripts/ranking) | openrouter.ai → key → load $5 |
| Google AI Studio | Nano Banana images | aistudio.google.com → API key (billing on; ~$0.039/img) |
| Apify | trend scraping | apify.com free plan → token |
| Upload-Post | TikTok/IG posting | upload-post.com → connect accounts → API key (free tier first) |

In n8n (https://n8n.<domain>) create credentials with EXACTLY these names
(workflows reference them by name):
`Apify Header Auth`, `OpenRouter Header Auth`, `Gemini API Key Query`,
`Supabase Service Auth` (Header Auth: `apikey: <service_role>` + `Authorization: Bearer <service_role>`),
`Telegram Bot`, `Upload-Post Header Auth`.
Also set n8n env vars (compose: add to n8n service): `SUPABASE_URL`, `TELEGRAM_CHAT_ID`.

Deploy workflows from your PC (or the VPS):
```bash
export N8N_URL=https://n8n.<domain>  N8N_API_KEY=<n8n Settings → API key>
python scripts/n8n_deploy.py workflows/01-trend-discovery.json
python scripts/n8n_deploy.py workflows/02-script-copy.json
python scripts/n8n_deploy.py workflows/03-image-generation.json
python scripts/n8n_deploy.py workflows/04-video-assembly.json
python scripts/n8n_deploy.py workflows/05-posting-approval.json
# activate only after credentials test green (HUMAN-CHECKPOINT):
python scripts/n8n_deploy.py workflows/01-trend-discovery.json --activate
```

## 6. Affiliate networks (the money layer)
| Network | Signup | Then |
|---|---|---|
| ClickBank | clickbank.com → affiliate account (nickname = your ID) | Settings → My Site → Instant Notifications: URL `https://go.<domain>/postback/clickbank`, secret = CB_INS_SECRET. API: Settings → API keys → create Clerk key |
| Digistore24 | digistore24.com → affiliate | Settings → IPN: URL `https://go.<domain>/postback/digistore24`, passphrase = DS24_IPN_PASSPHRASE, sha_sign on. API: Settings → API keys (readonly) |
| PartnerStack | market.partnerstack.com | Apply to 3-5 SaaS programs (20-40% recurring); Partner API key from settings |
| Link-in-bio | linktr.ee (or a page on your domain) | Single CTA target: `https://go.<domain>/v/<video_id>` per active video |

## 7. Social accounts (warming rules apply from day 1)
- New TikTok + Instagram accounts (or existing). 1-3 posts/day max, 2-4h apart,
  for the first 2-3 weeks. Human-approve EVERY post via the Telegram gate (Stages 0-2).
- Set the platform AI-content toggle ON for every post (Upload-Post does this via API;
  verify on the first 3 posts manually).

## 8. Go-live order (maps to JOURNAL checkpoints)
1. Domain + VPS + DNS (§1-3) → smoke green.
2. n8n owner account + credentials (§5) → deploy workflows (staging, not activated).
3. KC legal review of src/compliance/rules.py HIGH ruleset.
4. Network signups (§6) → postback URLs configured → fire test postback → conversion row appears in Supabase.
5. Offer shortlist: run feed ingest + scorer → KC approves 3-5 offers → offers.json + DB.
6. First end-to-end draft video → Telegram approval → first live post.
7. Daily: reconciliation + bandit update crons (Sprint 6 wiring).

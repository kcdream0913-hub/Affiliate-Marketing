-- 001_initial_schema.sql — autonomous-affiliate initial schema
-- Source: ARCHITECTURE.md (2026-06-09). Money in numeric for network-reported values;
-- internal computations convert to integer cents per CLAUDE.md convention.

create extension if not exists pgcrypto;

-- networks & offers
create table if not exists offers (
  id uuid primary key default gen_random_uuid(),
  network text not null,            -- clickbank|digistore24|partnerstack|impact|rewardful|amazon
  external_id text,                 -- sku / product id
  name text,
  category text,
  commission_pct numeric,
  avg_dollar_per_sale numeric,
  gravity numeric,
  epc_observed numeric,
  refund_rate numeric,
  cancellation_rate numeric,
  cookie_days int,
  payout_terms text,                -- e.g. 'NET15','twice-weekly'
  payout_reliability numeric,       -- manual constant 0-1
  source jsonb,                     -- {"gravity":"feed","epc":"api","refund":"scrape",...}
  rubric_score numeric,
  kill_flags text[],                -- e.g. {'refund>15','gravity<8'}
  status text not null default 'candidate',  -- candidate|approved|live|killed
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists videos (
  id uuid primary key default gen_random_uuid(),
  offer_id uuid references offers(id),
  platform text,                    -- tiktok|instagram
  post_id text,                     -- remote id
  script text,
  caption text,
  hook_type text,                   -- PAS|AIDA|HSO|demo
  ai_labeled bool not null default false,
  ftc_disclosed bool not null default false,
  c2pa_present bool,
  status text not null default 'draft',  -- draft|approved|posted|removed
  posted_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists clicks (
  id bigserial primary key,
  video_id uuid references videos(id),
  subid text not null,              -- tid / cid+sid composite
  ip_hash text,
  ua text,
  country text,
  ts timestamptz not null default now()
);

create table if not exists conversions (
  id bigserial primary key,
  video_id uuid references videos(id),
  subid text,
  network text,
  order_id text,
  gross numeric,
  commission numeric,
  type text,                        -- sale|rebill|refund|chargeback
  is_refund bool not null default false,
  ts timestamptz not null default now(),
  raw jsonb                         -- full postback payload
);

create table if not exists earnings (  -- network-truth, from reconciliation pollers
  id bigserial primary key,
  network text,
  offer_external_id text,
  subid text,
  period date,
  commission numeric,
  refunds numeric,
  rebills numeric,
  pulled_at timestamptz not null default now(),
  raw jsonb
);

create table if not exists compliance_logs (
  id bigserial primary key,
  video_id uuid references videos(id),
  stage text,                       -- compliance_gate|ai_labeler
  verdict text,                     -- HIGH|MEDIUM|LOW|PASS|BLOCK
  matched_rules text[],
  notes text,
  ts timestamptz not null default now()
);

create table if not exists bandit_state (
  arm_id text primary key,          -- offer_id:creative_id
  offer_id uuid,
  video_id uuid,
  alpha numeric not null default 1,
  beta numeric not null default 1,
  clicks int not null default 0,
  conversions int not null default 0,
  killed bool not null default false,
  last_update timestamptz not null default now()
);

create table if not exists agent_journal (  -- machine-written changelog
  id bigserial primary key,
  sprint text,
  agent text,
  action text,
  decision text,
  metric jsonb,
  ts timestamptz not null default now()
);

-- indexes
create index if not exists idx_clicks_subid on clicks (subid);
create index if not exists idx_clicks_video on clicks (video_id);
create index if not exists idx_conversions_subid on conversions (subid);
create index if not exists idx_conversions_video on conversions (video_id);
create index if not exists idx_bandit_offer on bandit_state (offer_id);
create index if not exists idx_offers_status on offers (status);
create index if not exists idx_earnings_period on earnings (network, period);

-- RLS: deny-all by default; service-role key (n8n/VPS env only) bypasses RLS.
alter table offers enable row level security;
alter table videos enable row level security;
alter table clicks enable row level security;
alter table conversions enable row level security;
alter table earnings enable row level security;
alter table compliance_logs enable row level security;
alter table bandit_state enable row level security;
alter table agent_journal enable row level security;

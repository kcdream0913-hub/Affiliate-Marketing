# The Affiliate-Side Knowledge Layer: A Decision-Grade Operating Manual for an Autonomous Affiliate Platform

## TL;DR

- **Build the offer-selection engine around verifiable affiliate-economic signals (EPC, refund/cancellation rate, commission structure, payout reliability) — NOT vanity popularity metrics like ClickBank Gravity, which is openly gamed and tells you nothing about whether YOUR traffic will convert.** Treat every offer as a hypothesis to be killed or scaled on its own per-creative EPC and revenue-per-1k-views, and accept that statistically valid kill/scale decisions need ~30–50+ conversions per arm, which at realistic conversion rates means tens of thousands of views per offer.
- **The single biggest structural risk to an AI-generated, autonomous operation is not picking a bad niche — it is account death.** Health, weight-loss, income/"make-money," and before/after claims carry the highest FTC substantiation risk AND the highest platform-ban risk, and TikTok's C2PA-based auto-detection (integrated January 2025, having labeled over 1.3 billion videos to date) now flags AI media automatically. Your compliance-checking agent (claim detection before posting) is the highest-leverage piece of automation you can build, and it must be a hard gate, not a soft warning.
- **For a solo automation-heavy operator, the highest-EV portfolio is a barbell: recurring-commission SaaS programs (20–40% lifetime/12-month, low-follower-friendly, clean partner APIs via PartnerStack/Impact/Rewardful) for compounding MRR, paired with high-AOV digital offers (Digistore24/ClickBank) for fast cash and fast test signal.** TikTok Shop is viable but gated (1,000-follower US affiliate threshold, identity verification, 30-day pilot with 5-video/week cap) and has the thinnest per-unit economics. Earnings reconciliation is fully automatable on ClickBank, Digistore24, Impact, and PartnerStack; Amazon has NO earnings API.

---

## Key Findings

1. **ClickBank Gravity is a momentum/competition proxy, not a quality or conversion signal, and it is actively manipulated.** Use it only as a coarse "is this alive" filter. The real selection signals are EPC, refund/cancellation rate, commission structure, and AOV.
2. **A solo operator can pull most vetting signals programmatically.** ClickBank exposes Avg $/sale, initial $/sale, Avg %/sale, and Gravity on listings; Digistore24 exposes EPC, cart conversion, and cancellation rate. Both have affiliate APIs. This means offer vetting can be coded as a scored pipeline.
3. **Refund/cancellation rate is the "silent assassin" of EPC** — under RevShare it is deducted directly from your commission. A >10% refund rate warrants scrutiny; TikTok Shop now enforces category Seller-Fault Return/Refund thresholds (e.g., <2.5% for FMCG) for affiliate eligibility.
4. **Recurring SaaS is the structurally best fit for a solo automator,** but the base rates are humbling: per Rewardful's "State of SaaS Affiliate Programs" report (analyzing $68.4M in affiliate revenue), the average affiliate commission rate is **24.16%**, the average referral-to-sale conversion rate is **0.8%** ("8 out of every 1,000 referred visitors become paying customers"), the average payout per commission is **$14.10**, and the report's own headline finding is that "Most Affiliate Programs Fail After 6 Months." The win comes from low churn + compounding cohorts over 6–9 months.
5. **TikTok Shop 2025–2026 reality:** US affiliate (marketplace promotion) generally requires 1,000 followers for the Affiliate Links/basic path and 5,000 for full Product Marketplace access depending on creator type; mandatory identity verification; a 30-day pilot program capping new creators at 5 shoppable videos/week; commissions typically 5–20% (beauty/supplements 15–25%).
6. **Attribution is achievable per-creative via SID/TID parameters + a self-hosted redirect layer logging to Supabase, plus S2S postbacks where available** (Digistore24 cid + sid1–5; ClickBank TID via Instant Notification/postback). Amazon and some networks are weaker. Link cloaking is allowed by ClickBank/Digistore24/CJ but the destination must match the promise; "ad cloaking" (showing reviewers different content than users) is a bannable offense and must never be confused with URL cloaking.
7. **Copywriting frameworks that survive compliance:** PAS, AIDA, Hook-Story-Offer, and demonstration/UGC formats, with the hook carrying the load — the first 3 seconds determine ~71% of scroll-or-stay decisions and retention is the primary distribution lever. The conversion-relevant move is curiosity-gap + specific-claim hooks feeding a congruent pre-sell/bridge page.
8. **Earnings APIs:** ClickBank (Analytics API, affiliate role, Clerk Key), Digistore24 (listTransactions), Impact (Partner API, Account SID + Auth Token), and PartnerStack (Partner API, Bearer token) all support automated affiliate earnings pulls. Amazon Associates has NO earnings API — report downloads only — and PA-API is being deprecated in 2026.

---

## Details

### 1. Niche/Offer Selection Framework (niche-agnostic)

**1.1 Why Gravity is a trap (and how to use it anyway)**

ClickBank Gravity counts unique affiliates who earned a commission on an offer in a rolling ~12-week window, weighted toward recent sales (each affiliate contributes between 0.1 and 1.0 depending on recency). It is explicitly described by ClickBank as "agnostic from revenue." Three consequences matter for you:

- **It measures competition as much as opportunity.** High gravity = many affiliates already winning = a crowded angle space. A "good gravity" band of roughly 20–100 is the commonly cited sweet spot for balancing proof-of-conversion against saturation; below ~5 means almost nobody is making it work.
- **It is gameable.** Practitioners on industry forums describe propping up gravity by running paid traffic through multiple ClickBank accounts via cheap URL rotators — meaning a 400+ gravity offer can still convert at 0% for you. One documented forum experiment sent 684 clicks straight to a 400+ gravity merchant's sales page with 94 order-form impressions and zero sales.
- **It is NOT a quality signal.** A high-gravity product can have a poor conversion ratio and a high refund rate simultaneously.

**Operating rule:** Gravity is a binary liveness filter (`gravity >= 8 AND gravity <= 150`), never a ranking input. Rank on economics.

**1.2 The signals that actually predict your outcome**

| Signal | Where to get it | What good looks like | Why it matters |
|---|---|---|---|
| **EPC (earnings/click)** | Digistore24 listing; ClickBank Avg $/sale × conversion; your own redirect logs | >$1 EPC as a baseline aspiration (traffic-dependent) | The single best cross-offer comparator; revenue ÷ clicks |
| **Refund / cancellation rate** | Digistore24 cockpit; ClickBank; ask vendor for 90-day stats | <10%; ideally <5% | Under RevShare, refunds are clawed back from you directly |
| **Cart conversion rate** | Digistore24 | 1–3% cold-traffic CR is the Digistore24-cited norm | Separates "sales page problem" from "checkout problem" |
| **AOV + upsell flow** | Vendor sales page; Avg $/sale vs initial $/sale | Higher AOV = more commission room | One-click upsells/rebills push you past breakeven |
| **Commission structure** | Network listing | RevShare for digital; CPA where you can negotiate it | Determines refund exposure and cash-flow timing |
| **Cookie / attribution window** | Network terms | 60 days (ClickBank std) to 180 days (Digistore24) | Longer = more credited conversions |

**CPA vs RevShare vs hybrid:** Under **RevShare** you share the upside (and the refund downside — refunds are deducted from commissions). Under **CPA** the vendor absorbs refund cost, but a high refund rate from your traffic can still get you flagged or removed. **Hybrid** (CPA + smaller rev-share) is the affiliate-friendliest where available. For an autonomous operation that cannot babysit disputes, CPA reduces clawback variance but RevShare on a low-refund, high-AOV offer with rebills usually has the higher ceiling.

**1.3 Demand & competition validation a solo dev can pull programmatically**

- **Search/trend velocity:** Google Trends (unofficial pytrends), keyword APIs, and the networks' own "new/trending" lists. The signal you want is *rising* interest, not absolute volume.
- **Competition density:** Gravity (CB), sales rank/popularity (Digistore24), and a count of existing short-form videos on the angle. High density isn't disqualifying if you have a differentiated hook, but it raises the creative bar.
- **Offer–niche–content coherence:** Score how natural the product is to *demonstrate* in 8–30 seconds of vertical video. Products with visible transformation (before/after, messy→organized) convert best on short-form because the format rewards visual proof.

**1.4 A concrete, codeable scoring rubric**

Score each candidate offer 0–100. Suggested weighted model (tune weights to your data):

```
offer_score =
   0.30 * EPC_score          # normalized EPC vs category benchmark
 + 0.20 * refund_score       # (1 - refund_rate), hard-capped
 + 0.15 * commission_score   # $ per conversion incl. rebills/upsells
 + 0.15 * demo_coherence     # 0-1, how well it shows in <30s vertical video
 + 0.10 * demand_velocity    # trend slope
 + 0.10 * payout_reliability # network/vendor reputation score

KILL CRITERIA (any one => reject, regardless of score):
 - refund_rate > 15%
 - gravity < 8 (CB) or no sales history (DS24)
 - claim_risk_class == "HIGH"  (see §2.3)
 - payout terms: Net-90, or holdbacks > 60 days, or no real-time dashboard
 - cookie window < 14 days
 - commission resets on plan downgrade (SaaS)
```

For short-form video traffic specifically, the evidence says winners share: **(1) a one-sentence "big idea" hook** ("a 30-second breakfast tweak…" beats "a 12-module course"), **(2) pre-sell/angle congruency** between video → bridge → sales page, and **(3) impulse-priced, visually demonstrable products**. ClickBank's own team states some affiliates "almost doubled their EPCs just by tweaking their pages for better congruency."

### 2. Offer-Vetting Mechanics (avoiding garbage offers)

**2.1 Programmatic + manual quality checks**

- **Refund/chargeback signals:** Pull refund/cancellation rate from the network; for ClickBank, the Analytics API exposes net vs gross (net = gross − chargebacks − refunds). A widening gap between gross and net earnings is your automated red flag.
- **Sales-page quality:** Automatable proxies — page load speed, mobile responsiveness, presence of a VSL, checkout step count, and whether the order form offers multiple payment methods (Digistore24 notes ~45% of transactions come via PayPal). A human (or a vision model) spot-checks the top-scoring offers before they enter rotation.
- **Vendor reputation research:** Search the vendor/product name + "refund," "scam," "chargeback," "lawsuit." Note the documented legal exposure of the category itself: a German consumer association (vzbv) sued Digistore24 over unclear subscription terms, and the Hildesheim court restricted certain practices in 2023 — a reminder that subscription-trap offers carry brand/legal risk even when the network is legitimate.

**2.2 Affiliate program terms that actually matter**

Red flags that predict clawbacks or non-payment (treat 2+ as disqualifying):
- Cookie duration < 14 days
- No real-time tracking dashboard (you cannot win disputes you cannot see)
- Net-90 payment terms (legitimate programs pay Net-30/Net-45)
- Vague or absent brand-bidding policy
- Commission structure that resets on plan downgrades (SaaS)
- In-house tracking with no third-party audit trail (vs Impact/PartnerStack/Rewardful/FirstPromoter, which give audit-ready data)

**2.3 FTC claim-risk classification (the account-survival layer)**

The FTC standard: every objective claim — express OR implied — must be substantiated *before* dissemination, and for health claims the bar is "competent and reliable scientific evidence," generally **randomized controlled human clinical trials** for disease claims. Critically for you: **the affiliate/endorser is independently liable** for deceptive or unsubstantiated claims, even if the vendor would also be liable, and "results not typical" disclaimers are generally considered insufficient to cure an otherwise-misleading claim.

Build your Script/Copy agent's claim-detection gate around a tiered risk model:

| Risk class | Claim types | Policy for an AI-generated autonomous op |
|---|---|---|
| **HIGH (avoid/hard-block)** | Disease cure/treatment/prevention; "clinically proven"/"studies show" without the study; income/earnings claims ("make $10k/mo"); before/after body transformations; "guaranteed results" | Block at generation. These carry the FTC's heaviest enforcement and highest platform-ban risk (see enforcement note below) |
| **MEDIUM (allow with structure)** | Structure/function claims ("supports energy"); general wellness; testimonials with typical-results context | Require disclosure + softened phrasing + no implied medical outcome |
| **LOW (allow)** | Demonstrable product features; price/availability; convenience; subjective opinion ("I love the design") | Standard FTC affiliate disclosure only |

**Enforcement reality (why HIGH is a hard block):** In *FTC v. Traffic and Funnels, LLC* (filed Dec 5, 2023, M.D. Tenn.; settled January 2025), the proposed orders carried a **$16,363,073.11 monetary judgment** (partially suspended), with Taylor Welch turning over **$600,000** and Christopher Evans **$400,000** (the ~$1M consumer-refund figure). Per the FTC, "Traffic and Funnels lured people looking to work and earn an income with false or unfounded earnings claims, even after receiving legal notices from the FTC" (Samuel Levine, Director, FTC Bureau of Consumer Protection). Separately, on **April 13, 2023** the FTC sent a Notice of Penalty Offenses Concerning Substantiation of Product Claims to roughly **670 companies** marketing OTC drugs, homeopathic products, dietary supplements and functional foods, exposing them to civil penalties of **up to $50,120 per violation**; the notice requires "at least one well-controlled human clinical trial to support claims that a product is effective in curing, mitigating, or treating a serious disease."

The detection logic: a regex/LLM-classifier pass over every generated script and caption that flags HIGH-risk lexemes (cure, heal, lose X lbs, guaranteed, proven, $/income, before-after) and routes to block or human review. **This is the single most important automation you build** — one wrong category can end the account.

### 3. Recurring SaaS Affiliate Programs (the under-covered, high-fit layer)

**3.1 Why this fits a solo automator best**

You do the content work once; a low-churn SaaS referral pays every month. The economics compound where info-product one-time commissions do not. Programs are findable on **PartnerStack** (marketplace; 116,000+ partners), **Impact**, **FirstPromoter**, **Rewardful** (Stripe-native), and direct/in-house pages (footer → "Affiliate Program").

**3.2 Representative terms (illustrative, verify before promoting)**

| Program | Commission | Cookie | Platform |
|---|---|---|---|
| GetResponse | 33% recurring lifetime | 120 days | In-house |
| ActiveCampaign | 20–30% recurring lifetime (tiered) | 90 days | PartnerStack |
| ClickFunnels | 30–40% recurring lifetime | 45 days | FirstPromoter |
| Leadpages | 10–50% recurring lifetime (tiered) | 90 days | Impact |
| LiveChat | 20% recurring for life | 120 days | PartnerStack |
| Copy.ai | 45% recurring (12 mo) | 60 days | FirstPromoter |

20–40% recurring is the solid band for SaaS. The real driver is **retention**: 20% on a low-churn, business-critical tool beats 40% on a high-churn "nice-to-have."

**3.3 Approval difficulty for low-follower accounts**

Most platform-run SaaS programs (PartnerStack/Impact/Rewardful) approve based on a basic application + content channel, not follower count — far more accessible than gated TikTok Shop categories. This is a genuine edge for a new, automation-first operator with no audience.

**3.4 The LTV math and realistic income curve**

Recurring affiliate LTV per referral ≈ `monthly_commission ÷ monthly_churn`. Example: $40/mo plan × 25% = $10/mo commission; at 5% monthly churn, expected lifetime ≈ 1/0.05 = 20 months → LTV ≈ $200/referral.

Cohort dynamics (the honest base rate): new MRR each month = `traffic × CTR × CVR × commission`. With the Rewardful-benchmarked ~0.8% SaaS referral-to-sale CR and ~$14.10 average payout per commission, you need real traffic volume to move the needle. Cohorts stack but decay at the churn rate; you reach a steady state where new MRR offsets churned MRR after roughly **3–9 months**. One worked industry model showed a low-churn (3%) business-critical SaaS stabilizing around $13–15k/mo commission MRR after 6 months of consistent cohort-stacking — but that assumes sustained, converting traffic, which is the hard part. Most SaaS affiliate programs fail to reach regular payout scale at all (Rewardful's report found most programs fail after 6 months).

### 4. TikTok Shop Affiliate Economics & Mechanics (2025–2026)

**4.1 Eligibility (US)**
- **Affiliate creator:** 1,000 followers, 18+, US-based, clean account standing, identity verification (gov ID + selfie). The **Affiliate Links / Linkshare** path has no follower requirement in some regions but with restricted features.
- **Marketing creator (full Product Marketplace):** 5,000 followers in the US.
- **30-day Pilot Program** for new/under-5,000 creators: access only to products with Shop Performance Score ≥95%, cap of **5 shoppable videos + 3 LIVEs per week**, no campaign eligibility. To graduate: reach 176 Creator Health Rating points OR ≤1 violation point; OR publish 6+ shoppable videos; OR generate 10 orders. The 5-video/week cap lifts only at 5,000 followers.

**4.2 Commission ranges & collaboration models**
- Category benchmarks: overall **2–20%**; beauty/personal care highest; beauty & supplements typically **15–25%**; apparel **10–20%**; electronics lowest. Payouts settle **15–30 days after delivery** (return-window protection).
- **Open Collaboration:** self-service, any eligible creator, globally set rate (often 10–15% base). **Targeted Collaboration:** invite-only, negotiable (18–25%+, up to 50% for top performers).

**4.3 In-video links vs link-in-bio**
Native in-video product tags remove the link-in-bio friction step entirely and reportedly increase conversion 45–65% vs external-link strategies; LIVE shopping converts ~50% higher than standard video. This is TikTok Shop's structural advantage — but it locks revenue inside TikTok's settlement system and account-health regime.

**4.4 AI-content policy (critical for an AI-generated pipeline)**
TikTok requires disclosure (self-label toggle, on-screen text, or sticker) when AI **generates or significantly edits realistic** images/audio/video. **Exempt:** AI script writing, captions, hashtags, text overlays — i.e., your text/planning layer. **Required:** synthetic faces/voices, AI avatars, AI-generated product imagery/backgrounds. TikTok integrated **C2PA Content Credentials in January 2025** (first major platform to do so) and per its Newsroom uses "labeling tools…our own detection models…[and] C2PA Content Credentials" which "helped label over **1.3 billion videos** to date" — and it can auto-label even without self-disclosure. Official position: the AIGC label is "a disclosure mechanism, not a distribution signal" — properly labeled AI content remains monetizable, but **undisclosed** synthetic media risks distribution reduction, removal, **permanent loss of commission-withdrawal privileges, or account ban.** For TikTok Shop product imagery specifically, fully synthetic product images must be disclosed; AI-enhanced authentic photos sit in a grayer zone.

**4.5 Account-health system**
Creator Health Rating (CHR) and violation points govern standing; Shop Performance Score (SPS) governs which products you can promote (shop disqualified from Affiliate Marketing if SPS < 3). Sharing login info with high-violation accounts is itself a disqualifier.

**4.6 Realistic solo-operator entry path**
Start in the pilot, target high-completion content (algorithm rewards watch time over follower count), promote only SPS≥95% products, accumulate the 10 orders / 6 videos to graduate, label all AI media. First payout from a zero-follower start typically takes 45–60 days including the follower ramp, review, and commission hold.

### 5. Conversion & Attribution Infrastructure

**5.1 Per-network sub-ID/SID parameters (this is what makes per-creative attribution possible)**

| Network | Parameter | Notes |
|---|---|---|
| ClickBank | `tid` (TID) | Alphanumeric; appears in commission reports' TID column; pass via HopLink/Direct Tracking Link. Also new affiliate tracking params + S2S postback via Instant Notification (INS v8) |
| Digistore24 | `cid` (click ID) + `sid1`–`sid5` | URL form `checkout-ds24.com/redir/[PRODUCT]/[AFFILIATE]/[CAMPAIGNKEY]?cid={click_id}&sid1=...`; uppercase/lowercase letters only — mind the char limit |
| Impact | sub-IDs via Partner API | Action-level reporting with payout |
| PartnerStack | sub-IDs (clunky, no standard UTM) | Server-to-server on your own domain recommended |
| Amazon | tracking ID (store ID, `-20` US) | Cannot cloak in a way that hides Amazon; weak per-creative granularity |

**5.2 The thin redirect/landing layer (Vercel + Supabase)**

Architecture for per-creative attribution:
1. Each video gets a unique short slug on your domain: `go.yourdomain.com/v/{video_id}`.
2. The Vercel edge function logs `{video_id, timestamp, geo, UA, referrer}` to Supabase, generates/forwards a click ID, and 302-redirects to the network link with `tid`/`cid`/`sid1` = `{video_id}`.
3. The network's S2S postback (Digistore24 S2S, ClickBank INS) fires the conversion back to a Supabase webhook endpoint, matched on click ID → revenue attributed to the exact video.

**Cloaking compliance:** This is "white-hat" URL cloaking (clean branded redirect, destination matches the promise) — explicitly allowed by ClickBank, Digistore24, and CJ. **It is categorically different from "ad cloaking"** (showing platform reviewers a compliant page and users a policy-breaking one), which is explicitly bannable on TikTok and every major platform. Never let your routing layer serve different content by detecting reviewers/bots — that crosses into deception. Amazon Associates specifically forbids cloaking that hides the Amazon destination; use native shortlinks there. If you log IP/UA/geo for EU visitors, add a privacy-policy line covering redirect tracking (GDPR).

**5.3 KPI definitions for the pipeline**
- **EPC** = revenue ÷ clicks (primary cross-offer comparator)
- **CR** = sales ÷ clicks (or sales ÷ link-clicks)
- **AOV** = revenue ÷ orders
- **Revenue per video** = attributed revenue per `video_id`
- **Revenue per 1k views (RPM-equivalent)** = (attributed revenue ÷ views) × 1000 — the truest north-star for a view-driven pipeline
- **Funnel:** views → bio/link CTR → landing CTR → offer CR → refund-adjusted net

**5.4 Attribution granularity actually achievable**
Per-creative revenue attribution is fully achievable on Digistore24 (cid+sid, S2S) and ClickBank (TID + INS postback). Impact and PartnerStack support it via sub-IDs + their APIs. Amazon is the weak link — coarse tracking IDs, no real-time conversion postback, no earnings API.

### 6. Copywriting & Script Frameworks for Affiliate Conversion

**6.1 The hook carries the conversion (and the distribution)**
The first 3 seconds determine ~71% of scroll-or-stay decisions; videos holding 70–85% retention at 3 seconds get materially more distribution. But note the conversion caveat: hooks that maximize *views* (pure curiosity bait) don't always maximize *sales*. The conversion-relevant hook does two jobs: stops the scroll AND pre-qualifies for the offer.

**Hook taxonomy (turn each into a prompt template):**
- **Bold/contestable claim:** "This is why your [problem] keeps happening." (curiosity gap before the brand)
- **Direct address / call-out:** name the viewer's exact situation in line one
- **Correction / "you're doing it wrong":** pattern-interrupt + authority
- **Curiosity loop:** open a question the payoff closes ("I ruined this on purpose — here's why")
- **Transformation / proof-first:** show the after, then explain
- **Insider secret:** "what [category] won't tell you"

Curiosity-gap hooks have been reported at 65–75% view-through vs 40–50% for purely descriptive hooks. Deliver on the hook's promise by ~second 10–15 or retention craters.

**6.2 Proven script structures (Script/Copy agent templates)**

- **PAS (Problem–Agitate–Solve):** Dan Kennedy's "most reliable formula." Best for short-form: Problem (hook) → Agitate (cost of inaction) → Solve (offer). Fits a 20-second/~60-word script.
- **AIDA (Attention–Interest–Desire–Action):** classic; spend less on Attention, more on Interest/Desire bridging hook→solution.
- **Hook–Story–Offer:** native UGC structure; relatable micro-story → product as resolution → CTA.
- **Demonstration:** show the transformation/use live — strongest for visually demonstrable products on short-form.
- **The DR formula** (Hook → Problem → Solution → Value Prop → Social Proof → CTA) for a fuller 20-second arc.

Match framework to **awareness level** (Eugene Schwartz's 5 levels): unaware → AIDA/curiosity; problem-aware → PAS; solution-aware → BAB/comparison; most-aware → direct CTA.

**6.3 Bridge / pre-sell page frameworks**
A bridge (pre-sell) page sits between the video and the vendor sales page to warm cold traffic, qualify leads, capture email, and stay compliant with ad-network rules. Practitioner data suggests pre-selling can lift conversion meaningfully versus direct linking, and ClickBank reports affiliates nearly doubling EPC through better congruency. Structure: outcome-focused headline congruent with the video → short empathy/story → 3 benefit bullets → soft proof → single CTA to the offer. Add `noindex`; keep it ~300–600 words; load fast on mobile. Note the 2026 caveat: thin "pure pass-through" bridge pages are increasingly filtered by platforms and search — make the page genuinely useful (comparison, FAQ, real context), not a hollow gateway.

**6.4 Psychological triggers that survive FTC compliance**
Curiosity, specificity, social proof (real and substantiated), scarcity *only if genuine*, and authority — none of which require a prohibited claim. The compliant move is to sell the *mechanism* and *experience* ("a 30-second morning routine"), not a prohibited *outcome* ("lose 20 lbs").

**6.5 Disclosure placement & conversion**
FTC requires clear and conspicuous disclosure of the material connection; the net impression must not mislead. The honest finding: rigorous public data quantifying disclosure's effect on conversion is thin and mixed — treat disclosure as a non-negotiable fixed cost of staying in business, not a conversion lever to optimize away. Place it on-screen AND in caption per your existing plan; do not bury it.

### 7. Autonomous Operation Mechanics (minimum human interaction)

**7.1 Safe-to-automate vs human-checkpoint**

| Fully automatable | Human (or hard-gate) checkpoint |
|---|---|
| Offer scoring & ranking (the rubric in §1.4) | Final offer approval before first spend/post (your existing approval gate) |
| Per-creative attribution + KPI dashboards | HIGH-risk claim review (anything the classifier flags) |
| Offer rotation / multi-armed bandit allocation | New-account warming decisions |
| Pause rules for underperformers | Network ToS / payout disputes |
| Earnings reconciliation across networks (APIs) | Tax filing / entity decisions |
| Compliance pre-screen (claim detection) | — |

**7.2 Offer rotation: multi-armed bandit allocation**
Treat each offer (or offer×creative) as a bandit arm; allocate impression/posting budget by expected revenue-per-1k-views. **Thompson Sampling** is the pragmatic choice — it balances exploration/exploitation, needs less data than fixed-horizon A/B tests, and is simple to implement (Beta posterior on conversion, sample, allocate to the max). Caveat from the literature: bandits **deliberately starve losing arms of traffic**, so you won't get tight confidence on *how bad* a loser is — fine for allocation, not for inference. For a low-conversion-rate domain, seed each new arm with a forced exploration floor (e.g., minimum N videos or N clicks) before letting the bandit down-weight it, or you'll kill arms on noise.

**7.3 Automated pause / kill rules**
- Pause an offer arm if refund-adjusted revenue-per-1k-views < threshold after a minimum sample (see §8).
- Hard-kill if refund_rate breaches 15% or the network flags the offer.
- Auto-pause any creative whose claim-classifier score crosses HIGH post-hoc (defense in depth).

**7.4 Programmatic compliance checking**
A pre-post gate: every script + caption runs through the §2.3 tiered classifier (lexicon + LLM). HIGH → block; MEDIUM → rewrite/soften + force disclosure; LOW → pass with standard disclosure. Log every decision for an audit trail (the FTC and platforms both reward demonstrable good-faith monitoring).

**7.5 Earnings reconciliation — which networks have usable affiliate APIs**

| Network | Affiliate earnings API? | Auth | Key endpoint | Limitation |
|---|---|---|---|---|
| **ClickBank** | ✅ Yes | Developer Key + **Clerk Key** (colon-separated; DEV key now optional via a public "captain" key) | `/1.3/analytics/affiliate/...`, `/1.3/quickstats/list` | Subscription `/subscription/details` & `/status` return **empty** for affiliate role (vendor-only since Dec 2022); rebill earnings via Analytics rebill events. No published numeric rate limit; 100 rows/call, 206-paginated |
| **Digistore24** | ✅ Yes | API key (`readonly`/`writable`/`developer`) | `listTransactions` (+ stats functions) | Docs are vendor-framed; scope set by key permission; `listTransactions` is the operative earnings endpoint |
| **Impact** | ✅ Yes (strongest partner API) | **Account SID + Auth Token**, HTTP Basic Auth | `/Mediapartners/{SID}/Actions`, `/ActionUpdates`, `/ReportExport/{id}` (Action Listing w/ Action Earnings) | 45-day range cap on Actions/ActionUpdates; some reports `ApiAccessible:false`; "Run report" deprecating |
| **PartnerStack** | ✅ Yes (separate Partner API) | **Bearer** `api_key` (Vendor API uses Basic Auth — don't confuse) | `GET /api/v2/rewards` (commissions), `/transactions`, `/payouts` | Rate limits undocumented; partner-team members must use owner's key; epoch-ms timestamps |
| **Amazon Associates** | ❌ **No earnings API** | (PA-API: AWS-signed keys) | None — earnings only via Associates Central report downloads | PA-API returns product data only; **deprecated in 2026** (pages conflict between Apr 30 and May 15, 2026), no new signups, 30-day-sales access requirement |

This means your reconciliation agent can hit ClickBank, Digistore24, Impact, and PartnerStack on a schedule and write to Supabase; Amazon must be handled via scheduled report-file ingestion (or skipped, consistent with its fallback role in your plan).

**7.6 Tax & entity considerations (US solo operator)**
- Affiliate income is **self-employment income** → Schedule C; **self-employment tax 15.3%** on net earnings; filing required above $400 net; **quarterly estimated payments** if you'll owe ≥$1,000.
- Networks issue a **1099-NEC** at ≥$600/year per network; you must report **all** income even without a 1099 (sum across ClickBank, Digistore24, Impact, PartnerStack, etc.).
- **Foreign networks** (Digistore24 is EU-based) may not issue a US 1099 and may ask you to certify status; you still owe US tax on the income. Digistore24 handles EU VAT on the underlying sale, so as the affiliate the "sale" is already taxed at the buyer level — your concern is income tax on commissions, not VAT collection.
- **Entity:** start as sole proprietor (simplest); consider an **LLC** for liability separation and, as income scales, an **S-corp election** to optimize SE tax. Get a CPA once revenue is real. (Not legal/tax advice.)
- Deductible: VPS/hosting, API/software subscriptions, AI-generation costs, domain, home-office portion.

### 8. Economics & Benchmarks (the honest base rates)

**8.1 Funnel benchmarks (treat as directional; sources vary in rigor)**
- **TikTok 3-second hold:** ~71% of stay/scroll decided in first 3s; 70–85% 3-s retention = strong distribution band.
- **Video→link CTR:** widely cited target 2–5% (vendor-blog figures, not peer-reviewed); TikTok small-creator affiliate "link engagement" is reported far higher than Instagram, but "engagement" ≠ purchase.
- **Click→purchase CR:** SaaS referral-to-sale **~0.8%** (Rewardful benchmark, well-sourced); Digistore24 cold-traffic norm **1–3%**; physical/Amazon-type **3–8%**; TikTok-Shop native shopping lifts CR materially vs external links. Treat any single CR figure as offer-and-traffic-specific.
- **TikTok ads "bad" CR:** below 0.5% is the cited failure line (ad context).
- **Revenue per 1k views:** highly skewed — a small number of viral videos drive 50–80% of monthly affiliate revenue; most videos earn $10–200, viral outliers far more. Plan for a power-law, not an average.

**8.2 How much data before a kill/scale decision is valid**
This is where your trading background pays off. At a true conversion rate around 1%, the variance is brutal: to distinguish, say, a 1.0% offer from a 1.5% offer with reasonable confidence (~80% power, 5% significance) you need on the order of **a few thousand clicks per arm** — i.e., **tens of thousands of views per offer** at a 2–5% link CTR. For a simpler "is this offer above my breakeven RPM" test, you still want a minimum of **~30–50 conversions** before trusting the estimate; below ~10 conversions the confidence interval on EPC is too wide to act on.

Practical rule for the pipeline:
- **Exploration floor before any kill:** ≥1,000 clicks OR ≥30 conversions per arm (whichever first), to avoid killing winners on early noise.
- **Bandit allocation** can start shifting budget earlier than a fixed A/B test would, but enforce the floor so low-traffic arms aren't starved before they've spoken.
- **Refund lag:** because refunds/cancellations arrive 15–60 days later, never finalize a "scale" decision on gross revenue — wait for the refund window or discount expected revenue by the category refund rate.

---

## Recommendations

**Stage 0 — Build the survival layer first (week 1–2).** Before any offer goes live, ship the **claim-detection compliance gate** (§2.3) and the **AI-disclosure auto-labeler** (§4.4). Account death is the dominant risk for an AI-generated autonomous op; these two are non-negotiable hard gates. Benchmark to change course: if >20% of generated scripts trip the HIGH-risk classifier, your offer pool is too claim-heavy — shift toward SaaS/low-risk physical.

**Stage 1 — Stand up attribution before scaling content (week 2–4).** Build the Vercel redirect → Supabase click-log → S2S-postback loop (§5.2) for Digistore24 and ClickBank first (best per-creative granularity). You cannot make valid kill/scale decisions without per-video revenue attribution. Benchmark: you should be able to trace ≥90% of conversions to a specific `video_id` before scaling volume.

**Stage 2 — Launch a barbell offer portfolio (month 1–2).**
- **Cash/signal arm:** 3–5 high-AOV, low-refund (<10%) Digistore24/ClickBank digital offers that are visually demonstrable and pass the rubric (§1.4). These generate fast test signal and front-end cash.
- **Compounding arm:** 3–5 recurring SaaS programs (PartnerStack/Impact/Rewardful, 20–40% recurring, low-follower-friendly) for MRR that compounds over 6–9 months.
- **Defer TikTok Shop** until you've cleared 1,000 followers and the 30-day pilot; treat it as a third arm, not the foundation, given its thin per-unit economics and gating.

**Stage 3 — Automate allocation with a seeded bandit (month 2+).** Implement Thompson Sampling over offer×creative arms keyed on refund-adjusted revenue-per-1k-views, with a forced exploration floor (§8.2). Auto-pause on the kill rules; require human sign-off only on new offers and HIGH-risk flags.

**Stage 4 — Close the books automatically (ongoing).** Build the earnings-reconciliation agent against ClickBank, Digistore24, Impact, and PartnerStack APIs (§7.5) writing to Supabase; ingest Amazon via scheduled report files. Reconcile attributed revenue (your redirect logs) against network-reported earnings weekly — divergence flags tracking leakage.

**Thresholds that change the strategy:**
- If recurring-SaaS cohort MRR isn't compounding after **6 months** of converting traffic, the problem is traffic→trial conversion, not the offers — fix the bridge-page congruency before adding offers.
- If any single offer's refund rate creeps above **15%**, hard-kill regardless of gross EPC.
- If TikTok account health (CHR/violation points) trends down, **stop posting AI media that could be auto-flagged** and audit disclosure compliance before it becomes a ban.
- When net affiliate income crosses **~$40–50k/year**, get a CPA and evaluate the LLC→S-corp election.

---

## Caveats

- **Source-quality disclosure:** Network economics (gravity mechanics, EPC/refund definitions, API capabilities, cookie windows, TikTok Shop rules, FTC standards/enforcement) are well-sourced from primary docs (ClickBank, Digistore24, TikTok Seller University/Newsroom, FTC, Impact, PartnerStack, Rewardful's report). **Conversion-rate and revenue-per-view benchmarks are weakly sourced** — they come largely from vendor blogs and creator-marketing sites, not peer-reviewed or audited data, and they vary widely. The notable exception is the SaaS referral-to-sale figures, which come from Rewardful's analysis of $68.4M in affiliate revenue. Treat all other CR/RPM figures as directional and replace them with your own measured numbers as fast as your attribution layer allows.
- **The "winning offer for short-form video" literature is largely practitioner anecdote,** not controlled study. The structural claims (hook quality, congruency, demonstrability) are widely corroborated but not experimentally proven; validate on your own data.
- **TikTok Shop rules are changing fast** (insurance mandate rolling out in early 2026, SFRR thresholds added Sept 2025, identity-verification tightening). Re-verify eligibility and AI-content rules at launch; this report reflects the 2025–2026 state.
- **Disclosure-vs-conversion data is genuinely thin.** Don't optimize disclosure away to chase conversion — the regulatory expected-value math (FTC + platform ban risk) dominates any small conversion gain.
- **Amazon PA-API deprecation date is internally inconsistent** across Amazon's own pages (April 30 vs May 15, 2026); since Amazon has no earnings API regardless and is your fallback network, this is low-impact, but confirm before building anything against it.
- **None of this is legal or tax advice.** The FTC liability and entity/tax sections are general; given the elevated claim-risk of AI-generated promotional content (the Traffic and Funnels judgment exceeded $16M; the 2023 notice exposed 670 firms to up to $50,120 per violation), a one-time consult with an advertising-law attorney and a CPA is cheap insurance before scaling.
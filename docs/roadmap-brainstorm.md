# الصَّيَّاد — Wide-Scale Brainstorm & Roadmap

> A deliberately broad "what could this store become?" sweep, generated as a
> planning aid (the *sleepy-brain-storm* branch). Nothing here is a commitment —
> it's a menu. Companion docs: [architecture.md](architecture.md) ·
> [database-schema.md](database-schema.md) · [development-log.md](development-log.md).
>
> Grounded in the code as of M29 (`db8a178`). Written for the Syrian market:
> first-time online shoppers, COD-dominant, WhatsApp everywhere, ShamCash
> arriving, delivery priced per governorate, intermittent connectivity, and
> some hosts that block Syrian IPs.

---

## How to read this

Every idea carries three tags so it can be triaged fast:

- **Impact** for a Syrian COD marketplace: 🔥 high · ➖ medium · 💤 nice-to-have
- **Effort**: S (a day or two) · M (a module) · L (multi-module / infra)
- **Where** it touches in the current code, so a "yes" turns into action quickly.

The philosophy that got us here still holds: **one job per screen, works
without JS, snapshots over references, activate-don't-delete, Arabic-first.**
Everything below should respect those or it doesn't belong.

---

## Where we are today (honest snapshot)

**Solid and shipped:** catalog with a category tree, Arabic-normalized search
with live suggestions, session cart, atomic COD checkout with stock locking,
delivery zones, coupons, verified-buyer reviews, order tracking, accounts
(customer/merchant/staff), a themed admin, a sales dashboard, an installable
PWA, rotating backups, i18n (ar/en), 167 green tests. Clean ~5k-line codebase,
zero external CDNs.

**The shape of what's missing** (the whole point of this doc):

1. **Payment is a single field, not a system.** `Order.payment_method` +
   a commented-out `ShamCashGateway` in `apps/orders/payments.py`. There is no
   payment-transaction record, no webhook endpoint, no idempotency, no
   retry/refund state. The thing we're literally asking ShamCash for has no
   home yet in the data model.
2. **The customer is told nothing automatically.** The owner gets an email; the
   customer gets a manual "راسِل الزبون" WhatsApp button in admin. No automated
   "order confirmed / shipped / delivered" message — the #1 trust signal for a
   first-time online buyer.
3. **Cart dies with the session.** Even a logged-in user's cart lives only in
   `django_session`. Switch device or clear cookies → cart gone. No persistence,
   no abandoned-cart capture.
4. **No product variants.** `specs` is free JSON, so "أحمر / مقاس L" can't carry
   its own stock or price. Fine for simple goods, a wall for clothing/shoes.
5. **One address, retyped every time.** No address book; guests and members
   both re-enter the whole address on each order.
6. **Search is match, not ranking.** Normalized `__icontains` over
   `search_text`. No relevance ranking, typo tolerance beyond letter-folding,
   or zero-result analytics.
7. **Merchants have no window of their own.** They use a scoped Django admin;
   there's no merchant-facing "my sales / my payouts" surface, and no
   commission/settlement model.
8. **Ops blind spots:** no CI, no error monitoring (Sentry), no shared cache
   (rate-limit counters drift across Gunicorn workers — already flagged), no
   product JSON-LD for SEO, `STORE_PHONE/EMAIL` default to a personal number in
   code.

None of these are criticisms of what exists — they're the natural next rings.

---

## The top 10 highest-leverage moves (if I had to rank)

Ordered by (impact for this market ÷ effort), most worth-it first:

| # | Move | Why it's leverage | Effort |
|---|------|-------------------|--------|
| 1 | **PaymentTransaction model + ShamCash gateway + webhook** | It's the active ask; do the data model *right* before the API lands (idempotency, status, retries, refunds). | M |
| 2 | **Automated order status → WhatsApp/SMS to the customer** | Biggest trust lever for first-time buyers; slashes "وين طلبي؟" load. | M |
| 3 | **Persistent cart + abandoned-cart recovery** | Recovers real revenue; cart-in-DB also unlocks cross-device and analytics. | M |
| 4 | **Product variants (size/color with own stock & price)** | Opens clothing/shoes/cosmetics — the categories that actually move online. | L |
| 5 | **Address book + one-tap reorder** | Removes the highest-friction step in checkout; repeat purchase becomes trivial. | S–M |
| 6 | **"نبّهني لمّا يتوفّر" back-in-stock + low-stock urgency** | Captures demand you're currently dropping on out-of-stock; cheap to build. | S |
| 7 | **Wishlist / favorites** | Retention + a marketing surface (price-drop pings); requested in backlog. | S |
| 8 | **Merchant dashboard (their sales, orders, payouts)** | Makes the marketplace real for sellers; precondition for scaling supply. | M |
| 9 | **Product JSON-LD + richer SEO + WhatsApp share polish** | Free acquisition; structured data + hreflang(ar/en) we already half-have. | S |
| 10 | **CI (GitHub Actions) + Sentry + shared Redis cache** | Protects the 167 tests, catches prod errors, fixes rate-limit drift. | S–M |

Everything below expands the menu by theme.

---

## 1) Payments & checkout 🔥

The store's next chapter. Treat payment as its own subsystem, not a field.

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **`PaymentTransaction` model** (order FK, method, provider ref, amount, status `initiated/pending/paid/failed/refunded`, raw payload JSON, idempotency key, timestamps) | 🔥 | M | new in `apps/orders`; the missing spine for ShamCash. See appendix. |
| **ShamCash gateway impl** (`start_payment`, `verify_payment`) behind the existing `payments.py` seam | 🔥 | M | uncomment/flesh the stub; keep COD as fallback always. |
| **Webhook/callback endpoint** with signature verification + idempotency | 🔥 | M | new URL in `orders`; must be replay-safe and CSRF-exempt with its own auth. |
| **Pay-on-confirmation vs pay-now flows** (some buyers pay after a human confirms availability) | ➖ | S | a status branch, not new tech. |
| **Retry a failed payment** from the order page | ➖ | S | reuses gateway; needs the transaction model. |
| **Refunds / partial refunds** state + admin action | ➖ | M | ties to returns (§9). |
| **Store credit / wallet** (refunds as credit, faster than cash back in SY) | ➖ | L | new model; strong retention tool locally. |
| **COD cash reconciliation** (mark cash collected, per-courier settlement) | 🔥 | M | COD is still the majority — closing the money loop matters as much as ShamCash. |
| **Split "amount due now" vs "on delivery"** (deposit online, rest COD) — hedges trust both ways | ➖ | M | powerful for higher-ticket items. |
| Other Syrian rails later (Bitaqti/Fatora/bank transfer receipt upload) | 💤 | M | same gateway abstraction pays off. |

## 2) Accounts, retention & re-engagement 🔥

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Address book** (multiple saved addresses, default) | 🔥 | S–M | new `Address` model; checkout picks instead of retyping. |
| **One-tap reorder** from order history | 🔥 | S | rebuild a cart from an `Order`'s items. |
| **Wishlist / favorites** (+ price-drop & back-in-stock pings) | 🔥 | S | backlog item; join table user↔product. |
| **OTP phone verification** (WhatsApp/SMS code) at signup & checkout | 🔥 | M | phone *is* the identity — verifying it kills fake orders. |
| **Persistent cart for members** (merge session→DB on login) | 🔥 | M | cross-device; foundation for abandoned-cart. |
| **Guest → account nudge** post-order ("احفظ طلبك، تتبّعه بضغطة") | ➖ | S | order already has phone; offer to claim it. |
| **Loyalty points / نقاط** (earn on delivered orders, redeem as discount) | ➖ | L | strong repeat-purchase driver; needs wallet-ish ledger. |
| **Referral program** (invite code → both get a coupon) | ➖ | M | reuses coupon engine + a referral table. |
| **In-app notification center** (order updates, price drops) | 💤 | M | pairs with PWA web-push. |

## 3) Catalog, variants & merchandising 🔥

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Product variants** (option types + variant rows w/ own SKU/stock/price/image) | 🔥 | L | the big catalog upgrade; migrate `specs` semantics carefully. |
| **Brands** as a first-class model (filter, brand pages, SEO) | ➖ | S–M | new `Brand` FK on Product. |
| **Faceted filters** (price range, brand, rating, in-stock, attributes) | 🔥 | M | leans on variants/brand/attributes; huge for discovery. |
| **Back-in-stock "نبّهني"** subscription | 🔥 | S | capture email/phone against an out-of-stock product. |
| **Cross-sell / upsell** ("يُشترى عادةً مع", "منتجات مشابهة" already exists) | ➖ | M | co-purchase from OrderItems. |
| **Recently viewed** (session/localStorage) | ➖ | S | pure front-end + a small endpoint. |
| **Bundles / عروض الطقم** (buy X+Y for Z) | ➖ | M | pricing rule + display. |
| **Pre-orders / حجز مسبق** for out-of-stock hot items | 💤 | M | order without stock deduction, flagged. |
| **Product Q&A** ("اسأل عن المنتج", answered by seller/staff) | ➖ | M | complements reviews; great for hesitant first-timers. |
| **Bulk product import (CSV/Excel)** for staff & merchants | 🔥 | M | onboarding supply at scale; validation is the hard part. |
| **Size guides / جداول المقاسات** per category | 💤 | S | static content slot on product page. |

## 4) Search & discovery ➖🔥

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Postgres full-text + `pg_trgm` typo tolerance** | 🔥 | M | already the planned prod DB; GIN index over `search_text`, no UI change. |
| **Search analytics** (log queries, surface zero-result & top terms) | 🔥 | S | tells you exactly what stock/aliases to add. |
| **Relevance ranking** (name > description, in-stock boost, popularity) | ➖ | M | replaces flat `icontains`. |
| **Synonyms / aliases dictionary** (جوال=موبايل=تلفون) | ➖ | S | extends the normalize() idea to word-level. |
| **"Did you mean…" & related searches** | 💤 | M | on top of trgm similarity. |
| **Sort by rating / best-selling** (have newest & price) | ➖ | S | add options to existing sort. |

## 5) Trust, reviews & social proof ➖

First-time buyers convert on *trust*. Cheap wins live here.

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Review photos** ("شارك صورة للمنتج اللي وصلك") | 🔥 | M | UGC is the strongest proof; reuses image/thumb pipeline. |
| **Helpful votes** on reviews + sort by helpful | ➖ | S | small model + HTMX. |
| **Seller/merchant rating & storefront page** | ➖ | M | aggregate per merchant; a public seller page. |
| **Merchant reply to reviews** | ➖ | S | one field + permission. |
| **Trust badges** (verified seller, "١٢٠ زبون اشترى هالمنتج") | ➖ | S | counts from OrderItems. |
| **Urgency/scarcity** ("آخر ٣ قطع", "١٥ شخص عم يتفرّجوا") — honestly | ➖ | S | from real stock; never fake it (matches the fake-sale guard ethos). |
| **Delivery-proof & ratings for the delivery experience** | 💤 | M | rate the courier, not just the product. |

## 6) Marketing, growth & CMS ➖🔥

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Abandoned-cart recovery** (WhatsApp/SMS "نسيت شي بالسلة؟" + optional coupon) | 🔥 | M | needs persistent cart (§2); high ROI. |
| **Homepage merchandising slots** managed from admin (banners, featured rows, deals of the week) | 🔥 | M | today the homepage is code-driven; make it a CMS surface. |
| **Flash sales / تخفيضات مؤقتة** with a countdown | ➖ | M | time-boxed price + urgency UI. |
| **Coupon expansion**: first-order code, auto-apply, free-shipping threshold, category/merchant-scoped | ➖ | S–M | engine exists; add targeting fields. |
| **Product JSON-LD + Open Graph polish + hreflang(ar/en)** | 🔥 | S | free SEO; we already have sitemaps/OG partially. |
| **Blog / أدلة شراء** (buying guides, "أفضل ٥…") for organic traffic | ➖ | M | new lightweight content app; big long-tail SEO. |
| **WhatsApp catalog / click-to-order** deep links | ➖ | S | WhatsApp is the channel here; make every product 1-tap shareable to a chat. |
| **Newsletter / broadcast list** (opt-in, price drops, new arrivals) | 💤 | M | email or WhatsApp broadcast. |
| **Referral & influencer codes** (trackable coupons) | ➖ | M | coupon + attribution. |

## 7) Logistics & delivery 🔥

The part that makes or breaks a Syrian store.

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Automated status → customer** (confirmed/shipped/out-for-delivery/delivered via WhatsApp/SMS) | 🔥 | M | see §7-adjacent notifications; the single biggest UX gap. |
| **Sub-areas / neighborhoods under a governorate** with their own fee | ➖ | M | extend `DeliveryZone` to a 2-level tree. |
| **Delivery time estimates** ("يوصلك خلال ٢-٤ أيام") per zone | ➖ | S | field on zone; shown at checkout. |
| **Scheduled delivery windows** (choose day/slot) | 💤 | M | for big cities. |
| **Courier assignment + a courier status view** (mobile-friendly page) | ➖ | L | mini role; updates status + collects COD cash. |
| **Pickup points / استلام من نقطة** as a zero-fee option | 💤 | M | cheaper than home delivery, builds trust. |
| **Packing slip / invoice PDF** print from admin | 🔥 | S | fulfillment basics; reuse the docx/pdf tooling. |

## 8) Merchant / marketplace 🔥

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Merchant-facing dashboard** (their orders, sales, low stock, payouts) — not raw admin | 🔥 | M | mirrors the owner dashboard, scoped to `merchant`. |
| **Commission & settlement model** (take-rate per sale, payout ledger) | 🔥 | L | precondition to actually running a marketplace. |
| **Merchant onboarding wizard** (docs, store profile, first product) | ➖ | M | improves the apply→approve funnel. |
| **Merchant order fulfillment** (mark shipped, print slip) within their scope | ➖ | M | ties to §7. |
| **Merchant analytics** (top products, conversion, returns) | 💤 | M | retention for sellers. |
| **Payout requests / تسوية** + history | ➖ | M | with the commission ledger. |

## 9) Admin, operations & fulfillment ➖🔥

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Order fulfillment workflow** (bulk status change, filters by zone/date, print run) | 🔥 | M | scale past hand-editing each order. |
| **Returns / RMA / إرجاع** flow (request → approve → refund/credit) | ➖ | M | pairs with refunds (§1). |
| **Inventory management** (restock, low-stock alerts to WhatsApp/email, stock history) | 🔥 | M | today low-stock is only a dashboard color. |
| **CSV export** everywhere (orders, products, customers) | ➖ | S | backlog item; ops love it. |
| **Audit log** (who changed price/stock/status, when) | ➖ | M | trust & debugging as staff grows. |
| **Purchase orders / توريد** to suppliers | 💤 | L | when inventory gets serious. |
| **Saved admin views & saved filters** | 💤 | S | quality-of-life. |

## 10) Analytics & business intelligence ➖

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Self-hosted, privacy-friendly analytics** (Matomo/Plausible, no external CDN — fits the no-CDN rule) | 🔥 | S–M | know traffic without shipping data abroad. |
| **Conversion funnel** (view→cart→checkout→paid) + cart-abandon rate | 🔥 | M | quantifies every idea above. |
| **Search & zero-result dashboard** | ➖ | S | see §4. |
| **Cohort / repeat-purchase retention** | ➖ | M | is loyalty working? |
| **Revenue & tax/settlement reports** (export) | ➖ | S | extends the sales dashboard. |
| **Product performance** (view→buy rate, return rate) | ➖ | M | merchandising decisions. |

## 11) Performance & scale ➖

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Redis (or DB) shared cache** | 🔥 | S | fixes rate-limit drift across workers (already flagged) + page fragment caching. |
| **Responsive images** (`srcset`, WebP/AVIF, lazy-load) | 🔥 | S–M | thumb pipeline exists; add sizes. Bandwidth matters in SY. |
| **Query audit** (`select_related`/`prefetch_related`, N+1 hunt on category & search) | ➖ | S | cheap latency wins. |
| **HTTP caching headers** for catalog pages + long-cache hashed static | ➖ | S | fewer round-trips on flaky connections. |
| **Fragment caching** of category grids & homepage | ➖ | M | with the shared cache. |
| **DB index review** as data grows | 💤 | S | revisit with real query logs. |

## 12) Reliability & DevOps 🔥

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **CI (GitHub Actions): tests + lint on every push/PR** | 🔥 | S | protects the 167-test invariant automatically. |
| **Sentry / error monitoring** | 🔥 | S | see real prod errors instead of guessing. |
| **Staging environment** mirroring prod | ➖ | M | test ShamCash/webhooks safely. |
| **Health-check endpoint + uptime monitor** | ➖ | S | `/healthz` + a pinger. |
| **Scheduled + offsite backups** (backup command exists; automate & ship off-box) | 🔥 | S | cron/Task Scheduler → remote copy. |
| **Automated deploy** (script or Actions) | ➖ | M | reduce human error on a solo project. |
| **Dependency scanning** (Dependabot/pip-audit) | ➖ | S | supply-chain hygiene. |
| **Log aggregation** | 💤 | M | when traffic justifies it. |

## 13) Security & compliance ➖🔥

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **2FA for admin/staff** | 🔥 | S–M | admin is the crown jewels. |
| **Security-header audit** (CSP, HSTS, Referrer-Policy, `SECURE_*` in prod) | 🔥 | S | verify `prod.py` sets the full set. |
| **Webhook signature verification & idempotency** (ShamCash) | 🔥 | M | part of §1; money endpoints must be replay-proof. |
| **Form honeypots / basic bot defense** on signup/checkout/reviews | ➖ | S | complements rate-limiting. |
| **PII data export/delete** ("نزّل بياناتي / احذف حسابي") | ➖ | M | good practice; user-initiated. |
| **Admin IP allowlist / geo rules** | 💤 | S | if the ops team is fixed-location. |
| **Move `STORE_PHONE/EMAIL/WHATSAPP` to env-only** (no personal defaults in code) | ➖ | S | small but real; they're baked into `base.py` now. |
| **Secret rotation & `.env` hygiene checklist** | 💤 | S | document it. |

## 14) Accessibility & UX polish ➖

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **One-page / fewer-step checkout** with address-book + saved phone | 🔥 | M | shortest path to "اطلب". |
| **WCAG pass** (contrast, focus order, Arabic screen-reader labels, form errors) | ➖ | M | M29 added focus rings; go the rest of the way. |
| **Skeleton loaders & better empty states** (empty cart, no results, no orders) | ➖ | S | perceived speed on slow links. |
| **Quantity steppers, inline validation, sticky add-to-cart on mobile** | ➖ | S | conversion micro-wins. |
| **Dark mode** (tokens make it feasible) | 💤 | M | tokens.css already centralizes color. |
| **Image gallery / zoom** on product page (placeholder exists) | ➖ | S | product_detail already has a gallery slot. |

## 15) Notifications & messaging 🔥

The connective tissue for §1, §2, §6, §7 — worth its own module.

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Notification service** (one place: email + WhatsApp + SMS + web-push, templated, logged) | 🔥 | M | generalizes today's owner-email + manual WhatsApp button. |
| **Transactional WhatsApp** (order confirmed/shipped/delivered) | 🔥 | M | WhatsApp Business API / provider; the market's default channel. |
| **Syrian SMS gateway** fallback | ➖ | M | for non-WhatsApp users / OTP. |
| **PWA web-push** (price drops, back-in-stock, order updates) | ➖ | M | SW already registered; add push. |
| **Branded HTML email templates** | 💤 | S | today notifications are plain. |
| **Delivery message log** (what was sent, when, to whom) | ➖ | S | audit + dedupe. |

## 16) Mobile ➖

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Deepen the PWA** (install prompt UX, offline cart, push, app-shell caching *without* caching store data — respect the current SW rule) | 🔥 | M | cheapest path to "an app" in SY. |
| **TWA wrapper → Google Play listing** | ➖ | M | a Play Store presence with the existing PWA. |
| **Native app** | 💤 | L | only if PWA proves demand; the service layer is already API-ready. |

## 17) Internationalization & localization ➖

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **Translatable product fields** (name/description per language) | ➖ | M | backlog item; en storefront currently shows Arabic product data. |
| **Kurdish (Kurmanji) UI** as a third language | 💤 | M | LANGUAGES is already a list; infra exists. |
| **Locale-correct number/price/date formatting** everywhere | ➖ | S | we already dodge the ٤٫٠ float trap; audit the rest. |
| **Currency display config** (if multi-currency ever matters) | 💤 | M | unlikely near-term; note only. |

## 18) AI & automation (bridges to your TrustAngle work) 💤➖

Reuses skills from the AI-content platform; several are genuinely high-ROI here.

| Idea | Impact | Effort | Where / notes |
|------|--------|--------|---------------|
| **AI Arabic product-description generator** in admin ("اكتب وصف") | 🔥 | M | merchants hate writing copy; huge onboarding accelerant. |
| **Auto alt-text & image tagging** for uploaded product photos | ➖ | M | fills `alt_text` (a11y + SEO) automatically. |
| **Auto-categorization suggestion** on new products | ➖ | M | speeds catalog entry. |
| **Review summarization** ("الزبائن بيمدحوا…") + sentiment moderation | ➖ | M | digestible social proof. |
| **Support chatbot** (order status, returns, FAQ) in Arabic | 💤 | L | deflects support load. |
| **Recommendations engine** ("لأنك اشتريت…") | 💤 | L | co-purchase data first, model later. |
| **Order-fraud scoring** (odd phone/address/velocity patterns) | 💤 | M | protects COD from prank orders. |

---

## Cross-cutting: data-model additions this roadmap implies

If we pursue the top themes, these new models/fields recur — worth designing
coherently rather than one-off:

- **`PaymentTransaction`** (§1) — the spine for ShamCash & any future rail.
- **`Address`** (§2) — user↔address, default flag; checkout reads it.
- **`Wishlist` / `Favorite`** join (§2/§3).
- **`BackInStockSubscription`** (§3) — product↔contact.
- **Variant models**: `OptionType`, `OptionValue`, `ProductVariant` (§3) — the
  biggest schema change; `specs` JSON stays for non-purchasable attributes.
- **`Brand`** (§3).
- **`Notification` / message log** (§15) — every channel, deduped, audited.
- **`MerchantPayout` / commission ledger** (§8).
- **`Return` / RMA** (§9).
- **`SearchQuery` log** (§4/§10).
- **Cart → DB** for members (§2) — enables abandoned-cart & analytics.

Design note: keep the **snapshot discipline** everywhere money is involved
(payments copy amounts; payouts copy commission rate at time of sale), exactly
like `OrderItem` and the coupon/fee snapshots do today.

---

## Appendix A — ShamCash payment architecture (deep dive)

Because it's the active ask and I just wrote the proposal, here's a concrete
shape so the integration is a *fill-in*, not a redesign, when the API lands.

**New model — `apps/orders/payments_models.py` (or fold into `models.py`):**

```
PaymentTransaction
  order            FK → Order (related_name="payments")
  method           "shamcash" | "cod" | …
  provider_ref     provider's transaction id (unique, nullable until issued)
  idempotency_key  our uuid per attempt (unique) — replay-safe
  amount           Decimal(12,0)  — snapshot, never recomputed
  status           initiated → pending → paid | failed | refunded | cancelled
  raw_request      JSON (what we sent)
  raw_response     JSON (what they returned / webhook body)
  created_at / updated_at
```

**Flow:**

1. Checkout with `method=shamcash` → `create_order_from_cart` runs as today
   (stock locked, order created `status=pending`), then
   `ShamCashGateway.start_payment(order)` creates a `PaymentTransaction`
   (`initiated`) and returns a pay URL/token → redirect the customer.
2. Customer pays in ShamCash → ShamCash calls our **webhook**
   (`/orders/pay/shamcash/callback/`, CSRF-exempt, **signature-verified**).
3. Webhook is **idempotent**: look up by `provider_ref`; if already `paid`,
   ack and no-op. Else verify amount == snapshot, mark transaction `paid`,
   move `Order.status` pending→confirmed, fire the customer notification
   (§15) via `transaction.on_commit` — same pattern as `notify_new_order`.
4. Failure/timeout → transaction `failed`; order stays `pending`; offer
   **retry** (new attempt = new idempotency key) or **switch to COD**.
5. Refund → gateway refund call + transaction `refunded` (+ store-credit
   option, §1).

**Guardrails:** never trust the client for success — only the verified webhook
flips money state; amount is compared to the snapshot; every provider call and
callback is logged in `raw_*`; the endpoint auth is separate from user sessions.
This keeps the atomic-service + snapshot philosophy intact and slots cleanly
into the existing `payments.py` seam.

---

## Appendix B — Quick wins worth doing regardless (a "this week" list)

Small, high-signal, low-risk — good warm-ups that don't depend on big decisions:

1. **Product JSON-LD + OG/hreflang** — free SEO (§6). S.
2. **CI GitHub Action** running `manage.py test apps` — protects everything. S.
3. **Sentry** in `prod.py` — stop flying blind. S.
4. **Move `STORE_*` to env-only** — no personal number hard-coded in `base.py`. S.
5. **Back-in-stock "نبّهني"** on out-of-stock products — capture lost demand. S.
6. **Wishlist** — small model, real retention, already in backlog. S.
7. **Packing-slip/invoice PDF** from admin — fulfillment basics. S.
8. **Responsive `srcset` on product images** — bandwidth win in SY. S.
9. **Reorder button** on past orders — trivial with existing OrderItems. S.
10. **Search-query logging** — one model + a save; tells you what to stock next. S.

---

## Decisions that are Omar's, not mine

These change *what* to build, so I left them open rather than guessing:

- **Marketplace depth**: is Al-Sayyad a curated store that also hosts a few
  merchants, or a true open marketplace? This decides whether §8 (commission,
  payouts, merchant dashboards) is core or optional.
- **Commission model**: flat take-rate, per-category, or subscription for
  sellers? Shapes the payout ledger.
- **WhatsApp strategy**: official WhatsApp Business API (paid, templated) vs a
  lighter click-to-chat approach — decides §15's cost and capability.
- **Variants now or later**: they're an L and touch the catalog deeply; worth it
  only if clothing/shoes/cosmetics are on the near-term roadmap.
- **Analytics stance**: self-hosted Matomo (fits the no-CDN, data-stays-home
  ethos) vs nothing vs a third party.
- **Loyalty vs referral vs coupons**: which growth lever first — they overlap.

---

*Generated on the `sleepy-brain-storm` branch as a planning menu. Pick, cut,
and promote items into real M30+ modules; ignore the rest guilt-free.*

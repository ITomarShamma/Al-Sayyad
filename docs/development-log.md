# Al-Sayyad — Development Log (الصَّيَّاد)

> A record of the full build conversation between Omar (owner/sole developer)
> and Claude (AI pair). June–July 2026. Companion docs:
> [architecture.md](architecture.md) · [database-schema.md](database-schema.md).

## The project in one paragraph

**الصَّيَّاد (Al-Sayyad, "The Hunter")** — an Arabic-first e-commerce
marketplace for the Syrian market. Amazon-style variety, Syria-only delivery,
Cash-on-Delivery now with ShamCash planned. Built with **Django 5.2 + HTMX**,
plain CSS with design tokens, everything self-hosted (no external CDNs).
Designed for first-time online shoppers: one job per screen, big tap targets,
no icon without a word, direction-agnostic CSS, always show trust and state.
Brand identity extracted from Omar's strategy PDF (logo still pending from
Figma — a swappable placeholder is used).

## Working rhythm

Every module followed the same loop: **build → test → verify live → teach
(ELI5) → commit → push**. From M8 onward, work happened on the
`night-features` branch and was merged into `main` only after its tests were
green — so `main` never held broken code. Chat in English, product in Arabic
(with full English via i18n since M20).

## Module timeline

| # | Module | Commit | What landed |
|---|---|---|---|
| M0 | Scaffold | `c584413` | Django project, split settings (base/dev/prod), 5 domain apps, .env, first push |
| M1 | Design system | `4725914` | tokens.css (17 brand colors, type scale), self-hosted IBM Plex Sans Arabic, RTL shell, i18n-ready |
| M1x | Responsive fix | `88a738f` | Omar's fix: 480px "app shell" → fluid 1200px multiplatform layout |
| M2 | Components | `94f4e93`, `a01a9c6` | Button/Badge/Field/Card/ProductCard partials + /styleguide (largely built by Omar); LANGUAGES=ar fix |
| M3 | Catalog + admin | `857b243` | Tree categories, products (SYP Decimal, JSON specs, Arabic slugs), Arabic admin, schema doc started |
| M4 | Storefront | `54bc1d0` | Home/category/product pages from real data, `<str:slug>` for Arabic URLs, active-only rule |
| M5 | Cart | `06f7966` | Session cart (no login), HTMX OOB header counters, progressive enhancement |
| M6 | Checkout + orders | `e3cae17` | Order/OrderItem with price snapshots, atomic stock deduction, PRG, ShamCash hook, phone normalization |
| M7 | Arabic search | `462a1e8` | normalize() (ة/ه، أ/ا…), denormalized search_text, live HTMX suggestions |
| M8 | Order tracking | `5bd8440` | «وين طلبي؟» number+phone lookup, status timeline |
| M9 | Smarter browsing | `00a8a6d` | Whole-tree category products, full breadcrumbs, sort/filter, `{% querystring %}` pagination |
| M10 | Product extras | `bc9bf3d` | Related products, WhatsApp share |
| M11 | Trust + SEO | `2b7ecf3` | About/contact, branded 404/500, sitemap/robots/OpenGraph |
| M12 | Admin QoL + toast | `112af76` | Low-stock filter + colors, order status colors, add-to-cart toast |
| M13 | Sale pricing | `1665caa` | compare_at_price, strikethrough + «خصم N٪» flag, fake-sale guard |
| M14 | Thumbnails | `041d433` | Auto 480px JPEG on save (real result: 593KB→30KB), backfill migration |
| M15 | Documentation | `8fc0bd7` | architecture.md (8 standing rules, roles), README refresh |
| M16 | Accounts | `8c560c8` | Phone-as-username auth, «حسابي» dashboard, settings pages, Order.user (guests keep working) |
| M17+18 | Merchant + staff roles | `6ba85fa` | Merchant application → one-click approval → own-products-only admin; 4 named permission groups |
| M19 | Branded admin | `5e3d8cf` | Django admin themed via its CSS variables — Deep Sea header, Tide buttons, brand font |
| M20 | English live | `941e223`, `dcab9db` | gettext via winget, 205+ strings translated, footer language switcher, .mo committed |
| M21 | Delivery zones | `d194d38` | 14 governorates seeded (fee NULL = «يُتفق هاتفياً»), zone select + live HTMX totals, fee snapshot |
| M22 | Notifications | `2a91021` | Owner email on_commit + fail_silently, «راسل الزبون» WhatsApp button in admin |
| M23 | Coupons | `1139590` | Percent/fixed codes with constraints, session apply via HTMX, row-locked usage counting |
| M24 | Reviews | `2a98869` | Verified-buyer reviews, star average, CSS-only star input, moderation |
| M25 | Login rate-limiting | `23cc63a` | Cache counters per phone + per IP, 5 fails = 15-min lock, site + admin logins |
| M26 | Sales dashboard | `14ffd8a` | /admin/dashboard/: period cards, 14-day CSS chart, top sellers, low stock; `orders.view_order` gate keeps merchants out |
| M27 | PWA | `f120d53` | Manifest + root-scoped service worker (offline page only — never caches store pages), generated placeholder icons |
| M28 | Backups | `98545d4` | `manage.py backup`: dumpdata JSON + media in one zip, `--keep` rotation, restore round-trip tested |

**Test suite: 0 → 167 tests, green at every merge.**

## Key decisions (and why)

- **Django + HTMX over React/Next**: Omar must understand every line;
  server-rendered pages + a 50KB JS library beat an SPA for that goal.
- **Session cart & guest checkout, no forced accounts**: first-time Syrian
  shoppers; any registration wall kills conversion. Guest = order with
  `user = NULL` — still true after accounts arrived.
- **Snapshots everywhere**: order lines copy product name/price; orders copy
  zone name/delivery fee and coupon code/discount. Invoices never change
  retroactively.
- **PROTECT vs CASCADE deliberately**: deactivate instead of delete for
  anything referenced by money (products in orders, categories with products,
  merchants with products); cascade only for meaningless-alone children.
- **Profile model, not custom User**: swapping AUTH_USER_MODEL mid-project is
  migration surgery; OneToOne profile is the safe standard.
- **Phone-first identity**: the mobile number is the username; Arabic-Indic
  digits normalized everywhere (٠٩ → 09).
- **Business logic in services**, one atomic function turns a cart into an
  order (stock locks, coupon lock, fee math) — reusable by any future API.
- **Fee/coupon three-state semantics**: NULL = "agreed by phone",
  0 = free, >0 = amount. Honest UI for each state.

## Bugs caught during the conversation (the lessons)

1. **Arabic content in an LTR page** — offering `en` in LANGUAGES before
   translations existed made English browsers get `dir=ltr` Arabic. Lesson:
   never advertise a language you can't serve. (Later reversed properly in M20.)
2. **`<slug:>` rejects Arabic** — URL converter is Latin-only; use `<str:>`.
3. **Django ≥4.1 caches templates even in DEBUG** — with `--noreload` the
   cache never invalidates; template edits silently ignored.
4. **`{# #}` comments are single-line** — a two-line comment rendered as page text.
5. **Closing an upload stream breaks the save** — thumbnail code used
   `with image.open()`; storage later hit "I/O operation on closed file".
   Read bytes + `seek(0)`, never close what others still need.
6. **`exclude` + declared `fieldsets` crashes admin forms** — must filter
   `get_fieldsets` too (merchant seller-field hiding).
7. **Data migrations see no permissions on fresh DBs** — `post_migrate`
   hasn't run; call `create_permissions()` explicitly before creating groups.
8. **Silent coupon drop at checkout** — an exhausted coupon was quietly
   removed and the customer charged full price; checkout must fail loudly
   with the reason. Caught by test before shipping.
9. **Arabic locale renders template floats as ٤٫٠** — format numbers
   server-side when you need `4.0`.
10. **`.mo` was gitignored** — a fresh clone would silently lose English;
    committed deliberately (no deploy pipeline yet).
11. **Substring traps in Arabic assertions** — «ريف دمشق» contains «دمشق»;
    assert on attributes/pks, not bare city names.

## How to add new translatable text (established M20)

```
manage.py makemessages -l en --ignore=.venv --ignore=staticfiles
python scripts/translate_en.py     # fills from map; FAILS listing anything missing
manage.py compilemessages -l en
```
gettext lives at `%LOCALAPPDATA%\Programs\gettext-iconv\bin` (installed via
`winget install mlocati.GetText`, user scope — prefix PATH when running).

## Current state (2026-07-09)

Fully functional COD marketplace: catalog with sales & reviews & thumbnails,
Arabic search with live suggestions, session cart with coupons, zone-based
delivery fees, checkout with live totals, order tracking, accounts
(customer/merchant/staff roles), owner notifications, branded bilingual UI
and admin, sitemap/SEO — plus, since Tier 2 (M25–M28): login rate-limiting,
an admin sales dashboard, an installable PWA with an offline page, and
one-command rotating backups. 167-test suite, docs for the company.

**Waiting on Omar:** ShamCash API + visual identity (hook ready in
`apps/orders/payments.py`) · real delivery fees per governorate (admin →
مناطق التوصيل) · final logo from Figma (swap one asset + regenerate PWA icons
with `scripts/make_pwa_icons.py`) · deployment decision (VPS; prod settings
ready) · scheduling `manage.py backup` (Task Scheduler / cron one-liners are
in the command help).

**Suggested Tier 3 backlog:** PostgreSQL full-text search, translatable
product fields, wishlist, sales CSV export; in prod, a shared cache (Redis /
DatabaseCache) so rate-limit counters stay exact across Gunicorn workers.

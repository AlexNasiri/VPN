
## Cloudflare Worker Relay improvements

- Added live Worker health/status checks with last deploy/check timestamps and latency.
- Added real Worker disable and delete controls using Cloudflare APIs.
- Added custom domain/subdomain selection and switching via Cloudflare Worker Domains.
- Improved API Token and permission error messages.
- Kept the existing Worker name across redeploys to preserve URLs and bindings.
- Added an in-panel explanation of the Worker Relay flow.
### Audit and integration hardening
- Worker relay now restricts forwarded paths to VLESS tunnel, subscription and readiness endpoints.
- Worker deployment validates workers.dev activation, resolves the account subdomain, performs a public readiness check, and cleans up failed/orphaned Workers.
- Gateway accepts the configured Cloudflare Worker origin for WebSocket handshakes.
- Subscription endpoint now treats non-browser clients with `*/*`/empty Accept as machine subscriptions.
- Railway deployments fail closed when `/data` is expected but not actually mounted as a Volume.
- Redis-backed multi-instance deployments require a stable `SESSION_SECRET` so CSRF tokens remain valid across replicas.
- Control-plane login/setup body-size limits now apply to the correct API endpoints.


### Railway persistence installer
- Added idempotent Railway deployment scripts that create/retain a `/data` Volume before deployment.
- Added explicit documentation explaining why a normal application startup cannot safely attach its own Railway Volume.
# Changelog

## 4.1-hardened — current

### Final audit fixes
- Automatically creates the account-level `workers.dev` subdomain when it does not exist, instead of failing after uploading the Worker.
- Retires the previously active Cloudflare Worker after the replacement passes the external readiness check, preventing orphaned Workers from accumulating.
- Added regression coverage for strict Worker gate handling and public Worker-based link generation.


This release consolidates the 4.0 production hardening and the 4.1.1 fixes into the current hardened baseline.

### Security and hardening

- First-run admin password setup with no built-in/default password.
- Admin password policy is intentionally simple: minimum 4 characters with no uppercase/lowercase, digit, or symbol requirements.
- Argon2id password hashing retained as the primary scheme with transparent PBKDF2 migration.
- Trusted-proxy CIDR validation before accepting `X-Forwarded-For`.
- SSRF/DNS-rebinding hardening for the HTTP proxy and VLESS destination handling.
- Explicit proxy and VLESS destination port allowlists.
- HTTP body and WebSocket frame limits.
- CSRF protection and hardened security headers/CSP.
- Encrypted automatic backups written atomically.

### Deployment

- Added idempotent Railway deployment scripts that create/retain a `/data` Volume before deployment.
- Documented the Railway limitation: the application container itself cannot safely attach a missing Volume before its first deployment.

### Reliability and correctness

- Added `SUBSCRIPTION_INDEX` for O(1) subscription-token lookup and a unique SQLite index.
- Added fail-fast runtime configuration validation.
- Fixed the automatic-backup lifecycle using FastAPI lifespan handling.
- Fixed the global WebSocket connection-limit race with an atomic counter.
- Fixed usage-flush retry behavior so dirty usage markers survive persistence failures.
- Serialized usage persistence with link mutations to avoid stale quota-reset writes.
- Delayed in-memory link mutations until successful SQLite persistence.
- Rejected non-finite/oversized traffic and speed limits before SQLite conversion.
- Rejected invalid non-empty expiry dates instead of silently treating them as no expiry.
- Improved WebSocket cancellation and cleanup.
- Reduced sensitive tunnel details in error logs.
- Added readiness checks including SQLite integrity and optional Redis connectivity.
- Added storage health checking for persistent volumes.

### Repository/CI

- Docker runtime uses a non-root user.
- CI is based on the standard-library `unittest` test runner and Python 3.13.
- CI checks Python syntax, dependency consistency, tests, and accidental generated Python artefacts without leaving bytecode in the working tree.
- Documentation was aligned with the current 4.1-hardened code and configuration contract.

## 4.0 Production

- Hardened SQLite connections with WAL, busy timeout, foreign keys and safe directory creation.
- Added request-size limits for control-plane endpoints.
- Added per-request `X-Request-ID` correlation IDs.
- Added COOP/CORP security headers.
- Added Docker health checks and non-root execution.
- Kept first-run admin password setup.
- Kept HTTP proxy fail-closed unless explicitly configured otherwise.
- Kept SSRF/DNS-rebinding protections and VLESS frame/port limits.

## 3.x and earlier

Historical releases are not reconstructed here because the current repository did not contain a complete, authoritative release history for every older version. Refer to Git history for the original commit-level history.

## Review pass (latest session)

### Fixed — Railway restart-loop investigation
- `/health/ready` was running a full `PRAGMA integrity_check` (a complete
  scan of the SQLite file) on **every single call** — and it's called
  repeatedly: every 30s by the Docker `HEALTHCHECK` and periodically by
  Railway's own health probe. On a small (150-link) test database this was
  measured at ~10x slower than a trivial query, and the cost grows with DB
  size (more links, more audit-log/usage history). If it ever took longer
  than Docker's 5s `HEALTHCHECK` timeout, the container would be marked
  unhealthy and restarted — which looks identical to "Railway keeps killing
  the panel" from the outside, with nothing actually wrong. The integrity
  check now runs exactly once, at process startup (`lifespan`), where a
  full scan belongs; `/health/ready` now does a cheap `SELECT 1` ping on
  every call instead (`_db_quick_ping_sync`).
- `_rate_limiters` (per-link speed-limit token buckets) was never cleaned
  up when a link was deleted (single delete, bulk delete, or backup
  restore) — a small, permanent per-uid memory leak over the life of a
  long-running deployment. Now cleared alongside `_notified_pct` /
  `link_hourly_traffic` in all three places.
- (Confirmed already fixed in this codebase, not new in this pass, but
  directly relevant to "VLESS connects for a few seconds then drops on
  Railway": the `_tune_socket` TCP_NODELAY fix and the `_allowed_origins`
  auto-detected-host fix for `RAILWAY_PUBLIC_DOMAIN`. If those symptoms
  still occur, double-check the deployed image is actually this reviewed
  version and not an older build.)

## Review pass (previous session)

### Added — User-experience features
- **صفحه‌ی `/sub/{token}`**: بخش «افزودن مستقیم به اپلیکیشن» با دکمه‌های
  deep-link برای V2rayNG، Hiddify، Shadowrocket، Clash، Streisand و
  sing-box (schemeهای مرجع از مستندات رسمی هر اپ / لیست Marzban)، طوری که
  کاربر نهایی (نه لزوماً فنی) بتواند لینک اشتراک را مستقیماً در اپ نصب‌شده
  باز کند، بدون نیاز به کپی/پیست دستی.
- **عملیات گروهی روی جدول لینک‌ها**: چک‌باکس روی هر ردیف + «انتخاب همه»،
  نوار عملیات دسته‌ای (فعال‌سازی، غیرفعال‌سازی، ریست مصرف، تمدید ۳۰ روزه،
  حذف) که با یک درخواست `POST /api/links/bulk` روی تا ۵۰۰ لینک هم‌زمان اجرا
  می‌شود؛ برای نوشتن روی SQLite هم به‌جای یک اتصال جدا به ازای هر لینک، از
  `executemany` روی یک اتصال مشترک استفاده شده (`_db_bulk_upsert_links` /
  `_db_bulk_delete_links`).
- **دکمه‌ی سریع «تمدید ۳۰ روزه» روی هر ردیف** (کنار دکمه‌ی ریست مصرف که از
  قبل وجود داشت)، برای تمدید تک‌لینکی بدون باز کردن مودال ویرایش.
- **وضعیت زنده‌ی Cloudflare Worker**: `loadCloudflareStatus` هر ۲۰ ثانیه
  خودکار اجرا می‌شود (مثل الگوی polling موجود برای Ads Block)، و دکمه‌ی
  Deploy در حین انتظار برای health-check سمت سرور (که می‌تواند تا چند ده
  ثانیه طول بکشد) یک شمارنده‌ی ثانیه‌شمار نمایش می‌دهد تا معلوم باشد پنل
  هنگ نکرده.

## Review pass (previous session)

### Fixed
- CSP `style-src`/`font-src` did not include `https://fonts.googleapis.com` /
  `https://fonts.gstatic.com`, even though `FONT_LINKS` (used on every page:
  login, dashboard, sub, sub-not-found) loads the Vazirmatn/JetBrains Mono
  stylesheet and fonts from exactly those origins. Browsers enforcing the
  CSP silently blocked the Google Fonts `<link>` and the referenced font
  files (visible only as a CSP violation in devtools), so the site always
  fell back to a generic system font. Both origins are now explicitly
  allowed.
- Removed the unused `fastapi.middleware.cors.CORSMiddleware` import; CORS
  is fully handled by the custom `dynamic_cors_middleware`.

## Review pass (previous session)

### Fixed
- `_db_get_settings_sync` now goes through `_db_connect()` (WAL / busy_timeout
  PRAGMAs) instead of a bare `sqlite3.connect(DB_PATH)`, and its two callers
  now serialize through `DB_LOCK` like every other SQLite write/read path in
  the app. Previously a settings read landing at the same moment as a write
  (link create/update, usage flush, password change) could raise a raw
  "database is locked" error instead of waiting like the rest of the code.
- Renamed the duplicate `api_setup_status` function (the `/api/setup/status`
  handler) to `api_setup_wizard_status`. Two different route handlers shared
  the same Python function name — harmless today since FastAPI routes by
  path/decorator, not by function name, but it is a real footgun for future
  maintenance (`app.url_path_for(...)`, `generate_unique_id_function`, OpenAPI
  operation IDs, or a future dev debugging via function name would silently
  hit the wrong endpoint's code by name).

### Reviewed, no change needed
Went through SSRF handling (`is_blocked_ip`, `_alt_ip_literal`,
`resolve_safe_ip`, IP pinning), the VLESS header parser, CSRF/session/cookie
flow, login rate limiting, WebSocket origin/IP checks, the HTTP proxy
streaming path, backup encryption/restore validation, and the dashboard/login
templates for XSS. All of these already matched the hardening described in
`CHANGELOG.md`/`SECURITY.md` and are covered by `tests/test_security.py` and
`tests/test_hardening.py`; no further issues found there.

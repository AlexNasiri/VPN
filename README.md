# 🌀 Vortex Gateway

**زبان‌ها:** فارسی (اصلی) · [English](README_EN.md)

Vortex Gateway یک Gateway سخت‌سازی‌شده برای **VLESS روی WebSocket** است که داشبورد مدیریت، سهمیه و محدودیت اتصال/ترافیک، HTTP Proxy کنترل‌شده، Backup رمزنگاری‌شده SQLite، Redis اختیاری برای Session و Rate Limit توزیع‌شده، و Cloudflare Worker Relay اختیاری را ارائه می‌دهد.

نسخه فعلی: **4.1-hardened**

> ⚠️ **نکته امنیتی:** VLESS UUID، Subscription URL/Token، نشست ادمین و کلید Backup را Secret در نظر بگیرید. هرگز `.env`، دیتابیس Production، API Token یا Backupهای واقعی را commit نکنید.

---

## ✨ قابلیت‌ها

- 🔐 Setup یک‌باره رمز ادمین در اولین اجرا؛ هیچ رمز پیش‌فرضی وجود ندارد.
- 🔑 Hash رمز با Argon2id و مهاجرت PBKDF2 برای نصب‌های قدیمی.
- 🛡️ CSRF Protection برای عملیات تغییر‌دهنده وضعیت.
- 🚦 Login Rate Limit به‌صورت Per-IP و Global و محدودیت اندازه Request.
- 🌐 پذیرش `X-Forwarded-For` فقط از Proxyهای مورداعتماد.
- 🧱 محافظت SSRF شامل آدرس‌های Private/Loopback/Link-local/Multicast/Reserved و شکل‌های خاص IPv4/IPv6.
- 🔒 IP Pinning پس از DNS Resolve برای کاهش DNS-Rebinding risk.
- 🚫 HTTP Proxy به‌صورت پیش‌فرض **Fail-Closed** و با Allowlist دامنه/پورت.
- 🌊 Streaming Proxy با محدودیت اندازه Request/Response.
- 📏 اعتبارسنجی سخت‌گیرانه VLESS برای Version، UUID، Command، Destination و Port.
- ♻️ Restore تراکنشی/Atomic برای SQLite.
- 🗃️ Audit Log و آمار Connection/Traffic.
- ❤️ Liveness و Readiness Endpoint.
- 🔐 Backup با Fernet؛ Restore از Backup خام فقط با فعال‌سازی صریح.
- ⚡ Redis اختیاری برای Session و Login Rate Limit توزیع‌شده.
- ☁️ Deploy کردن Cloudflare Worker Relay از Dashboard.
- 🐳 Docker غیر Root و تنظیمات Railway.
- 🧪 تست‌های امنیتی خودکار.

## 🏗️ معماری

```text
                         ┌──────────────────────┐
                         │   داشبورد مدیریت     │
                         │ login / links / ops  │
                         └──────────┬───────────┘
                                    │
                                    ▼
┌───────────────┐        ┌──────────────────────┐        ┌────────────────┐
│ VLESS Clients │───────▶│    Vortex Gateway    │───────▶│ Public targets │
└───────────────┘   WS   │  Railway / Docker    │ Proxy  └────────────────┘
                         │ SQLite + optional    │
                         │ Redis + backups      │
                         └──────────┬───────────┘
                                    ▲
                                    │ relay
                         ┌──────────┴───────────┐
                         │ Optional Cloudflare  │
                         │      Worker          │
                         └──────────────────────┘
```

**Cloudflare Worker فقط Relay است.** منطق VLESS، احراز هویت، Quota، سیاست Proxy و وضعیت Database در Vortex Gateway باقی می‌ماند.

## 📋 پیش‌نیازها

- Python **3.13** برای توسعه محلی.
- Docker سازگار با Python 3.13 یا Railway.
- Storage دائمی برای SQLite در Production.
- Redis اختیاری برای Session و Login State توزیع‌شده.

## 🚀 اجرای سریع

### نصب

```bash
git clone <YOUR-REPOSITORY-URL>
cd vortex-gateway-4.1-hardened
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Storage محلی

Default `DB_PATH` برابر `/data/vortex_data.db` است که برای Container/Railway مناسب است. در اجرای محلی مسیر writable محلی تعیین کنید:

PowerShell:

```powershell
$env:DB_PATH = "$PWD\vortex_data.db"
$env:LOG_PATH = "$PWD\vortex.log"
```

Linux/macOS:

```bash
export DB_PATH="$PWD/vortex_data.db"
export LOG_PATH="$PWD/vortex.log"
```

### اجرا

```bash
python main.py
```

سپس:

```text
http://localhost:8000/login
```

در اولین اجرا صفحه Setup نمایش داده می‌شود. رمز ادمین باید **حداقل ۴ کاراکتر** باشد؛ هیچ اجباری برای حروف بزرگ/کوچک، عدد یا نماد وجود ندارد.

`ADMIN_PASSWORD` اختیاری است و فقط برای Bootstrap امن‌تر در محیط‌های بدون Volume استفاده می‌شود؛ مقدار آن باید در Secret/Variables سرویس تنظیم شود و هرگز داخل کد commit نشود.

## 🚂 استقرار روی Railway

1. Repository را روی GitHub قرار دهید.
2. در Railway یک Project از GitHub Repository بسازید.
3. Build را با `Dockerfile` انجام دهید.
4. برای استقرار خودکار و جلوگیری از خراب‌شدن رمز/لینک‌ها، بعد از `railway link` اسکریپت `scripts/deploy-railway.ps1` را در Windows یا `scripts/deploy-railway.sh` را در Linux/macOS اجرا کنید؛ اگر Volume مسیر `/data` وجود نداشته باشد خودش آن را می‌سازد و بعد Deploy می‌کند.
5. اگر از Deploy مستقیم GitHub در داشبورد Railway استفاده می‌کنید، Volume را یک‌بار روی `/data` متصل کنید؛ یک `railway.toml` معمولی نمی‌تواند Volume را در همان Deploy به‌صورت امن قبل از اولین اجرا ایجاد و متصل کند.
6. تنظیم کنید:

```text
DB_PATH=/data/vortex_data.db
```

6. Deploy کنید و `/login` را باز کنید.
7. Setup رمز ادمین را کامل کنید.

`railway.toml` تنظیمات Docker Build، Readiness و Restart Policy را فراهم می‌کند. Railway معمولاً `PORT` را inject می‌کند.

> ⚠️ بدون Volume دائمی، Redeploy می‌تواند SQLite و در نتیجه Linkها، تنظیمات، Audit History و Hash رمز ادمین را از بین ببرد.

## 🐳 Docker

```bash
docker build -t vortex-gateway .
```

اجرای محلی:

```bash
docker run --rm \
  -p 8000:8000 \
  -v "$PWD/data:/data" \
  -e DB_PATH=/data/vortex_data.db \
  -e LOG_PATH=/data/vortex.log \
  vortex-gateway
```

## ⚙️ متغیرهای محیطی

این جدول با Defaultهای فعلی کد هماهنگ است.

| متغیر | پیش‌فرض | کاربرد |
|---|---|---|
| `PORT` | `8000` | پورت HTTP؛ Railway معمولاً آن را تعیین می‌کند. |
| `RAILWAY_PUBLIC_DOMAIN` | `localhost` | Host عمومی برای ساخت Linkها؛ `https://` وارد نکنید. |
| `DB_PATH` | `/data/vortex_data.db` | مسیر SQLite. |
| `LOG_PATH` | `vortex.log` | مسیر Log چرخشی. |
| `TRUST_PROXY` | `0` | اعتماد به Forwarding Headerها فقط با فعال‌سازی صریح. |
| `TRUSTED_PROXY_CIDRS` | خالی | شبکه‌های Proxy مورداعتماد؛ با `TRUST_PROXY=1` لازم است. |
| `SESSION_SECRET` | خالی | وقتی `REDIS_URL` فعال است اجباری؛ راز تصادفی پایدار برای هماهنگی CSRF بین Replicaها. |
| `REQUIRE_PERSISTENT_VOLUME` | `0` | اگر روی `1` باشد، در Railway بدون Volume واقعی برنامه متوقف می‌شود؛ `0` اجازه می‌دهد بدون Volume اجرا شود و `/data` را موقتاً استفاده کند. برای داده دائمی، Volume در `/data` توصیه می‌شود. |
| `BACKUP_ENCRYPTION_KEY` | خالی | Fernet Key برای Backup رمزدار. |
| `ALLOW_PLAINTEXT_BACKUP` | `0` | فعال‌سازی Restore از Backup خام/قدیمی. |
| `ALLOW_LEGACY_SUBSCRIPTION_UUID` | `0` | پذیرش موقت Subscription URL قدیمی مبتنی بر UUID. |
| `PROXY_ALLOWED_DOMAINS` | خالی | Allowlist مقصدهای HTTP Proxy، مانند `example.com` یا `*.example.org`. |
| `PROXY_REQUIRE_ALLOWLIST` | `1` | با فعال بودن، Proxy بدون Allowlist رد می‌شود. |
| `PROXY_ALLOWED_PORTS` | `80,443,8080,8443` | Portهای مجاز HTTP Proxy خروجی. |
| `TUNNEL_ALLOWED_PORTS` | `80,443,8080,8443` | Portهای مجاز مقصد VLESS. |
| `PROXY_MAX_RESPONSE_BYTES` | `52428800` | حداکثر Response Proxy، برابر 50 MiB. |
| `PROXY_MAX_URL_LENGTH` | `8192` | حداکثر طول URL Proxy. |
| `MAX_HTTP_BODY_BYTES` | `2097152` | حداکثر Body کنترل‌پلین، برابر 2 MiB. |
| `MAX_LOGIN_BODY_BYTES` | `16384` | حداکثر Body برای Login/Setup. |
| `MAX_WS_INITIAL_BYTES` | `16384` | حداکثر Frame اولیه VLESS WebSocket. |
| `MAX_CONNECTIONS_GLOBAL` | `500` | سقف Connection همزمان کل. |
| `MAX_CONNECTIONS_PER_IP` | `25` | سقف Connection همزمان برای هر IP. |
| `MAX_CONNECTIONS_PER_LINK` | `50` | سقف Connection همزمان برای هر Link. |
| `AUTO_BACKUP_INTERVAL_HOURS` | `24` | فاصله Backup خودکار؛ `<=0` برای غیرفعال کردن. |
| `AUTO_BACKUP_KEEP` | `7` | تعداد Backupهای خودکار نگهداری‌شده. |
| `AUTO_BACKUP_DIR` | `/data/backups` | مسیر Backupهای خودکار. |
| `TELEGRAM_BOT_TOKEN` | خالی | Token اختیاری Telegram Bot. |
| `TELEGRAM_CHAT_ID` | خالی | Chat ID مقصد Telegram. |

### متغیر پشتیبانی‌نشده

`ADMIN_PASSWORD` اختیاری است؛ اگر در Railway به‌صورت Secret/Variable تنظیم شود، در اولین اجرای دیتابیس بدون رمز، فقط hash آن با Argon2id ذخیره می‌شود. در Production اتصال Volume به `/data` روش اصلی است. روی Railway، در حالت پیش‌فرض `REQUIRE_PERSISTENT_VOLUME=0` است؛ بنابراین برنامه بدون Volume هم بالا می‌آید، اما داده‌های `/data` روی storage موقت قرار می‌گیرند و ممکن است با Redeploy/تعویض Container از بین بروند. برای داده دائمی، `REQUIRE_PERSISTENT_VOLUME=1` و Volume واقعی روی `/data` را تنظیم کنید.

## 💾 Backup و Restore

ساخت Fernet Key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

سپس به‌عنوان Secret ذخیره کنید:

```text
BACKUP_ENCRYPTION_KEY=<generated-key>
```

کلید را کنار Backupها ذخیره نکنید. از دست دادن آن یعنی Backup رمزنگاری‌شده قابل Restore نخواهد بود.

Backupهای خودکار قبل از نصب نهایی فایل، رمزنگاری و Atomic ذخیره می‌شوند. Restore از Backup خام فقط با `ALLOW_PLAINTEXT_BACKUP=1` فعال می‌شود.

## 🛡️ امنیت HTTP Proxy

Proxy در Dashboard احراز هویت می‌شود و عملیات تغییر‌دهنده وضعیت به CSRF Token نیاز دارند. مقصدهای خروجی تحت SSRF Check و IP Pinning قرار می‌گیرند.

پیش‌فرض:

```text
PROXY_REQUIRE_ALLOWLIST=1
```

پس Allowlist خالی یعنی **Proxy غیرفعال و Fail-Closed**.

اگر عمداً `PROXY_REQUIRE_ALLOWLIST=0` را فعال کنید، Proxy می‌تواند به مقصدهایی که SSRF Check و Port Policy را پاس می‌کنند متصل شود. فقط در صورت نیاز عملیاتی مشخص از این حالت استفاده کنید.

## ☁️ Cloudflare Worker Relay

Dashboard می‌تواند یک Relay اختیاری Cloudflare Worker ایجاد کند.

```text
Client → Cloudflare Worker → Vortex Gateway → destination
```

Worker جایگزین Gateway نیست؛ درخواست را به Origin عمومی Vortex Forward می‌کند و منطق VLESS/Authentication در Gateway باقی می‌ماند.

Endpoint استقرار، Cloudflare API Token را فقط در Request احراز‌هویت‌شده دریافت می‌کند، آن را validate می‌کند و Account را پیدا می‌کند. Token در Database ذخیره نمی‌شود. Deployهای بعدی ترجیحاً همان Worker Name قبلی را به‌روزرسانی می‌کنند تا URL و لینک‌های موجود ثابت بمانند. پنل همچنین Health Check واقعی، زمان آخرین Deploy/Check، تغییر Custom Domain، غیرفعال‌سازی و حذف کامل Worker را ارائه می‌دهد.

برای این قابلیت Gateway باید از اینترنت عمومی قابل دسترسی باشد؛ localhost نمی‌تواند Origin Worker باشد.

## 🔌 APIها

### عمومی / Health

- `GET /` — Metadata سرویس.
- `GET /health` — وضعیت کلی.
- `GET /health/live` — Liveness.
- `GET /health/ready` — Readiness شامل Integrity SQLite و در صورت وجود Redis Connectivity.
- `GET /sub/{subscription_token}` — Subscription.
- `WS /tunnel/{uuid}` — VLESS WebSocket Tunnel.

### Authentication / Setup

- `GET /api/setup-status`
- `POST /api/setup-password`
- `POST /api/login`
- `POST /api/logout`
- `GET /api/me`
- `POST /api/change-password`

### Dashboard / Operations

- `GET /api/system/status`
- `POST /api/system/storage-test`
- `GET /api/stats`
- `GET /api/audit`
- `GET /api/connections`
- `POST /api/notify/test`
- `POST /api/cloudflare/deploy-worker`
- `GET /api/cloudflare/status` — Health check واقعی Worker و آخرین Deploy/Check.
- `POST /api/cloudflare/domains` — فهرست Custom Domainهای قابل استفاده برای Token.
- `POST /api/cloudflare/domain` — تغییر/اتصال دامنه یا زیردامنه Worker.
- `POST /api/cloudflare/disable-worker` — غیرفعال‌سازی دسترسی Worker بدون حذف اسکریپت.
- `POST /api/cloudflare/delete-worker` — حذف کامل Worker و Binding دامنه.

### Links / Backup

- `GET /api/links`
- `POST /api/links`
- `PATCH /api/links/{uid}`
- `DELETE /api/links/{uid}`
- `GET /api/links/{uid}/traffic`
- `GET /api/backup`
- `POST /api/backup/restore`

### Proxy احراز‌هویت‌شده

- `GET|POST|PUT|DELETE|PATCH|HEAD /api/proxy/{target_url}`

## 🧩 Redis و چند Instance

با `REDIS_URL`، Redis برای **Sessionهای توزیع‌شده و Login Rate Limiting** استفاده می‌شود.

SQLite همچنان منبع اصلی داده‌های Link و Stateهای دائمی است؛ بنابراین این Release از نظر Database-backed state هنوز عمدتاً **Single-Instance** است. چند Instance با SQLite جایگزین یک Database واقعی Multi-Writer نمی‌شود.

برای Scale افقی واقعی، PostgreSQL گزینه طبیعی مرحله بعد است و Redis می‌تواند Stateهای موقت/توزیع‌شده را مدیریت کند.

## 🔒 TLS و Reverse Proxy

برنامه خودش TLS را Terminate نمی‌کند. در Production این کار را در Railway، Reverse Proxy یا Load Balancer انجام دهید.

فقط وقتی واقعاً پشت Proxy مورداعتماد هستید تنظیم کنید:

```text
TRUST_PROXY=1
```

و شبکه‌های دقیق Proxy را در `TRUSTED_PROXY_CIDRS` مشخص کنید.

## 🧪 تست‌ها

پروژه از `unittest` استاندارد Python استفاده می‌کند و به `pytest` نیاز ندارد:

```bash
python -m unittest discover -s tests -v
```

CI فایل‌های Python را بدون تولید Bytecode Parse می‌کند. اجرای مشابه محلی:

```bash
python - <<'PY'
import ast
from pathlib import Path
for path in Path('.').rglob('*.py'):
    if any(part in {'.git', '.venv', 'venv', '__pycache__'} for part in path.parts):
        continue
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
print('Python syntax: OK')
PY
```

CI همچنین `pip check` را اجرا و نبود Artifactهای Bytecode را بررسی می‌کند.

## 📁 ساختار پروژه

```text
vortex-gateway-4.1-hardened/
├── main.py
├── templates.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── .dockerignore
├── railway.toml
├── README.md
├── README_EN.md
├── SECURITY.md
├── CHANGELOG.md
├── .github/
│   └── workflows/
│       └── ci.yml
└── tests/
    ├── __init__.py
    ├── test_security.py
    └── test_hardening.py
```

## 🔐 راهنمای امنیتی

قبل از Public کردن Repository:

- هرگز `.env`، SQLite DB، Log، Backup، Credential یا API Token را commit نکنید.
- `BACKUP_ENCRYPTION_KEY` واقعی را در Issue، PR، README یا Commit Message قرار ندهید.
- Subscription URLها را Credential در نظر بگیرید.
- در Production از Storage دائمی برای SQLite استفاده کنید.
- HTTP Proxy را تا زمانی که Allowlist و نیاز عملیاتی مشخص ندارید Fail-Closed نگه دارید.
- از یک رمز ادمین طولانی و یکتا استفاده کنید و در صورت افشا فوراً آن را تغییر دهید.

جزئیات اختصاصی در [SECURITY.md](SECURITY.md) آمده است.

## 🗺️ نقشه راه

- PostgreSQL برای State دائمی و Multi-Instance واقعی.
- مدیریت توزیع‌شده Quota/Connection با Redis.
- Prometheus Metrics.
- تست‌های End-to-End برای WebSocket و HTTP Proxy.
- Modular کردن `main.py` به auth/proxy/tunnel/database.
- Static Analysis/Linting و Vulnerability Check برای Dependencyها در CI.

## 📄 مجوز

در Repository فعلی License وجود ندارد. بدون افزودن License صریح، کاربران نباید فرض کنند که اجازه Copy، Modify یا Redistribute پروژه را دارند.

---

## English documentation

نسخه کامل انگلیسی در [README_EN.md](README_EN.md) قرار دارد.

"""
Vortex Gateway
یک گیت‌وی تونل‌زنی VLESS روی WebSocket به همراه HTTP Proxy امن‌شده و
داشبورد مدیریتی. طراحی و پیاده‌سازی مستقل، بدون کپی از پروژه‌های مشابه.
"""

import asyncio
import inspect
import glob
import contextlib
import base64
import hashlib
import hmac
import html
import ipaddress
import json
import logging
import logging.handlers
import math
import os
import secrets
import socket
import sqlite3
import time
import uuid as uuidlib
from collections import defaultdict, deque
from datetime import datetime
from typing import Literal
from urllib.parse import quote, urlparse

import httpx
try:
    import redis.asyncio as redis_async
except ImportError:  # optional distributed state backend
    redis_async = None
from cryptography.fernet import Fernet, InvalidToken
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response, StreamingResponse
from pydantic import BaseModel, Field


# Automatic SQLite backup settings.
AUTO_BACKUP_INTERVAL_HOURS = float(os.getenv("AUTO_BACKUP_INTERVAL_HOURS", "24"))
AUTO_BACKUP_KEEP = int(os.getenv("AUTO_BACKUP_KEEP", "7"))
AUTO_BACKUP_DIR = os.getenv("AUTO_BACKUP_DIR", "/data/backups")

LOG_PATH = os.environ.get("LOG_PATH", "vortex.log")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vortex")

# علاوه بر لاگِ stdout (که Railway/هر پلتفرمی خودش جمع‌آوری می‌کند)، یک فایل
# لاگ محلی هم با rotation نگه می‌داریم تا برای بررسی بعدی (مثلاً بعد از یک
# کرش یا رفتار عجیب) در دسترس باشد، بدون این‌که رشد بی‌نهایت فضای دیسک را
# مصرف کند: حداکثر ۵ مگابایت در هر فایل و ۳ نسخه‌ی قدیمی‌تر (در مجموع حداکثر
# ~۲۰ مگابایت).
try:
    _file_handler = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    _file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(_file_handler)
except OSError as exc:
    logger.warning("امکان نوشتن فایل لاگ در %s نبود (%s) — فقط لاگ stdout فعال است.", LOG_PATH, exc)

APP_NAME = "Vortex Gateway"
APP_VERSION = "4.1-hardened"

async def _automatic_sqlite_backup():
    """Create periodic encrypted SQLite backups without blocking the event loop.

    Automatic backups never write a plaintext database to disk.  If encryption is
    not configured, the worker stays disabled and logs a clear warning.
    """
    if AUTO_BACKUP_INTERVAL_HOURS <= 0:
        logger.info("automatic backups disabled: AUTO_BACKUP_INTERVAL_HOURS <= 0")
        return
    if not CONFIG["backup_encryption_key"]:
        logger.warning("automatic backups disabled: BACKUP_ENCRYPTION_KEY is not configured")
        return

    interval = max(60.0, AUTO_BACKUP_INTERVAL_HOURS * 3600)
    first_run = True
    while True:
        try:
            # Run once after startup, then on the configured interval.  This avoids
            # a 24-hour window after deployment where no recovery point exists.
            if not first_run:
                await asyncio.sleep(interval)
            first_run = False

            db_path = globals().get("DB_PATH")
            if not db_path or not os.path.exists(db_path):
                continue

            os.makedirs(AUTO_BACKUP_DIR, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
            tmp_db = os.path.join(AUTO_BACKUP_DIR, f".vortex-{stamp}.tmp.db")
            backup_path = os.path.join(AUTO_BACKUP_DIR, f"vortex-{stamp}.db.enc")

            def _backup():
                src_conn = sqlite3.connect(db_path, timeout=30)
                try:
                    dst_conn = sqlite3.connect(tmp_db, timeout=30)
                    try:
                        src_conn.backup(dst_conn)
                    finally:
                        dst_conn.close()

                    # Read the SQLite snapshot and wrap it in the same encrypted
                    # container used by manual backups.  The plaintext temporary
                    # file is removed before returning.
                    with open(tmp_db, "rb") as fh:
                        sqlite_bytes = fh.read()
                    encrypted = ENCRYPTED_BACKUP_PREFIX + _backup_cipher().encrypt(sqlite_bytes)
                    tmp_out = backup_path + ".tmp"
                    with open(tmp_out, "wb") as fh:
                        fh.write(encrypted)
                        fh.flush()
                        os.fsync(fh.fileno())
                    os.replace(tmp_out, backup_path)
                finally:
                    src_conn.close()
                    with contextlib.suppress(FileNotFoundError):
                        os.remove(tmp_db)

            await asyncio.to_thread(_backup)

            backups = sorted(
                glob.glob(os.path.join(AUTO_BACKUP_DIR, "vortex-*.db.enc")),
                key=os.path.getmtime,
                reverse=True,
            )
            for old in backups[AUTO_BACKUP_KEEP:]:
                with contextlib.suppress(OSError):
                    os.remove(old)
            logger.info("automatic encrypted SQLite backup created: %s", backup_path)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Backups must never take down the gateway.
            logger.error("automatic backup failed: %s", exc)



async def _graceful_shutdown():
    """Stop background workers and give active relay tasks a short grace period."""
    global _AUTO_BACKUP_TASK

    task = _AUTO_BACKUP_TASK
    _AUTO_BACKUP_TASK = None
    if task is not None and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Close known async clients if the application creates any at module scope.
    for name in ("HTTP_CLIENT", "http_client", "SESSION", "session"):
        resource = globals().get(name)
        close = getattr(resource, "aclose", None) if resource is not None else None
        if close is not None:
            try:
                result = close()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                pass

    active = []
    for name in ("ACTIVE_TASKS", "RELAY_TASKS"):
        value = globals().get(name)
        if isinstance(value, (set, list, tuple)):
            active.extend(t for t in value if isinstance(t, asyncio.Task) and not t.done())

    if active:
        _, pending = await asyncio.wait(active, timeout=5.0)
        for pending_task in pending:
            pending_task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


app = FastAPI(title=APP_NAME, docs_url=None, redoc_url=None)




_AUTO_BACKUP_TASK = None

# ───────────────────────── Config ─────────────────────────

CONFIG = {
    "port": int(os.environ.get("PORT", 8000)),
    "host_env": os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost"),
    # اجازه‌دادن به کاربر برای محدود کردن دامنه‌های مجاز پروکسی. اگر خالی باشد،
    # پروکسی برای هر دامنه‌ی عمومی (غیر داخلی) باز است اما همچنان در برابر SSRF محافظت می‌شود.
    "proxy_allowlist": [
        d.strip().lower()
        for d in os.environ.get("PROXY_ALLOWED_DOMAINS", "").split(",")
        if d.strip()
    ],
    # مسیر فایل SQLite برای ماندگاری لینک‌ها/رمز عبور بین ری‌استارت‌ها.
    # روی Railway اگر می‌خواهید بین دیپلوی‌های مجدد (نه فقط ری‌استارت ساده)
    # هم دیتا از دست نرود، باید یک Volume به همین مسیر متصل کنید؛ وگرنه
    # فایل‌سیستم کانتینر با هر deploy از صفر ساخته می‌شود.
    "db_path": os.environ.get("DB_PATH", "/data/vortex_data.db"),
    # On Railway, fail closed when /data is not an actual mounted Volume.
    # This prevents a fresh ephemeral SQLite DB from silently replacing the
    # persistent database and making the previously configured password fail.
    "require_persistent_volume": os.environ.get("REQUIRE_PERSISTENT_VOLUME", "0") == "1",
    # Optional bootstrap credential for deployments without a persistent volume.
    # Prefer a Railway secret variable over relying on ephemeral SQLite storage.
    "admin_password": os.environ.get("ADMIN_PASSWORD", ""),
    # اختیاری: توکن ربات تلگرام + chat_id برای ارسال هشدار وقتی مصرف یک لینک
    # به ۸۰٪/۹۰٪/۱۰۰٪ سقف ترافیک می‌رسد. اگر خالی باشند، این قابلیت به‌سادگی
    # غیرفعال می‌ماند (هیچ درخواست شبکه‌ای زده نمی‌شود).
    "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID", ""),
    "trust_proxy": os.environ.get("TRUST_PROXY", "0") == "1",
    "trusted_proxy_cidrs": [x.strip() for x in os.environ.get("TRUSTED_PROXY_CIDRS", "").split(",") if x.strip()],
    "proxy_require_allowlist": os.environ.get("PROXY_REQUIRE_ALLOWLIST", "1") == "1",
    "redis_url": os.environ.get("REDIS_URL", "").strip(),
    "session_secret": os.environ.get("SESSION_SECRET", "").strip(),
    "backup_encryption_key": os.environ.get("BACKUP_ENCRYPTION_KEY", "").strip(),
    "allow_plaintext_backup": os.environ.get("ALLOW_PLAINTEXT_BACKUP", "0") == "1",
    "allow_legacy_subscription_uuid": os.environ.get("ALLOW_LEGACY_SUBSCRIPTION_UUID", "0") == "1",
    "proxy_max_response_bytes": int(os.environ.get("PROXY_MAX_RESPONSE_BYTES", str(50 * 1024 * 1024))),
    "proxy_max_url_length": int(os.environ.get("PROXY_MAX_URL_LENGTH", "8192")),
    "proxy_allowed_ports": {int(x.strip()) for x in os.environ.get("PROXY_ALLOWED_PORTS", "80,443,8080,8443").split(",") if x.strip().isdigit()},
    # VLESS is a general TCP tunnel: restricting it to web ports breaks
    # ordinary VPN/app traffic (e.g. 5228, 993, 5223, etc.). Keep the legacy
    # TUNNEL_ALLOWED_PORTS variable for backward compatibility elsewhere, but
    # make VLESS filtering explicit and opt-in. Empty means all TCP ports.
    "tunnel_allowed_ports": {int(x.strip()) for x in os.environ.get("TUNNEL_ALLOWED_PORTS", "80,443,8080,8443").split(",") if x.strip().isdigit()},
    "vless_allowed_ports": {int(x.strip()) for x in os.environ.get("VLESS_ALLOWED_PORTS", "").split(",") if x.strip().isdigit()},
    "max_ws_initial_bytes": int(os.environ.get("MAX_WS_INITIAL_BYTES", "16384")),
    "max_connections_per_ip": int(os.environ.get("MAX_CONNECTIONS_PER_IP", "25")),
    "max_connections_global": int(os.environ.get("MAX_CONNECTIONS_GLOBAL", "500")),
    "max_http_body_bytes": int(os.environ.get("MAX_HTTP_BODY_BYTES", str(2 * 1024 * 1024))),
    "max_login_body_bytes": int(os.environ.get("MAX_LOGIN_BODY_BYTES", "16384")),
}

# کلید داخلی فقط برای امضای uuidهای دترمینیستیک استفاده می‌شود (نه برای پسورد)
INSTANCE_SECRET = secrets.token_bytes(32)
CSRF_SECRET = (CONFIG.get("session_secret") or "").encode("utf-8") or INSTANCE_SECRET

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

# ─── Zero-config public-host auto-detection ───────────────────────────────
# قبلاً همه‌چیز (کوکی secure، CORS، لینک‌های تولیدشده، چک Origin وب‌سوکت)
# فقط از روی RAILWAY_PUBLIC_DOMAIN تصمیم می‌گرفت. اما Railway صرفاً با
# ساختن دامنه‌ی عمومی از Settings → Networking این متغیر را خودکار داخل
# کانتینر تزریق نمی‌کند — باید دستی به‌عنوان Reference Variable اضافه شود،
# و خیلی از دیپلوی‌ها همین قدم را جا می‌اندازند. برای اینکه گیت‌وی بدون
# هیچ تنظیم دستی‌ای درست کار کند، دامنه‌ی عمومی واقعی را از روی هدر Host
# همان درخواستی که واقعاً از بیرون می‌رسد (که Railway/Cloudflare همیشه
# درست پاس می‌دهند) به‌صورت خودکار یاد می‌گیریم و به‌عنوان fallback بعد
# از RAILWAY_PUBLIC_DOMAIN استفاده می‌کنیم.
_DETECTED_PUBLIC_HOST: str | None = None
RAILWAY_DETECTED = bool(os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_PROJECT_ID"))


def _looks_like_public_host(host: str) -> bool:
    h = host.strip().lower().rstrip(".")
    if not h or h in _LOCAL_HOSTS:
        return False
    if h.endswith(".railway.internal"):
        return False
    return True


def _note_request_host(raw_host_header: str | None) -> None:
    """Learn the public hostname from a real incoming request, with zero configuration.

    Called on every HTTP/WebSocket request. Only takes effect when
    RAILWAY_PUBLIC_DOMAIN isn't explicitly set, so an explicit env var always
    wins when present.
    """
    global _DETECTED_PUBLIC_HOST
    if os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip():
        return
    if not raw_host_header:
        return
    parsed = urlparse(raw_host_header if "://" in raw_host_header else f"https://{raw_host_header}")
    host = (parsed.hostname or "").strip().rstrip(".")
    if not host or not _looks_like_public_host(host):
        return
    if parsed.port and parsed.port not in (80, 443):
        host = f"{host}:{parsed.port}"
    _DETECTED_PUBLIC_HOST = host


def get_host() -> str:
    """Return a normalized public hostname without scheme/path/port.

    Railway normally provides RAILWAY_PUBLIC_DOMAIN as a hostname, but users
    sometimes paste a full URL into the variable. Keeping one canonical form
    prevents malformed URLs such as https://https://example.com in CORS,
    cookies, generated subscriptions, and Worker deployment.

    When RAILWAY_PUBLIC_DOMAIN isn't set at all, we fall back to whatever
    public hostname we've automatically detected from real incoming traffic
    (see _note_request_host) instead of silently pretending to be localhost.
    """
    raw = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if not raw and _DETECTED_PUBLIC_HOST:
        raw = _DETECTED_PUBLIC_HOST
    if not raw:
        return "localhost"
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").strip().rstrip(".")
    if not host:
        return "localhost"
    if parsed.port and parsed.port not in (80, 443):
        host = f"{host}:{parsed.port}"
    return host


def get_public_origin() -> str:
    """Return the canonical public origin used by browser-facing URLs."""
    if get_host() in _LOCAL_HOSTS:
        return f"http://localhost:{CONFIG['port']}" if CONFIG["port"] != 80 else "http://localhost"
    return f"https://{get_host()}"


def cookie_secure() -> bool:
    """Whether Set-Cookie should carry the Secure flag.

    روی دیپلوی واقعی (Railway) همیشه HTTPS است؛ فقط برای اجرای لوکال روی
    localhost کوکی secure را غیرفعال می‌کنیم تا تست محلی خراب نشود. این
    مقدار دیگر ثابتِ زمان import نیست: علاوه بر هاست تشخیص‌داده‌شده، حضورِ
    متغیرهای خودکارِ Railway (RAILWAY_ENVIRONMENT_NAME/RAILWAY_PROJECT_ID —
    که برخلاف RAILWAY_PUBLIC_DOMAIN همیشه و بدون نیاز به تنظیم دستی توسط
    Railway تزریق می‌شوند) هم کافی است تا HTTPS واقعی را فرض کنیم، حتی قبل
    از اینکه اولین درخواست واقعی برسد و هاست را یاد بگیریم.
    """
    return RAILWAY_DETECTED or get_host() not in _LOCAL_HOSTS



# Public endpoint used for generated client configurations.  When a
# Cloudflare Worker relay is deployed, subscriptions/VLESS links must point
# to the Worker (including its private gate path), not directly to Railway.
ACTIVE_WORKER_URL = ""


def _worker_endpoint_parts() -> tuple[str, str] | None:
    base = ACTIVE_WORKER_URL.strip().rstrip("/")
    if not base:
        return None
    parsed = urlparse(base)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        return None
    gate_path = parsed.path.rstrip("/")
    if not gate_path or gate_path == "/":
        return None
    return parsed.netloc, gate_path


# ───────────────────────── CORS ─────────────────────────
# توجه: چون پنل از کوکی سشن استفاده می‌کند، origin وایلدکارد را با credentials
# ترکیب نمی‌کنیم (این ترکیب یک ضعف امنیتی شناخته‌شده است).
#
# قبلاً از CORSMiddleware استانداردِ Starlette با یک allow_origins ثابت
# استفاده می‌شد که فقط یک‌بار، در زمان import ماژول (قبل از رسیدن هر
# درخواستی)، از روی RAILWAY_PUBLIC_DOMAIN محاسبه می‌شد. همان مشکلِ
# RAILWAY_PUBLIC_DOMAIN تنظیم‌نشده اینجا هم بود، به‌علاوه‌ی اینکه حتی اگر
# بعداً هاست را از روی ترافیک واقعی یاد بگیریم، آن لیست ثابت هرگز به‌روز
# نمی‌شد. به‌جایش این میدل‌ور سبک، مبدأهای مجاز را در لحظه‌ی هر درخواست
# با _allowed_origins() (همان منطقِ خودکار/بدون‌نیاز-به-تنظیم استفاده‌شده
# برای وب‌سوکت) حساب می‌کند.
@app.middleware("http")
async def dynamic_cors_middleware(request: Request, call_next):
    # هر درخواست واقعی (نه فقط آن‌هایی که Origin دارند) هاست عمومی را
    # خودکار یاد می‌گیرد تا get_host()/cookie_secure() از همان اولین
    # درخواست درست کار کنند، حتی بدون تنظیم RAILWAY_PUBLIC_DOMAIN.
    _note_request_host(request.headers.get("host"))
    origin = request.headers.get("origin")
    if request.method == "OPTIONS" and origin:
        allowed = _allowed_origins(request.headers.get("host"))
        if origin in allowed:
            resp = Response(status_code=200)
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-CSRF-Token"
            resp.headers["Vary"] = "Origin"
            return resp
        return Response(status_code=400)
    response = await call_next(request)
    if origin:
        allowed = _allowed_origins(request.headers.get("host"))
        if origin in allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
    return response


@app.middleware("http")
async def request_size_middleware(request: Request, call_next):
    # Reject oversized control-plane requests before parsing JSON/forms.
    # WebSocket upgrades are intentionally excluded; their own frame limits
    # are enforced in the tunnel handler.
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
            except ValueError:
                return JSONResponse({"detail": "invalid content-length"}, status_code=400)
            limit = CONFIG["max_login_body_bytes"] if request.url.path in {"/api/login", "/api/setup-password"} else CONFIG["max_http_body_bytes"]
            if length > limit:
                return JSONResponse({"detail": "request body too large"}, status_code=413)
    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    # دفاع اضافه برای پنل مدیریتی که با کوکی سشن کار می‌کند: جلوگیری از
    # کلیک‌جکینگ (X-Frame-Options)، sniff نادرست نوع محتوا، و محدودکردن
    # منابعی که صفحه اجازه‌ی بارگذاری دارد (چون از Chart.js و آیکن‌های CDN
    # استفاده می‌شود، آن دامنه‌ها صراحتاً در CSP مجاز شده‌اند).
    #
    # یک nonce تصادفیِ per-request تولید می‌کنیم و به هندلرهای صفحه (از طریق
    # request.state) می‌دهیم تا فقط تگ‌های <script> که همین nonce را دارند
    # اجازه‌ی اجرا داشته باشند.
    #
    # نکته‌ی مهم (که باعث خرابی همه‌ی دکمه‌های داشبورد شده بود): طبق اسپک CSP،
    # وقتی یک nonce در script-src حاضر باشد، 'unsafe-inline' کاملاً نادیده
    # گرفته می‌شود — نه فقط برای تگ‌های <script>، بلکه برای attributeهای
    # event handler مثل onclick="..." هم. یعنی نگه‌داشتن 'unsafe-inline' در
    # کنار nonce هیچ فایده‌ای نداشت و صرفاً گمراه‌کننده بود. راه‌حل واقعی این
    # بود که همه‌ی onclick/onchange/oninput از HTML حذف و با addEventListener
    # داخل همان <script> نانس‌دار جایگزین شوند (templates.py) — این‌طوری
    # نیازی به unsafe-inline نیست و CSP هم واقعاً سخت‌گیرانه می‌ماند.
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce
    request_id = secrets.token_urlsafe(12)
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    if cookie_secure():
        # فقط وقتی واقعاً روی HTTPS هستیم (دیپلوی واقعی، نه اجرای لوکال) این
        # هدر را می‌فرستیم؛ چون به مرورگر می‌گوید برای مدت طولانی فقط HTTPS
        # را برای این دامنه بپذیرد، فرستادنش روی http://localhost باعث
        # می‌شود توسعه‌ی محلی بعداً به مشکل بخورد.
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    if request.url.path.startswith(("/api/", "/login", "/dashboard", "/sub/")):
        response.headers["Cache-Control"] = "no-store"
    return response

# ───────────────────────── In-memory state ─────────────────────────

LINKS: dict = {}
# O(1) subscription-token lookup. Keeping this separate from LINKS avoids an
# O(n) scan on every client refresh, which otherwise becomes expensive with
# thousands of subscriptions.
SUBSCRIPTION_INDEX: dict[str, str] = {}
LINKS_LOCK = asyncio.Lock()

connections: dict = {}
connections_by_ip: dict[str, int] = defaultdict(int)
# Tracks the asyncio Task running each active /tunnel/{uid} websocket handler,
# so _graceful_shutdown() can find and wait on real in-flight relay tasks
# (see websocket_tunnel below, which adds/removes itself here).
RELAY_TASKS: set = set()
CONNECTIONS_LOCK = asyncio.Lock()
stats = {"total_bytes": 0, "total_requests": 0, "total_errors": 0, "start_time": time.time()}
error_logs: deque = deque(maxlen=50)
hourly_traffic: dict = defaultdict(int)
# مشابه hourly_traffic ولی به‌ازای هر لینک، برای نمودار مصرف اختصاصی هر لینک
# در داشبورد. کلید بیرونی uuid لینک است، کلید داخلی همان الگوی ساعت ("HH:00").
link_hourly_traffic: dict = defaultdict(lambda: defaultdict(int))

http_client: httpx.AsyncClient | None = None
redis_client = None

# ───────────────────────── Persistence (SQLite) ─────────────────────────
# لینک‌ها و هش رمز عبور در یک فایل SQLite کنار برنامه ذخیره می‌شوند تا با
# ری‌استارت سرویس از بین نروند. دیکشنری‌های بالا (LINKS, AUTH) همچنان
# منبع اصلیِ خواندن سریع در مسیر داغِ کد (تونل/پروکسی) هستند؛ SQLite فقط
# برای نوشتن پشت‌صحنه و بارگذاری اولیه استفاده می‌شود — پس هیچ query ای
# در مسیر رله‌ی داده اجرا نمی‌شود و سرعت تونل تحت تأثیر قرار نمی‌گیرد.
DB_PATH = CONFIG["db_path"]
DB_LOCK = asyncio.Lock()  # نوشتن‌های sqlite را سریالایز می‌کند تا خطای "database is locked" رخ ندهد


def _db_connect() -> sqlite3.Connection:
    # SQLite is only used for control-plane persistence.  Make every
    # connection resilient to short write bursts and power-loss scenarios.
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _db_init():
    conn = _db_connect()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS links (
                uuid TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                limit_bytes INTEGER NOT NULL,
                used_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                active INTEGER NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                action TEXT NOT NULL,
                ip TEXT,
                details TEXT
            )"""
        )
        # مهاجرت برای دیتابیس‌های قدیمی‌تر: دو ستون جدید برای «تاریخ انقضا» و
        # «محدودیت سرعت» به‌ازای هر لینک. چون SQLite با نبود این ستون‌ها در
        # جدول‌های ساخته‌شده‌ی قبلی خطا می‌دهد، وجودشان را چک می‌کنیم و فقط
        # در صورت نبود اضافه می‌کنیم (ALTER TABLE ADD COLUMN ایمن و بدون
        # از دست رفتن داده‌ی موجود است).
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(links)").fetchall()}
        if "expires_at" not in existing_cols:
            conn.execute("ALTER TABLE links ADD COLUMN expires_at TEXT")
        if "speed_limit_bps" not in existing_cols:
            conn.execute("ALTER TABLE links ADD COLUMN speed_limit_bps INTEGER NOT NULL DEFAULT 0")
        if "subscription_token" not in existing_cols:
            conn.execute("ALTER TABLE links ADD COLUMN subscription_token TEXT")
        # مهاجرت: هر لینک می‌تواند مسیر تولید کانفیگش را انتخاب کند —
        # 'auto' (پیش‌فرض قبلی: اگر Worker فعال باشد از آن استفاده کن)،
        # 'railway' (همیشه مستقیم به Railway) یا 'cloudflare' (همیشه از Worker،
        # حتی اگر بعداً هم فعال شود). لینک‌های قدیمی همان رفتار قبلی auto را می‌گیرند.
        if "route_via" not in existing_cols:
            conn.execute("ALTER TABLE links ADD COLUMN route_via TEXT NOT NULL DEFAULT 'auto'")
        # Every link gets a high-entropy subscription secret. Existing UUID-based
        # subscriptions can be disabled after migration with ALLOW_LEGACY_SUBSCRIPTION_UUID=0.
        rows = conn.execute("SELECT uuid FROM links WHERE subscription_token IS NULL OR subscription_token = ''").fetchall()
        for (uid,) in rows:
            conn.execute("UPDATE links SET subscription_token=? WHERE uuid=?", (secrets.token_urlsafe(32), uid))
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_links_subscription_token ON links(subscription_token)")
        conn.commit()
    finally:
        conn.close()


# توابع sqlite3 استاندارد کتابخانه، حتی برای یک UPDATE ساده، synchronous و
# بلاک‌کننده هستند. قبلاً این توابع مستقیم داخل کوروتین‌ها صدا زده می‌شدند؛
# یعنی هر نوشتن روی دیسک (هرچند چند میلی‌ثانیه) کل event loop را می‌بست —
# همان event loop ای که هم‌زمان مسئول رله‌ی بایت‌های تونل‌های VLESS باز است.
# با هول‌دادن بخش synchronous به یک ترد جدا (asyncio.to_thread) این بلاک‌شدن
# از event loop اصلی حذف می‌شود؛ DB_LOCK همچنان نوشتن‌ها را سریالایز می‌کند
# تا خطای "database is locked" رخ ندهد.

def _db_get_settings_sync():
    """Return the application settings as a plain dict.

    This is kept synchronous because callers run database work through
    asyncio.to_thread(), avoiding blocking the event loop.

    Bug fixed in this audit: this function used to open a bare
    ``sqlite3.connect(DB_PATH)`` instead of going through ``_db_connect()``.
    That connection never received the WAL / busy_timeout PRAGMAs that every
    other connection in this module gets, so a call landing at the same
    moment as a write (e.g. link create/update, usage flush) could raise a
    raw "database is locked" error instead of transparently waiting like the
    rest of the app does. It is now routed through ``_db_connect()`` for a
    consistent, resilient connection.
    """
    conn = _db_connect()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT key, value FROM settings"
        ).fetchall()
    finally:
        conn.close()
    return {row["key"]: row["value"] for row in rows}


def _db_load_all_sync():
    conn = _db_connect()
    try:
        link_rows = conn.execute(
            "SELECT uuid, label, limit_bytes, used_bytes, created_at, active, "
            "expires_at, speed_limit_bps, subscription_token, route_via FROM links"
        ).fetchall()
        setting_rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return link_rows, setting_rows
    finally:
        conn.close()


async def _db_load_all():
    async with DB_LOCK:
        return await asyncio.to_thread(_db_load_all_sync)


def _db_upsert_link_sync(uid: str, data: dict):
    conn = _db_connect()
    try:
        conn.execute(
            """INSERT INTO links (uuid, label, limit_bytes, used_bytes, created_at, active,
                                   expires_at, speed_limit_bps, subscription_token, route_via)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(uuid) DO UPDATE SET
                   label=excluded.label, limit_bytes=excluded.limit_bytes,
                   used_bytes=excluded.used_bytes, created_at=excluded.created_at,
                   active=excluded.active, expires_at=excluded.expires_at,
                   speed_limit_bps=excluded.speed_limit_bps,
                   subscription_token=excluded.subscription_token,
                   route_via=excluded.route_via""",
            (uid, data["label"], data["limit_bytes"], data["used_bytes"],
             data["created_at"], int(data["active"]),
             data.get("expires_at"), data.get("speed_limit_bps", 0),
             data.get("subscription_token") or secrets.token_urlsafe(32),
             data.get("route_via") or "auto"),
        )
        conn.commit()
    finally:
        conn.close()


async def _db_upsert_link(uid: str, data: dict):
    async with DB_LOCK:
        await asyncio.to_thread(_db_upsert_link_sync, uid, data)


def _db_delete_link_sync(uid: str):
    conn = _db_connect()
    try:
        conn.execute("DELETE FROM links WHERE uuid=?", (uid,))
        conn.commit()
    finally:
        conn.close()


async def _db_delete_link(uid: str):
    async with DB_LOCK:
        await asyncio.to_thread(_db_delete_link_sync, uid)


def _db_replace_all_links_sync(links_snapshot: dict):
    conn = _db_connect()
    try:
        conn.execute("DELETE FROM links")
        conn.executemany(
            "INSERT INTO links (uuid, label, limit_bytes, used_bytes, created_at, active, "
            "expires_at, speed_limit_bps, subscription_token, route_via) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (uid, d["label"], d["limit_bytes"], d["used_bytes"], d["created_at"], int(d["active"]),
                 d.get("expires_at"), d.get("speed_limit_bps", 0), d.get("subscription_token") or secrets.token_urlsafe(32),
                 d.get("route_via") or "auto")
                for uid, d in links_snapshot.items()
            ],
        )
        conn.commit()
    finally:
        conn.close()


async def _db_replace_all_links(links_snapshot: dict):
    """برای بازیابی (restore) کامل: کل جدول links جایگزین می‌شود."""
    async with DB_LOCK:
        await asyncio.to_thread(_db_replace_all_links_sync, links_snapshot)


def _db_restore_sync(links_snapshot: dict, password_hash: str | None):
    conn = _db_connect()
    try:
        with conn:
            conn.execute("DELETE FROM links")
            conn.executemany(
                "INSERT INTO links (uuid, label, limit_bytes, used_bytes, created_at, active, expires_at, speed_limit_bps, subscription_token, route_via) VALUES (?,?,?,?,?,?,?,?,?,?)",
                [
                    (uid, d["label"], d["limit_bytes"], d["used_bytes"], d["created_at"], int(d["active"]), d.get("expires_at"), d.get("speed_limit_bps", 0), d.get("subscription_token") or secrets.token_urlsafe(32), d.get("route_via") or "auto")
                    for uid, d in links_snapshot.items()
                ],
            )
            if password_hash is not None:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    ("password_hash", password_hash),
                )
    finally:
        conn.close()


async def _db_restore(links_snapshot: dict, password_hash: str | None):
    async with DB_LOCK:
        await asyncio.to_thread(_db_restore_sync, links_snapshot, password_hash)


def _db_audit_sync(action: str, ip: str, details: str):
    conn = _db_connect()
    try:
        conn.execute("INSERT INTO audit_log (created_at, action, ip, details) VALUES (?,?,?,?)", (datetime.now().isoformat(), action, ip, details[:1000]))
        conn.commit()
    finally:
        conn.close()


def _db_recent_audit_sync(limit: int):
    conn = _db_connect()
    try:
        return conn.execute("SELECT created_at, action, ip, details FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    finally:
        conn.close()


async def audit(action: str, ip: str = "", details: str = ""):
    try:
        await asyncio.to_thread(_db_audit_sync, action, ip, details)
    except Exception as exc:
        logger.warning("audit persistence failed: %s", exc)


def _db_set_setting_sync(key: str, value: str):
    conn = _db_connect()
    try:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


async def _db_set_setting(key: str, value: str):
    async with DB_LOCK:
        await asyncio.to_thread(_db_set_setting_sync, key, value)


# مصرف بایت‌به‌بایت هر پکت را مستقیم روی دیسک نمی‌نویسیم (خیلی کند می‌شود)؛
# فقط uid لینک‌های تغییرکرده را در یک set نگه می‌داریم و هر چند ثانیه یک‌بار
# با _flush_usage به‌صورت batch روی دیسک می‌نویسیم.
_dirty_usage_uids: set = set()
_usage_flush_task: asyncio.Task | None = None


def _flush_usage_sync(snapshot: list):
    conn = _db_connect()
    try:
        # Write the exact in-memory value captured under LINKS_LOCK.  A generation
        # check below prevents an older snapshot from clearing a newer dirty mark.
        conn.executemany("UPDATE links SET used_bytes=? WHERE uuid=?", snapshot)
        conn.commit()
    finally:
        conn.close()


async def _flush_usage():
    # Keep LINKS_LOCK while taking DB_LOCK and writing the snapshot.  This gives
    # control-plane operations (reset/delete/update) a consistent lock order and
    # prevents a quota reset from racing with an older usage flush.
    async with LINKS_LOCK:
        dirty = list(_dirty_usage_uids)
        if not dirty:
            return
        snapshot = [(LINKS[uid]["used_bytes"], uid) for uid in dirty if uid in LINKS]
        snapshot_values = {uid: value for value, uid in snapshot}
        try:
            async with DB_LOCK:
                await asyncio.to_thread(_flush_usage_sync, snapshot)
        except Exception as exc:
            # Never drop dirty markers when SQLite/I/O fails; the next periodic
            # pass must retry so usage cannot silently disappear.
            logger.error("usage flush failed; dirty state retained: %s", exc)
            return
        for uid in dirty:
            if uid not in LINKS or LINKS[uid]["used_bytes"] == snapshot_values.get(uid):
                _dirty_usage_uids.discard(uid)


async def _periodic_usage_flush():
    while True:
        try:
            await asyncio.sleep(10)
            await _flush_usage()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("usage flush error: %s", exc)

# ───────────────────────── Per-link speed throttling ─────────────────────────
# پیاده‌سازی «سطل توکن» (token bucket) برای محدودکردن سرعت هر لینک. ظرفیت
# سطل برابر نرخ مجاز در نظر گرفته می‌شود (یعنی حداکثر یک ثانیه burst مجاز
# است) که برای ترافیک واقعی (پکت‌های نامنظم) طبیعی‌تر از یک محدودیت سخت‌گیرانه
# است. یک باکت به‌ازای هر لینک، فقط وقتی speed_limit_bps > 0 باشد، ساخته می‌شود.
class _TokenBucket:
    __slots__ = ("rate", "capacity", "tokens", "last", "lock")

    def __init__(self, rate_bps: int):
        self.rate = rate_bps
        self.capacity = max(rate_bps, RELAY_BUF)
        self.tokens = float(self.capacity)
        self.last = time.monotonic()
        self.lock = asyncio.Lock()

    async def consume(self, n: int):
        async with self.lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
            self.last = now
            self.tokens -= n
            if self.tokens < 0:
                wait = -self.tokens / self.rate
                self.tokens = 0
                await asyncio.sleep(wait)


_rate_limiters: dict = {}  # uid -> (configured_rate_bps, _TokenBucket)


async def throttle(uid: str, rate_bps: int, n: int):
    """اگر لینک محدودیت سرعت داشته باشد، به اندازه‌ی لازم مکث می‌کند تا نرخ
    انتقال از سقف تعیین‌شده عبور نکند. اگر rate_bps صفر باشد (نامحدود) بلافاصله
    برمی‌گردد."""
    if rate_bps <= 0:
        return
    entry = _rate_limiters.get(uid)
    if entry is None or entry[0] != rate_bps:
        bucket = _TokenBucket(rate_bps)
        _rate_limiters[uid] = (rate_bps, bucket)
    else:
        bucket = entry[1]
    await bucket.consume(n)


# ───────────────────────── Telegram notifications ─────────────────────────
# هشدار اختیاری وقتی مصرف یک لینک به آستانه‌های ۸۰٪/۹۰٪/۱۰۰٪ سقف ترافیک
# می‌رسد. کاملاً اختیاری است — اگر TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ست
# نشده باشند، send_telegram_message بی‌سروصدا هیچ کاری نمی‌کند.
NOTIFY_THRESHOLDS = (80, 90, 100)
# آخرین آستانه‌ای که برای هر لینک اعلان ارسال شده (در حافظه؛ با ری‌استارت
# سرویس پاک می‌شود، یعنی ممکن است حداکثر یک اعلان تکراری بعد از هر ری‌استارت
# دریافت کنید — یک تبادل ساده برای این‌که مسیر داغِ رله‌ی داده هیچ نوشتن
# اضافه‌ای روی دیسک نداشته باشد).
_notified_pct: dict = defaultdict(int)


async def send_telegram_message(text: str) -> bool:
    token = CONFIG["telegram_bot_token"]
    chat_id = CONFIG["telegram_chat_id"]
    if not token or not chat_id or not http_client:
        return False
    try:
        resp = await http_client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )
        return resp.status_code == 200
    except Exception as exc:
        logger.error("telegram notify error: %s", exc)
        return False


def _maybe_schedule_quota_alert(uid: str, label: str, pct: float):
    crossed = None
    for t in NOTIFY_THRESHOLDS:
        if pct >= t and _notified_pct[uid] < t:
            crossed = t
    if crossed is None:
        return
    _notified_pct[uid] = crossed
    emoji = "🛑" if crossed >= 100 else "⚠️"
    text = f"{emoji} Vortex Gateway\nلینک «{label}» به {crossed}٪ از سقف ترافیک خود رسید."
    if crossed >= 100:
        text += "\nاین لینک تا بازنشانی/افزایش سقف، مسدود شده است."
    asyncio.create_task(send_telegram_message(text))


# ───────────────────────── Tunnel connection limits ─────────────────────────
# بدون این سقف‌ها، یک لینک (یا یک لینک لو‌رفته) می‌تواند هزاران WebSocket
# هم‌زمان باز کند و منابع سرور (فایل‌دیسکریپتور/رم/CPU) را با یک DoS ساده
# مصرف کند. یک سقف کلی و یک سقف به‌ازای هر لینک در نظر می‌گیریم.
MAX_CONNECTIONS_GLOBAL = CONFIG["max_connections_global"]
MAX_CONNECTIONS_PER_LINK = int(os.environ.get("MAX_CONNECTIONS_PER_LINK", "50"))
_link_conn_counts: dict = defaultdict(int)
_global_conn_count = 0
_conn_limit_lock = asyncio.Lock()


async def try_acquire_connection_slot(uid: str) -> bool:
    global _global_conn_count
    async with _conn_limit_lock:
        if _global_conn_count >= MAX_CONNECTIONS_GLOBAL:
            return False
        if _link_conn_counts[uid] >= MAX_CONNECTIONS_PER_LINK:
            return False
        _global_conn_count += 1
        _link_conn_counts[uid] += 1
        return True


async def release_connection_slot(uid: str):
    global _global_conn_count
    async with _conn_limit_lock:
        if _link_conn_counts.get(uid, 0) > 0:
            _link_conn_counts[uid] -= 1
            _global_conn_count = max(0, _global_conn_count - 1)
            if _link_conn_counts[uid] == 0:
                _link_conn_counts.pop(uid, None)

# ───────────────────────── Auth: password hashing ─────────────────────────

# Argon2id is the primary password hash. PBKDF2 is retained only for seamless
# migration of older installations; a successful PBKDF2 login is transparently
# upgraded to Argon2id.
PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16)
PBKDF2_ITERATIONS = 260_000

def hash_password(password: str, salt: bytes | None = None) -> str:
    return PASSWORD_HASHER.hash(password)

def _verify_pbkdf2(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False

def verify_password(password: str, stored: str) -> bool:
    if not stored:
        return False
    if stored.startswith("$argon2id$"):
        try:
            return PASSWORD_HASHER.verify(stored, password)
        except (VerifyMismatchError, InvalidHashError, ValueError):
            return False
    return _verify_pbkdf2(password, stored)

def password_needs_rehash(stored: str) -> bool:
    return bool(stored) and not stored.startswith("$argon2id$")

# The first-run password is always chosen by the operator in the web UI.
# There is intentionally no built-in/default credential, even for localhost.
# Until the operator completes setup, authentication remains disabled and the
# login page becomes a one-time password setup screen. Only the Argon2id hash
# is stored in the database.
AUTH = {"password_hash": "", "setup_required": True}

async def _bootstrap_admin_password(settings_map: dict[str, str]) -> None:
    stored_hash = settings_map.get("password_hash")
    if stored_hash:
        AUTH["password_hash"] = stored_hash
        AUTH["setup_required"] = False
        return

    # On ephemeral deployments, an operator can pin the admin password in a
    # Railway/host secret.  The secret is never written to logs or returned by
    # the API; only its Argon2id hash is persisted.
    bootstrap_password = CONFIG.get("admin_password", "")
    if bootstrap_password:
        err = _password_strength_error(bootstrap_password)
        if err is None:
            new_hash = hash_password(bootstrap_password)
            await _db_set_setting("password_hash", new_hash)
            AUTH["password_hash"] = new_hash
            AUTH["setup_required"] = False
            logger.info("🔐 admin password bootstrapped from deployment secret")
            return
        logger.error("ADMIN_PASSWORD is configured but invalid: %s", err)

    AUTH["password_hash"] = ""
    AUTH["setup_required"] = True

SESSION_COOKIE = "vortex_session"
CSRF_COOKIE = "vortex_csrf"
CSRF_HEADER = "x-csrf-token"
SESSION_TTL = 60 * 60 * 24 * 7  # 7 روز
SESSIONS: dict = {}
SESSIONS_LOCK = asyncio.Lock()

# ───────────────────────── Login brute-force protection ─────────────────────────

LOGIN_ATTEMPTS: dict = {}  # ip -> {"count": int, "locked_until": float}
LOGIN_LOCK = asyncio.Lock()
LOGIN_GLOBAL_EVENTS: deque[float] = deque()
MAX_GLOBAL_LOGIN_ATTEMPTS = 30
GLOBAL_LOGIN_WINDOW = 60
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 5 * 60


async def check_login_allowed(ip: str) -> tuple[bool, int]:
    now = time.time()
    if redis_client is not None:
        key = hashlib.sha256(ip.encode()).hexdigest()
        lock_key = f"vortex:login:lock:{key}"
        ttl = await redis_client.ttl(lock_key)
        if ttl and ttl > 0:
            return False, int(ttl)
        global_key = "vortex:login:global"
        count = await redis_client.get(global_key)
        if count and int(count) >= MAX_GLOBAL_LOGIN_ATTEMPTS:
            ttl = await redis_client.ttl(global_key)
            return False, max(1, int(ttl))
        return True, 0
    async with LOGIN_LOCK:
        while LOGIN_GLOBAL_EVENTS and LOGIN_GLOBAL_EVENTS[0] <= now - GLOBAL_LOGIN_WINDOW:
            LOGIN_GLOBAL_EVENTS.popleft()
        if len(LOGIN_GLOBAL_EVENTS) >= MAX_GLOBAL_LOGIN_ATTEMPTS:
            return False, max(1, int(LOGIN_GLOBAL_EVENTS[0] + GLOBAL_LOGIN_WINDOW - now))
        rec = LOGIN_ATTEMPTS.get(ip)
        if not rec:
            return True, 0
        if rec["locked_until"] and rec["locked_until"] > now:
            return False, int(rec["locked_until"] - now)
        return True, 0

async def record_login_failure(ip: str):
    if redis_client is not None:
        key = hashlib.sha256(ip.encode()).hexdigest()
        count_key = f"vortex:login:fail:{key}"
        lock_key = f"vortex:login:lock:{key}"
        global_key = "vortex:login:global"
        pipe = redis_client.pipeline()
        pipe.incr(count_key)
        pipe.expire(count_key, LOCKOUT_SECONDS)
        pipe.incr(global_key)
        pipe.expire(global_key, GLOBAL_LOGIN_WINDOW)
        vals = await pipe.execute()
        if int(vals[0]) >= MAX_ATTEMPTS:
            await redis_client.set(lock_key, "1", ex=LOCKOUT_SECONDS)
        return
    async with LOGIN_LOCK:
        LOGIN_GLOBAL_EVENTS.append(time.time())
        rec = LOGIN_ATTEMPTS.setdefault(ip, {"count": 0, "locked_until": 0})
        rec["count"] += 1
        if rec["count"] >= MAX_ATTEMPTS:
            rec["locked_until"] = time.time() + LOCKOUT_SECONDS
            rec["count"] = 0

async def record_login_success(ip: str):
    if redis_client is not None:
        key = hashlib.sha256(ip.encode()).hexdigest()
        await redis_client.delete(f"vortex:login:fail:{key}", f"vortex:login:lock:{key}")
        return
    async with LOGIN_LOCK:
        LOGIN_ATTEMPTS.pop(ip, None)

def _trusted_proxy_networks() -> list[ipaddress._BaseNetwork]:
    networks = []
    for raw in CONFIG["trusted_proxy_cidrs"]:
        try:
            networks.append(ipaddress.ip_network(raw, strict=False))
        except ValueError:
            logger.warning("Ignoring invalid TRUSTED_PROXY_CIDRS entry: %s", raw)
    return networks


TRUSTED_PROXY_NETWORKS = _trusted_proxy_networks()


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    if not CONFIG["trust_proxy"] or not TRUSTED_PROXY_NETWORKS:
        return peer
    try:
        peer_ip = ipaddress.ip_address(peer)
    except ValueError:
        return peer
    if not any(peer_ip in net for net in TRUSTED_PROXY_NETWORKS):
        return peer
    values = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    values.append(peer)
    for value in reversed(values):
        try:
            ip = ipaddress.ip_address(value)
        except ValueError:
            continue
        if not any(ip in net for net in TRUSTED_PROXY_NETWORKS):
            return str(ip)
    return peer


async def create_session() -> str:
    token = secrets.token_urlsafe(32)
    expires = int(SESSION_TTL)
    if redis_client is not None:
        await redis_client.setex(f"vortex:session:{token}", expires, "1")
    else:
        async with SESSIONS_LOCK:
            SESSIONS[token] = time.time() + SESSION_TTL
    return token

async def is_valid_session(token: str | None) -> bool:
    if not token:
        return False
    if redis_client is not None:
        return bool(await redis_client.exists(f"vortex:session:{token}"))
    async with SESSIONS_LOCK:
        exp = SESSIONS.get(token)
        if exp is None:
            return False
        if exp < time.time():
            SESSIONS.pop(token, None)
            return False
        return True

async def destroy_session(token: str | None):
    if not token:
        return
    if redis_client is not None:
        await redis_client.delete(f"vortex:session:{token}")
        return
    async with SESSIONS_LOCK:
        SESSIONS.pop(token, None)

async def require_auth(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not await is_valid_session(token):
        raise HTTPException(status_code=401, detail="unauthorized")
    return token


def csrf_token_for_session(session_token: str) -> str:
    # به‌جای نگه‌داشتن یک جدول جدای CSRF token، مقدار آن را قطعی (deterministic)
    # از خودِ session token با HMAC می‌سازیم — یعنی نیازی به state اضافه نیست
    # و با هر ری‌استارت سرویس (که INSTANCE_SECRET عوض می‌شود و سشن‌های قدیمی
    # هم چون در حافظه بودند از بین رفته‌اند) به‌طور خودکار sync می‌ماند.
    return hmac.new(CSRF_SECRET, f"csrf:{session_token}".encode(), hashlib.sha256).hexdigest()


async def require_auth_csrf(request: Request):
    """مثل require_auth، به‌علاوه‌ی بررسی CSRF token برای متدهای تغییردهنده‌ی
    وضعیت (POST/PUT/PATCH/DELETE).

    چون کوکی سشن httponly است و کوکی CSRF نیست، فقط جاوااسکریپتِ همان
    origin می‌تواند مقدار کوکی CSRF را بخواند و به‌عنوان هدر بفرستد — یک
    سایتِ ثالث که کاربر لاگین‌شده را به این پنل هدایت می‌کند (CSRF کلاسیک)
    نمی‌تواند این هدر را بسازد، چون به کوکی CSRF (که SameSite هم هست)
    دسترسی ندارد. این یک لایه‌ی دفاعی اضافه روی SameSite=Lax است، نه
    جایگزین آن.
    """
    token = request.cookies.get(SESSION_COOKIE)
    if not await is_valid_session(token):
        raise HTTPException(status_code=401, detail="unauthorized")
    expected = csrf_token_for_session(token)
    provided = request.headers.get(CSRF_HEADER, "")
    if not provided or not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
    return token



def _db_integrity_check_sync():
    conn = _db_connect()
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        if not row or row[0] != "ok":
            raise RuntimeError(f"sqlite integrity check failed: {row}")
    finally:
        conn.close()

# ───────────────────────── Startup / shutdown ─────────────────────────

_cleanup_task: asyncio.Task | None = None


async def _periodic_cleanup():
    """سشن‌های منقضی‌شده و رکوردهای قفلِ لغوشده‌ی ورود را هر چند دقیقه پاک می‌کند.

    قبلاً این‌ها فقط هنگام دسترسی مجدد (lazy) پاک می‌شدند؛ توکن‌هایی که هیچ‌وقت
    دوباره استفاده نمی‌شوند برای همیشه در حافظه می‌ماندند و در یک دیپلوی
    طولانی‌مدت رشد می‌کردند.
    """
    while True:
        try:
            await asyncio.sleep(600)
            now = time.time()
            async with SESSIONS_LOCK:
                expired = [t for t, exp in SESSIONS.items() if exp < now]
                for t in expired:
                    SESSIONS.pop(t, None)
            async with LOGIN_LOCK:
                stale = [
                    ip for ip, rec in LOGIN_ATTEMPTS.items()
                    if rec["locked_until"] < now and rec["count"] == 0
                ]
                for ip in stale:
                    LOGIN_ATTEMPTS.pop(ip, None)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("periodic cleanup error: %s", exc)


from contextlib import asynccontextmanager

def validate_runtime_config() -> None:
    positive_limits = (
        "max_ws_initial_bytes", "max_connections_per_ip",
        "max_connections_global", "max_http_body_bytes", "max_login_body_bytes",
        "proxy_max_response_bytes", "proxy_max_url_length",
    )
    for key in positive_limits:
        if CONFIG[key] <= 0:
            raise RuntimeError(f"invalid configuration: {key} must be > 0")
    if CONFIG["proxy_require_allowlist"] and not CONFIG["proxy_allowlist"]:
        logger.info("HTTP proxy is fail-closed: PROXY_ALLOWED_DOMAINS is empty")
    if CONFIG["trust_proxy"] and not TRUSTED_PROXY_NETWORKS:
        raise RuntimeError("TRUST_PROXY=1 requires TRUSTED_PROXY_CIDRS")
    if CONFIG["redis_url"] and not CONFIG["session_secret"]:
        raise RuntimeError("REDIS_URL is set: SESSION_SECRET must also be configured for multi-instance CSRF/session consistency")
    if any(port < 1 or port > 65535 for port in CONFIG["tunnel_allowed_ports"]):
        raise RuntimeError("invalid TUNNEL_ALLOWED_PORTS")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global http_client, _cleanup_task, _usage_flush_task, redis_client
    validate_runtime_config()
    _db_init()
    # Fail fast on an unusable persistent volume instead of starting a
    # half-working gateway that silently loses control-plane state.
    storage = await asyncio.to_thread(_storage_status_sync)
    if not storage["writable"]:
        raise RuntimeError(f"database directory is not writable: {storage['db_path']}")
    if (storage.get("railway") and storage.get("persistent_path")
            and CONFIG["require_persistent_volume"] and not storage.get("volume_mounted")):
        raise RuntimeError(
            "Railway persistent storage is required: /data is not mounted as a Volume. "
            "Create/attach a Railway Volume at /data before deploying. "
            "Set REQUIRE_PERSISTENT_VOLUME=0 only if you intentionally accept ephemeral storage."
        )
    if CONFIG["redis_url"]:
        if redis_async is None:
            raise RuntimeError("REDIS_URL is set but redis package is not installed")
        redis_client = redis_async.from_url(CONFIG["redis_url"], decode_responses=True)
        await redis_client.ping()

    link_rows, setting_rows = await _db_load_all()
    async with LINKS_LOCK:
        LINKS.clear()
        SUBSCRIPTION_INDEX.clear()
        for uuid, label, limit_bytes, used_bytes, created_at, active, expires_at, speed_limit_bps, subscription_token, route_via in link_rows:
            token = subscription_token or secrets.token_urlsafe(32)
            LINKS[uuid] = {
                "label": label, "limit_bytes": limit_bytes, "used_bytes": used_bytes,
                "created_at": created_at, "active": bool(active), "expires_at": expires_at,
                "speed_limit_bps": speed_limit_bps or 0,
                "subscription_token": token,
                "route_via": route_via if route_via in ("auto", "railway", "cloudflare") else "auto",
            }
            SUBSCRIPTION_INDEX[token] = uuid
    global ACTIVE_WORKER_URL
    settings_map = dict(setting_rows)
    ACTIVE_WORKER_URL = settings_map.get("cloudflare_worker_url", "") or ""
    await _bootstrap_admin_password(settings_map)

    scheme = "https" if cookie_secure() else "http"
    panel_host = get_host()
    display_host = f"{panel_host}" if cookie_secure() else f"{panel_host}:{CONFIG['port']}"
    panel_url = f"{scheme}://{display_host}/login"
    logger.info("🌀 پنل Vortex در آدرس زیر در دسترس است: %s", panel_url)

    limits = httpx.Limits(max_connections=300, max_keepalive_connections=50)
    timeout = httpx.Timeout(20.0, connect=8.0)
    http_client = httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=False)
    await ensure_default_link()
    _cleanup_task = asyncio.create_task(_periodic_cleanup())
    _usage_flush_task = asyncio.create_task(_periodic_usage_flush())
    global _AUTO_BACKUP_TASK
    if _AUTO_BACKUP_TASK is None or _AUTO_BACKUP_TASK.done():
        _AUTO_BACKUP_TASK = asyncio.create_task(_automatic_sqlite_backup())
    logger.info("🌀 %s v%s started on port %s (%d links)", APP_NAME, APP_VERSION, CONFIG["port"], len(LINKS))
    try:
        yield
    finally:
        await _flush_usage()
        if _cleanup_task:
            _cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await _cleanup_task
        if _usage_flush_task:
            _usage_flush_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await _usage_flush_task
        await _graceful_shutdown()
        if http_client:
            await http_client.aclose()
        if redis_client:
            await redis_client.aclose()

app.router.lifespan_context = lifespan


# ───────────────────────── Helpers ─────────────────────────

def generate_uuid(seed: str | None = None) -> str:
    if seed is None:
        raw = secrets.token_bytes(16).hex()
    else:
        raw = hmac.new(INSTANCE_SECRET, seed.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"


def _link_route_via(uid: str) -> str:
    """کاربر می‌تواند برای هر لینک جداگانه مسیر تولید کانفیگ را انتخاب کند:
    'auto' (پیش‌فرض: اگر Worker فعال باشد از آن استفاده کن، وگرنه مستقیم Railway)،
    'railway' (همیشه مستقیم، حتی اگر Worker فعال باشد) یا
    'cloudflare' (همیشه از Worker؛ اگر Worker هنوز دیپلوی نشده باشد به auto سقوط می‌کند)."""
    value = (LINKS.get(uid, {}).get("route_via") or "auto").strip().lower()
    return value if value in ("auto", "railway", "cloudflare") else "auto"


def generate_vless_link(uid: str, host: str, remark: str = "Vortex") -> str:
    route_via = _link_route_via(uid)
    worker_parts = _worker_endpoint_parts() if route_via != "railway" else None
    if worker_parts:
        endpoint_host, gate_path = worker_parts
        link_host = endpoint_host
        path = f"{gate_path}/tunnel/{uid}"
    else:
        link_host = host
        # Direct Railway VLESS compatibility: use the canonical /ws/{uuid}
        # endpoint used by the known-working reference project.
        # Cloudflare Worker links keep /tunnel/ because the Worker forwards
        # that path explicitly.
        path = f"/ws/{uid}"
    params = {
        "encryption": "none",
        "security": "tls",
        "type": "ws",
        "host": link_host,
        "path": path,
        "sni": link_host,
        "fp": "chrome",
        "alpn": "http/1.1",
    }
    query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    return f"vless://{uid}@{link_host}:443?{query}#{quote(remark)}"


def generate_sub_url(uid: str, host: str) -> str:
    route_via = _link_route_via(uid)
    worker_parts = _worker_endpoint_parts() if route_via != "railway" else None
    if worker_parts:
        endpoint_host, gate_path = worker_parts
        token = LINKS.get(uid, {}).get("subscription_token", uid)
        # Subscription endpoint is deliberately exposed through the Worker so
        # the generated client URL remains usable even when the Railway origin
        # is hidden behind Cloudflare.
        return f"https://{endpoint_host}{gate_path}/sub/{token}"
    base = get_public_origin() if not cookie_secure() else f"https://{get_host()}"
    return f"{base}/sub/{LINKS.get(uid, {}).get('subscription_token', uid)}"

def uptime_str() -> str:
    secs = int(time.time() - stats["start_time"])
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_size_to_bytes(value: float, unit: str) -> int:
    unit = unit.upper()
    mult = {"GB": 1024**3, "MB": 1024**2, "KB": 1024}.get(unit, 1)
    return int(value * mult)


def parse_speed_to_bps(value: float, unit: str) -> int:
    """مقدار محدودیت سرعت (KB/s یا MB/s) را به بایت‌بر ثانیه تبدیل می‌کند."""
    unit = (unit or "").upper()
    mult = {"MBPS": 1024**2, "KBPS": 1024}.get(unit, 1024)
    return max(0, int(value * mult))


def parse_expiry_input(value) -> str | None:
    """ورودی تاریخ انقضا (از input[type=date] مثل '2026-12-31') را به یک
    ISO datetime تبدیل می‌کند که پایان همان روز را نشان می‌دهد، تا کاربر تا
    آخر روزِ انتخاب‌شده بتواند از لینک استفاده کند. اگر خالی/نامعتبر باشد
    None برمی‌گرداند (یعنی بدون انقضا)."""
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        if "T" in value:
            # از قبل یک ISO datetime کامل است (مثلاً از یک بکاپ یا PATCH قبلی)
            datetime.fromisoformat(value)
            return value
        parsed_date = datetime.fromisoformat(value).date()
        return datetime.combine(parsed_date, datetime.max.time().replace(microsecond=0)).isoformat()
    except ValueError:
        return None


def is_link_expired(link: dict) -> bool:
    exp = link.get("expires_at")
    if not exp:
        return False
    try:
        return datetime.fromisoformat(exp) <= datetime.now()
    except ValueError:
        return False


async def ensure_default_link():
    created_uid = None
    async with LINKS_LOCK:
        if not LINKS:
            uid = generate_uuid("default")
            LINKS[uid] = {
                "label": "لینک پیش‌فرض",
                "limit_bytes": 0,
                "used_bytes": 0,
                "created_at": datetime.now().isoformat(),
                "active": True,
                "expires_at": None,
                "speed_limit_bps": 0,
                "subscription_token": secrets.token_urlsafe(32),
                "route_via": "auto",
            }
            created_uid = uid
    if created_uid:
        await _db_upsert_link(created_uid, LINKS[created_uid])


# ───────────────────────── SSRF protection ─────────────────────────

def _is_blocked_single(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True

    if isinstance(ip, ipaddress.IPv6Address):
        # نکته‌ی مهم (که با تست واحد پیدا شد): کتابخانه‌ی ipaddress پایتون
        # کل بلوک ::ffff:0:0/96 (IPv4-mapped) را طبق ثبت IANA به‌عنوان
        # «is_reserved=True» علامت می‌زند — چه IPv4 تعبیه‌شده در آن خصوصی
        # باشد چه کاملاً عمومی (مثلاً ::ffff:8.8.8.8). یعنی اگر این‌جا
        # اول چک عمومی روی خودِ پوسته‌ی IPv6 را انجام می‌دادیم (مثل قبل)،
        # همه‌ی آدرس‌های IPv4-mapped همیشه مسدود می‌شدند حتی وقتی مقصد
        # واقعاً عمومی و مجاز بود. برای این‌ها باید صرفاً بر اساس IPv4
        # واقعیِ تعبیه‌شده تصمیم گرفت، نه پرچم‌های خودِ پوسته‌ی IPv6.
        mapped = ip.ipv4_mapped
        if mapped is not None:
            return _is_blocked_single(mapped)
        # آدرس‌های 6to4 (2002::/16) و Teredo (2001::/32) پرچم is_reserved
        # ندارند، پس چک عمومیِ پایین (روی خودِ پوسته) به‌تنهایی برایشان کافی
        # نیست چون IPv4 تعبیه‌شده در آن‌ها می‌تواند داخلی باشد بدون این‌که
        # خودِ پوسته‌ی IPv6 private/reserved تشخیص داده شود.
        embedded = getattr(ip, "sixtofour", None) or getattr(ip, "teredo", None)
        if embedded is not None:
            candidates = embedded if isinstance(embedded, tuple) else (embedded,)
            for c in candidates:
                if isinstance(c, ipaddress.IPv4Address) and _is_blocked_single(c):
                    return True

    return _is_blocked_single(ip)


def _alt_ip_literal(hostname: str) -> str | None:
    """تشخیص می‌دهد آیا hostname یک نمایش جایگزین (غیرمتعارف) از یک آدرس IPv4 است،
    مثل عدد اعشاری تک‌رقمی (2130706433)، هگزادسیمال (0x7f000001)، اوکتال
    (0177.0.0.1) یا فرم کوتاه (127.1). این فرم‌ها توسط ipaddress.ip_address
    استاندارد رد می‌شوند اما بسیاری از resolver ها/کتابخانه‌های شبکه (از جمله
    inet_aton در سطح سیستم‌عامل) آن‌ها را به‌عنوان IP معتبر می‌پذیرند — پس اگر
    این بررسی را نکنیم، مهاجم می‌تواند با یکی از این فرم‌ها فیلتر hostname را
    دور بزند و در عین حال به یک IP داخلی متصل شود.
    """
    try:
        ipaddress.ip_address(hostname)
        return None  # فرم استاندارد است؛ مسیر عادی resolve آن را می‌گیرد
    except ValueError:
        pass
    try:
        return socket.inet_ntoa(socket.inet_aton(hostname))
    except OSError:
        return None


async def resolve_safe_ips(hostname: str) -> list[str]:
    """Resolve a destination and keep every publicly routable address.

    The previous VLESS path selected the first acceptable DNS answer. On hosts
    with mixed IPv4/IPv6 (or otherwise flaky) egress, that single choice could
    be unreachable even though another public address worked. The reference
    RVG project lets asyncio.open_connection() choose/fallback itself; this
    version preserves SSRF protection while trying every safe address.
    """
    alt = _alt_ip_literal(hostname)
    if alt is not None:
        return [] if is_blocked_ip(alt) else [alt]

    try:
        infos = await asyncio.get_event_loop().getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return []

    result: list[str] = []
    seen: set[str] = set()
    for info in infos:
        ip = info[4][0]
        if ip in seen or is_blocked_ip(ip):
            continue
        seen.add(ip)
        result.append(ip)
    return result


async def resolve_safe_ip(hostname: str) -> str | None:
    """اگر hostname به یک IP عمومی/امن resolve شود آن IP را برمی‌گرداند، وگرنه None.

    به‌جای این‌که فقط نتیجه‌ی بولی برگردانیم و بعداً اجازه دهیم httpx دوباره
    hostname را resolve کند (که باز‌ی برای DNS rebinding باز می‌گذارد)،
    همان IP بررسی‌شده را برمی‌گردانیم تا request واقعی مستقیماً به همان IP برود.
    """
    alt = _alt_ip_literal(hostname)
    if alt is not None:
        return None if is_blocked_ip(alt) else alt

    try:
        infos = await asyncio.get_event_loop().getaddrinfo(hostname, None)
    except socket.gaierror:
        return None
    for info in infos:
        ip = info[4][0]
        if not is_blocked_ip(ip):
            return ip
    return None


async def is_proxy_target_allowed(target_url: str) -> tuple[bool, str, str | None]:
    parsed = urlparse(target_url)
    if parsed.scheme not in ("http", "https"):
        return False, "scheme not allowed", None
    hostname = parsed.hostname
    if not hostname:
        return False, "invalid host", None
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if CONFIG["proxy_allowed_ports"] and port not in CONFIG["proxy_allowed_ports"]:
        return False, "destination port not allowed", None
    host_l = hostname.lower().rstrip(".")
    if CONFIG["proxy_require_allowlist"] and not CONFIG["proxy_allowlist"]:
        return False, "proxy allowlist is not configured", None
    if CONFIG["proxy_allowlist"]:
        allowed = any(
            host_l == d or (d.startswith("*.") and host_l.endswith(d[1:]) and host_l != d[2:])
            for d in CONFIG["proxy_allowlist"]
        )
        if not allowed:
            return False, "domain not in allowlist", None
    safe_ip = await resolve_safe_ip(hostname)
    if safe_ip is None:
        return False, "target resolves to a private/internal address", None
    return True, "", safe_ip


# ───────────────────────── Basic endpoints ─────────────────────────

@app.get("/")
async def root():
    return {"service": APP_NAME, "version": APP_VERSION, "status": "active", "host": get_host()}


@app.get("/health")
async def health():
    return {"status": "ok", "connections": len(connections), "uptime": uptime_str(), "version": APP_VERSION}


@app.get("/health/live")
async def health_live():
    # Liveness never touches external dependencies; a temporary DB/Redis
    # outage must not make the process look dead to the orchestrator.
    return {"status": "alive", "version": APP_VERSION}


@app.get("/health/ready")
async def health_ready():
    if http_client is None:
        raise HTTPException(status_code=503, detail="service not ready")
    try:
        await asyncio.to_thread(_db_integrity_check_sync)
    except Exception:
        raise HTTPException(status_code=503, detail="database not ready")
    if CONFIG["redis_url"]:
        if redis_client is None:
            raise HTTPException(status_code=503, detail="redis not ready")
        try:
            await redis_client.ping()
        except Exception:
            raise HTTPException(status_code=503, detail="redis not ready")
    return {"status": "ready", "version": APP_VERSION}


# ───────────────────────── Auth endpoints ─────────────────────────

class LoginRequest(BaseModel):
    password: str = Field(default="", max_length=1024)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(default="", max_length=1024)
    new_password: str = Field(default="", min_length=4, max_length=1024)


class SetupPasswordRequest(BaseModel):
    password: str = Field(default="", min_length=4, max_length=1024)
    password_confirm: str = Field(default="", min_length=4, max_length=1024)


def _password_strength_error(password: str) -> str | None:
    if len(password) < 4:
        return "رمز عبور باید حداقل ۴ کاراکتر باشد"
    if len(password.encode("utf-8")) > 4096:
        return "رمز عبور بیش از حد طولانی است"
    return None


@app.get("/api/setup-status")
async def api_setup_status():
    return {"setup_required": bool(AUTH["setup_required"])}


@app.post("/api/setup-password")
async def api_setup_password(payload: SetupPasswordRequest, request: Request):
    if not AUTH["setup_required"] or AUTH["password_hash"]:
        raise HTTPException(status_code=409, detail="راه‌اندازی قبلاً انجام شده است")
    ip = client_ip(request)
    allowed, wait = await check_login_allowed(ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"تعداد تلاش‌ها زیاد بود. {wait} ثانیه دیگر دوباره تلاش کنید")
    if payload.password != payload.password_confirm:
        await record_login_failure(ip)
        raise HTTPException(status_code=400, detail="تکرار رمز عبور یکسان نیست")
    err = _password_strength_error(payload.password)
    if err:
        await record_login_failure(ip)
        raise HTTPException(status_code=400, detail=err)
    new_hash = hash_password(payload.password)
    # Persist first, then change in-memory state. This prevents a partial
    # setup if the database write fails.
    await _db_set_setting("password_hash", new_hash)
    AUTH["password_hash"] = new_hash
    AUTH["setup_required"] = False
    await record_login_success(ip)
    logger.info("🔐 AUDIT initial admin password configured ip=%s", ip)
    asyncio.create_task(audit("initial_password_configured", ip))
    token = await create_session()
    resp = JSONResponse({"ok": True, "setup_required": False})
    resp.set_cookie(key=SESSION_COOKIE, value=token, max_age=SESSION_TTL, httponly=True, samesite="lax", secure=cookie_secure(), path="/")
    resp.set_cookie(key=CSRF_COOKIE, value=csrf_token_for_session(token), max_age=SESSION_TTL, httponly=False, samesite="lax", secure=cookie_secure(), path="/")
    return resp


@app.post("/api/login")
async def api_login(payload: LoginRequest, request: Request):
    if AUTH["setup_required"] or not AUTH["password_hash"]:
        raise HTTPException(status_code=428, detail="ابتدا رمز عبور پنل را تعیین کنید")
    ip = client_ip(request)
    allowed, wait = await check_login_allowed(ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"تعداد تلاش‌های ناموفق زیاد بود. {wait} ثانیه دیگر دوباره تلاش کنید")

    password = payload.password
    if not verify_password(password, AUTH["password_hash"]):
        await record_login_failure(ip)
        logger.warning("🔒 AUDIT login failed ip=%s", ip)
        asyncio.create_task(audit("login_failed", ip, "invalid password"))
        raise HTTPException(status_code=401, detail="رمز عبور اشتباه است")

    # Transparently upgrade legacy PBKDF2 hashes after a successful login.
    if password_needs_rehash(AUTH["password_hash"]):
        AUTH["password_hash"] = hash_password(password)
        await _db_set_setting("password_hash", AUTH["password_hash"])
    await record_login_success(ip)
    token = await create_session()
    logger.info("🔑 AUDIT login success ip=%s", ip)
    asyncio.create_task(audit("login_success", ip))
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        key=SESSION_COOKIE, value=token, max_age=SESSION_TTL,
        httponly=True, samesite="lax", secure=cookie_secure(), path="/",
    )
    # کوکی CSRF عمداً httponly نیست: جاوااسکریپت پنل باید بتواند مقدارش را
    # بخواند و به‌عنوان هدر X-CSRF-Token در درخواست‌های تغییردهنده بفرستد.
    resp.set_cookie(
        key=CSRF_COOKIE, value=csrf_token_for_session(token), max_age=SESSION_TTL,
        httponly=False, samesite="lax", secure=cookie_secure(), path="/",
    )
    return resp


@app.post("/api/logout")
async def api_logout(request: Request, _=Depends(require_auth_csrf)):
    token = request.cookies.get(SESSION_COOKIE)
    await destroy_session(token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    resp.delete_cookie(CSRF_COOKIE, path="/")
    return resp


@app.get("/api/me")
async def api_me(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    return {"authenticated": await is_valid_session(token)}


def _storage_status_sync() -> dict:
    db_path = os.path.abspath(DB_PATH)
    db_dir = os.path.dirname(db_path) or os.getcwd()
    data_root = os.path.abspath("/data")
    persistent = db_path == data_root or db_path.startswith(data_root + os.sep)
    mounted = os.path.ismount(data_root) if os.path.isdir(data_root) else False
    railway = bool(os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_PROJECT_ID"))
    writable = os.access(db_dir, os.W_OK)
    return {
        "db_path": db_path,
        "persistent_path": persistent,
        "volume_mounted": mounted,
        "writable": writable,
        "railway": railway,
        "railway_volume_required": bool(railway and CONFIG["require_persistent_volume"] and persistent),
        "railway_volume_recommended": bool(railway and not mounted),
    }


def _system_status_sync() -> dict:
    db_path = os.path.abspath(DB_PATH)
    db_dir = os.path.dirname(db_path) or os.getcwd()
    try:
        usage = os.statvfs(db_dir)
        disk_total = usage.f_blocks * usage.f_frsize
        disk_free = usage.f_bavail * usage.f_frsize
    except OSError:
        disk_total = disk_free = 0

    db_ok = False
    db_error = None
    try:
        conn = _db_connect()
        row = conn.execute("PRAGMA integrity_check").fetchone()
        db_ok = bool(row and row[0] == "ok")
        conn.close()
    except Exception as exc:
        db_error = str(exc)[:200]

    persistent = db_path == "/data" or db_path.startswith("/data" + os.sep)
    return {
        "version": APP_VERSION,
        "python": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}.{__import__('sys').version_info.micro}",
        "platform": os.environ.get("RAILWAY_ENVIRONMENT_NAME", "standalone"),
        "railway": bool(os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_PROJECT_ID")),
        "database": {
            "ok": db_ok, "path": db_path, "persistent": persistent,
            "writable": os.access(db_dir, os.W_OK), "error": db_error,
        },
        "redis": {"configured": bool(CONFIG["redis_url"]), "connected": bool(redis_client is not None)},
        "cloudflare": {"configured": bool(ACTIVE_WORKER_URL.strip())},
        "backup": {"encryption_configured": bool(CONFIG["backup_encryption_key"]), "plaintext_allowed": CONFIG["allow_plaintext_backup"]},
        "telegram": {"configured": bool(CONFIG["telegram_bot_token"] and CONFIG["telegram_chat_id"])},
        "disk": {"total_bytes": disk_total, "free_bytes": disk_free, "free_percent": round((disk_free / disk_total) * 100, 1) if disk_total else None},
        "connections": len(connections),
        "links": len(LINKS),
        "uptime": uptime_str(),
    }


@app.get("/api/system/status")
async def api_system_status(_=Depends(require_auth)):
    return await asyncio.to_thread(_system_status_sync)


@app.post("/api/system/storage-test")
async def api_storage_test(request: Request, _=Depends(require_auth_csrf)):
    storage_test = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)) or os.getcwd(), ".vortex-write-test")
    def _write_test():
        with open(storage_test, "w", encoding="utf-8") as fh:
            fh.write(datetime.now().isoformat())
    try:
        await asyncio.to_thread(_write_test)
        await asyncio.to_thread(os.remove, storage_test)
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"ذخیره‌سازی قابل نوشتن نیست: {exc}")
    await audit("storage_test", client_ip(request), "storage write test passed")
    return {"ok": True}


@app.get("/api/setup/status")
async def api_setup_wizard_status(request: Request, _=Depends(require_auth)):
    async with DB_LOCK:
        settings_rows = await asyncio.to_thread(_db_get_settings_sync)
    settings_map = dict(settings_rows)
    storage = await asyncio.to_thread(_storage_status_sync)
    return {
        "setup_completed": settings_map.get("setup_completed") == "1",
        "storage": storage,
        "railway": bool(os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_PROJECT_ID")),
        "version": APP_VERSION,
    }


@app.post("/api/setup/complete")
async def api_setup_complete(request: Request, _=Depends(require_auth_csrf)):
    await _db_set_setting("setup_completed", "1")
    await audit("setup_completed", client_ip(request), "first-run setup completed")
    return {"ok": True}


@app.post("/api/change-password")
async def api_change_password(payload: ChangePasswordRequest, request: Request, _=Depends(require_auth_csrf)):
    current = payload.current_password
    new = payload.new_password
    if not verify_password(current, AUTH["password_hash"]):
        raise HTTPException(status_code=400, detail="رمز فعلی اشتباه است")
    strength_error = _password_strength_error(new)
    if strength_error:
        raise HTTPException(status_code=400, detail=strength_error)
    AUTH["password_hash"] = hash_password(new)
    await _db_set_setting("password_hash", AUTH["password_hash"])
    current_token = request.cookies.get(SESSION_COOKIE)
    if redis_client is not None:
        keys = []
        async for key in redis_client.scan_iter(match="vortex:session:*", count=100):
            keys.append(key)
        if keys:
            await redis_client.delete(*keys)
        if current_token:
            await redis_client.setex(f"vortex:session:{current_token}", SESSION_TTL, "1")
    else:
        async with SESSIONS_LOCK:
            SESSIONS.clear()
            if current_token:
                SESSIONS[current_token] = time.time() + SESSION_TTL
    logger.info("🔑 AUDIT password changed ip=%s", client_ip(request))
    return {"ok": True}


# ───────────────────────── Cloudflare Worker relay ─────────────────────────
# یک Worker رایگان روی کلادفلر می‌سازیم که فقط ترافیک را (بعد از چک یک مسیرِ
# مخفیِ تصادفی) به همین گیت‌وی روی Railway پاس می‌دهد؛ منطق VLESS/احراز هویت
# همچنان همین‌جا روی سرور اجرا می‌شود — Worker صرفاً یک رله‌ی شفاف است.

class CloudflareWorkerRequest(BaseModel):
    api_token: str = Field(default="", min_length=1, max_length=2048)


def _build_cloudflare_worker_script(origin_host: str, gate: str) -> str:
    origin = json.dumps(f"https://{origin_host}")
    gate_prefix = json.dumps(f"/{gate}")
    return f"""const ORIGIN = {origin};
const GATE = {gate_prefix};

export default {{
  async fetch(request) {{
    const incoming = new URL(request.url);
    if (!incoming.pathname.startsWith(GATE + "/")) {{
      return new Response("Not Found", {{ status: 404, headers: {{ "cache-control": "no-store" }} }});
    }}

    const upstreamPath = incoming.pathname.slice(GATE.length) || "/";
    const allowed = upstreamPath.startsWith("/tunnel/")
      || upstreamPath.startsWith("/sub/")
      || upstreamPath === "/health/ready";
    if (!allowed) {{
      return new Response("Not Found", {{ status: 404, headers: {{ "cache-control": "no-store" }} }});
    }}

    const target = new URL(ORIGIN);
    target.pathname = upstreamPath;
    target.search = incoming.search;

    // Use the platform-supported fetch(url, request) proxy form. Cloudflare
    // rewrites the destination hostname for the subrequest and preserves the
    // incoming WebSocket Upgrade without trying to mutate forbidden headers
    // such as Host/Connection.
    return fetch(target.toString(), request);
  }}
}};
"""


def _resolve_public_host(request: Request) -> str:
    """Best-effort public hostname for this gateway.

    Prefers the explicit RAILWAY_PUBLIC_DOMAIN env var when it is actually
    set. If Railway hasn't had that variable added to the service (a common
    setup gap — generating a domain in Settings → Networking does not by
    itself inject it into the container), fall back to the Host header of
    the very request the admin is making right now. Since the admin is
    already logged into the panel through its real public URL, that Host
    header reflects the correct public domain without requiring any manual
    Railway configuration.
    """
    env_host = get_host().strip()
    if env_host and env_host.lower() not in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return env_host

    # Only trust the Host header as a fallback for this admin-only, already
    # authenticated action; it is never used to bypass auth or CSRF.
    header_host = (request.headers.get("host") or "").strip()
    if not header_host:
        return env_host or "localhost"
    parsed = urlparse(header_host if "://" in header_host else f"https://{header_host}")
    candidate = (parsed.hostname or "").strip().rstrip(".")
    if not candidate or candidate.lower() in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return env_host or "localhost"
    # Never point the Worker relay back at a workers.dev address (would create
    # a Worker → Worker loop instead of Worker → Railway origin).
    if candidate.lower().endswith(".workers.dev"):
        return env_host or "localhost"
    return candidate


@app.post("/api/cloudflare/deploy-worker")
async def api_cloudflare_deploy_worker(payload: CloudflareWorkerRequest, request: Request, _=Depends(require_auth_csrf)):
    api_token = payload.api_token.strip()
    if not api_token:
        raise HTTPException(status_code=400, detail="API Token را وارد کن")

    # If RAILWAY_PUBLIC_DOMAIN is missing we no longer fail immediately —
    # _resolve_public_host() below falls back to the current request's Host
    # header, which works automatically for the vast majority of setups.
    early_host = _resolve_public_host(request)
    if early_host.lower() in {"", "localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "آدرس عمومی گیت‌وی قابل تشخیص نیست (نه از RAILWAY_PUBLIC_DOMAIN و نه از هدر درخواست). "
                "مطمئن شو تو Railway، Settings → Networking یک Public Domain ساخته‌ای و از همان آدرس "
                "(نه localhost) وارد پنل شده‌ای، بعد دوباره امتحان کن."
            ),
        )

    headers = {"Authorization": f"Bearer {api_token}"}

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            verify_resp = await client.get("https://api.cloudflare.com/client/v4/user/tokens/verify", headers=headers)
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="اتصال به Cloudflare برقرار نشد")
        try:
            verify_data = verify_resp.json()
        except ValueError:
            verify_data = {}
        if verify_resp.status_code != 200 or not verify_data.get("success"):
            raise HTTPException(status_code=400, detail="توکن Cloudflare معتبر نیست یا منقضی شده")

        try:
            accounts_resp = await client.get(
                "https://api.cloudflare.com/client/v4/accounts",
                headers=headers,
                params={"page": 1, "per_page": 100},
            )
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="اتصال به Cloudflare برقرار نشد")
        try:
            accounts_data = accounts_resp.json()
        except ValueError:
            accounts_data = {}
        if accounts_resp.status_code != 200 or not accounts_data.get("success"):
            raise HTTPException(
                status_code=400,
                detail="خواندن Account از کلادفلر ناموفق بود؛ توکن باید دسترسی Account لازم و Workers Scripts Edit داشته باشد",
            )
        accounts_list = accounts_data.get("result") or []
        account_id = next((item.get("id", "") for item in accounts_list if item.get("id")), "")
        if not account_id:
            raise HTTPException(status_code=400, detail="Account ID قابل تشخیص نبود")

        origin_host = _resolve_public_host(request).strip().rstrip("/")
        parsed_origin = urlparse(origin_host if "://" in origin_host else f"https://{origin_host}")
        if (parsed_origin.hostname or "").lower() in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
            raise HTTPException(
                status_code=400,
                detail="گیت‌وی روی آدرس محلی اجرا می‌شود؛ ابتدا آن را روی یک Origin عمومی مثل Railway دیپلوی کن.",
            )
        if not parsed_origin.hostname:
            raise HTTPException(status_code=400, detail="آدرس عمومی گیت‌وی معتبر نیست")
        origin_host = parsed_origin.hostname

        worker_name = f"vortex-{secrets.token_hex(4)}"
        # Reuse the previously deployed gate path (if any) instead of always
        # generating a brand new one. This is the direct fix for "old
        # sub/tunnel links stop working every time I rebuild the Worker":
        # since the gate segment is embedded in every generated vless:// and
        # /sub/ link, changing it on every redeploy silently invalidates all
        # links already handed out to users. Reusing the same gate means a
        # Worker rebuild (e.g. after a Railway redeploy changed the origin
        # host) keeps existing links working; the gate only changes on the
        # very first deployment.
        async with DB_LOCK:
            existing_settings = await asyncio.to_thread(_db_get_settings_sync)
        gate = (existing_settings.get("cloudflare_worker_gate") or "").strip()
        if not gate or not gate.isalnum() or not (10 <= len(gate) <= 20):
            gate = secrets.token_urlsafe(18).replace("_", "").replace("-", "")[:20]
        script = _build_cloudflare_worker_script(origin_host, gate)
        upload_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{worker_name}"
        metadata = {"main_module": "worker.js", "compatibility_date": "2024-09-23"}
        files = {
            "metadata": (None, json.dumps(metadata), "application/json"),
            "worker.js": ("worker.js", script, "application/javascript+module"),
        }
        try:
            upload_resp = await client.put(upload_url, headers=headers, files=files)
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="آپلود Worker به Cloudflare ناموفق بود")
        try:
            upload_data = upload_resp.json()
        except ValueError:
            upload_data = {}
        if upload_resp.status_code not in (200, 201) or not upload_data.get("success"):
            errs = upload_data.get("errors") or []
            msg = errs[0].get("message") if errs else "ساخت Worker ناموفق بود"
            raise HTTPException(status_code=400, detail=f"خطای Cloudflare: {msg}")

        subdomain_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{worker_name}/subdomain"
        try:
            enable_resp = await client.post(
                subdomain_url,
                headers={**headers, "Content-Type": "application/json"},
                json={"enabled": True, "previews_enabled": False},
            )
            enable_data = enable_resp.json()
        except (httpx.HTTPError, ValueError):
            enable_resp = None
            enable_data = {}
        if not enable_resp or enable_resp.status_code not in (200, 201) or not enable_data.get("success"):
            # Best-effort cleanup so a failed deployment does not leave an orphan Worker.
            with contextlib.suppress(Exception):
                await client.delete(upload_url, headers=headers)
            errs = (enable_data.get("errors") or []) if isinstance(enable_data, dict) else []
            msg = errs[0].get("message") if errs else "فعال‌سازی workers.dev ناموفق بود"
            raise HTTPException(status_code=400, detail=f"Cloudflare: {msg}")

        try:
            sub_resp = await client.get(subdomain_url, headers=headers)
            sub_data = sub_resp.json()
        except (httpx.HTTPError, ValueError):
            sub_resp = None
            sub_data = {}
        if not sub_resp or sub_resp.status_code != 200 or not sub_data.get("success") or not (sub_data.get("result") or {}).get("enabled"):
            with contextlib.suppress(Exception):
                await client.delete(upload_url, headers=headers)
            raise HTTPException(status_code=400, detail="workers.dev برای این Worker فعال نشد")

        # The account-level workers.dev subdomain is required to construct the
        # public URL. If the account has not created one yet, create it
        # automatically (Cloudflare exposes this as a separate account action).
        account_subdomain_endpoint = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/subdomain"
        try:
            account_subdomain_resp = await client.get(account_subdomain_endpoint, headers=headers)
            account_subdomain_data = account_subdomain_resp.json()
        except (httpx.HTTPError, ValueError):
            account_subdomain_resp = None
            account_subdomain_data = {}
        subdomain = (account_subdomain_data.get("result") or {}).get("subdomain", "")

        if not subdomain:
            # Some accounts do not have a workers.dev subdomain until the first
            # worker deployment. Ask Cloudflare to create the account subdomain
            # instead of failing after successfully uploading the Worker.
            try:
                create_subdomain_resp = await client.put(
                    account_subdomain_endpoint,
                    headers={**headers, "Content-Type": "application/json"},
                    json={"subdomain": worker_name},
                )
                create_subdomain_data = create_subdomain_resp.json()
            except (httpx.HTTPError, ValueError):
                create_subdomain_resp = None
                create_subdomain_data = {}
            if not create_subdomain_resp or create_subdomain_resp.status_code not in (200, 201) or not create_subdomain_data.get("success"):
                with contextlib.suppress(Exception):
                    await client.delete(upload_url, headers=headers)
                errs = create_subdomain_data.get("errors") or [] if isinstance(create_subdomain_data, dict) else []
                msg = errs[0].get("message") if errs else "ساخت workers.dev subdomain ناموفق بود"
                raise HTTPException(status_code=400, detail=f"Cloudflare: {msg}")
            subdomain = (create_subdomain_data.get("result") or {}).get("subdomain", "")

        if not subdomain:
            with contextlib.suppress(Exception):
                await client.delete(upload_url, headers=headers)
            raise HTTPException(status_code=400, detail="Account workers.dev subdomain قابل دریافت نیست")

        worker_url = f"https://{worker_name}.{subdomain}.workers.dev/{gate}"

        # Verify the actual deployed relay before writing anything to SQLite.
        health_url = f"{worker_url}/health/ready"
        last_status = None
        for _attempt in range(3):
            try:
                health_resp = await client.get(health_url, headers={"Cache-Control": "no-cache"})
                last_status = health_resp.status_code
                if health_resp.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            await asyncio.sleep(1.0)
        else:
            with contextlib.suppress(Exception):
                await client.delete(upload_url, headers=headers)
            raise HTTPException(status_code=502, detail=f"Worker ساخته شد اما از بیرون قابل دسترسی نیست (status={last_status})")

    # New Worker is healthy. Retire the previously active Worker to avoid
    # accumulating unused scripts in the account. Failure to delete the old
    # script is non-fatal because the new Worker is already known-good.
    previous_worker_name = ""
    try:
        async with DB_LOCK:
            settings_snapshot = await asyncio.to_thread(_db_get_settings_sync)
        previous_worker_name = settings_snapshot.get("cloudflare_worker_name", "") or ""
    except Exception:
        previous_worker_name = ""
    if previous_worker_name and previous_worker_name != worker_name:
        previous_upload_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{previous_worker_name}"
        try:
            cleanup_resp = await client.delete(previous_upload_url, headers=headers)
            if cleanup_resp.status_code not in (200, 204):
                logger.warning("Cloudflare old Worker cleanup failed name=%s status=%s", previous_worker_name, cleanup_resp.status_code)
        except httpx.HTTPError as exc:
            logger.warning("Cloudflare old Worker cleanup failed name=%s error=%s", previous_worker_name, exc)

    global ACTIVE_WORKER_URL
    ACTIVE_WORKER_URL = worker_url
    await _db_set_setting("cloudflare_worker_name", worker_name)
    await _db_set_setting("cloudflare_worker_url", ACTIVE_WORKER_URL)
    await _db_set_setting("cloudflare_worker_gate", gate)

    logger.info("☁️ AUDIT cloudflare worker deployed name=%s ip=%s", worker_name, client_ip(request))
    return {"ok": True, "worker_name": worker_name, "worker_url": ACTIVE_WORKER_URL, "gate": gate, "gate_reused": bool(existing_settings.get("cloudflare_worker_gate"))}


# ───────────────────────── Stats ─────────────────────────

@app.get("/api/stats")
async def get_stats(_=Depends(require_auth)):
    return {
        "active_connections": len(connections),
        "total_traffic_mb": round(stats["total_bytes"] / (1024 * 1024), 2),
        "total_requests": stats["total_requests"],
        "total_errors": stats["total_errors"],
        "uptime": uptime_str(),
        "timestamp": datetime.now().isoformat(),
        "hourly": dict(hourly_traffic),
        "recent_errors": list(error_logs)[-10:],
        "links_count": len(LINKS),
        "telegram_configured": bool(CONFIG["telegram_bot_token"] and CONFIG["telegram_chat_id"]),
    }


@app.get("/api/audit")
async def list_audit(limit: int = 100, _=Depends(require_auth)):
    limit = max(1, min(limit, 500))
    rows = await asyncio.to_thread(_db_recent_audit_sync, limit)
    return {"events": [{"created_at": r[0], "action": r[1], "ip": r[2], "details": r[3]} for r in rows]}


@app.get("/api/connections")
async def list_connections(_=Depends(require_auth)):
    """اتصالات فعالِ زنده به‌همراه عنوان لینکِ مربوطه، برای نمایش لحظه‌ای در
    صفحه‌ی «اتصالات فعال» داشبورد (قبلاً این صفحه هیچ‌وقت توسط JS پر نمی‌شد)."""
    async with LINKS_LOCK:
        labels = {uid: data["label"] for uid, data in LINKS.items()}
    result = []
    for conn_id, info in connections.items():
        result.append({
            "conn_id": conn_id,
            "uuid": info["uuid"],
            "label": labels.get(info["uuid"], "لینک حذف‌شده"),
            "connected_at": info["connected_at"],
            "bytes": info["bytes"],
        })
    result.sort(key=lambda x: x["connected_at"], reverse=True)
    return {"connections": result}


@app.post("/api/notify/test")
async def send_test_notification(_=Depends(require_auth_csrf)):
    if not (CONFIG["telegram_bot_token"] and CONFIG["telegram_chat_id"]):
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN یا TELEGRAM_CHAT_ID تنظیم نشده است")
    ok = await send_telegram_message("✅ Vortex Gateway: این یک پیام تستی است. اعلان‌ها درست کار می‌کنند.")
    if not ok:
        raise HTTPException(status_code=502, detail="ارسال پیام تلگرام ناموفق بود؛ توکن/chat_id را بررسی کنید")
    return {"ok": True}


# ───────────────────────── Link management ─────────────────────────
# مدل‌های Pydantic ورودی API را قبل از رسیدن به بدنه‌ی هندلر اعتبارسنجی
# می‌کنند (نوع/محدوده‌ی مقادیر)؛ قبلاً با body.get(...) خام پارس می‌شد که
# مثلاً یک مقدار غیرعددی برای limit_value باعث ValueError کنترل‌نشده (خطای
# ۵۰۰ خام) می‌شد. حالا چنین ورودی‌ای همان‌جا با پیام ۴۲۲ واضح رد می‌شود.

SizeUnit = Literal["GB", "MB", "KB"]
SpeedUnit = Literal["KBps", "MBps"]


RouteVia = Literal["auto", "railway", "cloudflare"]


class LinkCreateRequest(BaseModel):
    label: str = "لینک جدید"
    limit_value: float = 0
    limit_unit: SizeUnit = "GB"
    expires_at: str | None = None
    speed_limit_value: float = 0
    speed_limit_unit: SpeedUnit = "KBps"
    route_via: RouteVia = "railway"


class LinkUpdateRequest(BaseModel):
    active: bool | None = None
    limit_value: float | None = None
    limit_unit: SizeUnit = "GB"
    reset_usage: bool | None = None
    label: str | None = None
    expires_at: str | None = None
    speed_limit_value: float | None = None
    speed_limit_unit: SpeedUnit = "KBps"
    route_via: RouteVia | None = None


def _require_finite(value: float, field_name: str) -> float:
    if not math.isfinite(value):
        raise HTTPException(status_code=422, detail=f"{field_name} must be finite")
    return value


SQLITE_INT64_MAX = 9_223_372_036_854_775_807


def _limit_value_to_bytes(value: float, unit: str) -> int:
    """Convert a traffic limit to bytes; non-positive values mean unlimited."""
    value = _require_finite(value, "limit_value")
    if value <= 0:
        return 0
    try:
        result = parse_size_to_bytes(value, unit)
    except (OverflowError, ValueError):
        raise HTTPException(status_code=422, detail="limit_value is too large")
    if result > SQLITE_INT64_MAX:
        raise HTTPException(status_code=422, detail="limit_value is too large")
    return result


def _speed_value_to_bps(value: float, unit: str) -> int:
    """Convert a speed limit to bytes per second; non-positive means unlimited."""
    value = _require_finite(value, "speed_limit_value")
    if value <= 0:
        return 0
    try:
        result = parse_speed_to_bps(value, unit)
    except (OverflowError, ValueError):
        raise HTTPException(status_code=422, detail="speed_limit_value is too large")
    if result > SQLITE_INT64_MAX:
        raise HTTPException(status_code=422, detail="speed_limit_value is too large")
    return result


@app.post("/api/links")
async def create_link(payload: LinkCreateRequest, request: Request, _=Depends(require_auth_csrf)):
    label = payload.label.strip()[:60] or "لینک جدید"
    limit_bytes = _limit_value_to_bytes(payload.limit_value, payload.limit_unit)
    expires_at = parse_expiry_input(payload.expires_at)
    if payload.expires_at and expires_at is None:
        raise HTTPException(status_code=422, detail="invalid expires_at")
    speed_limit_bps = _speed_value_to_bps(payload.speed_limit_value, payload.speed_limit_unit)
    uid = generate_uuid()
    snapshot = {
        "label": label,
        "limit_bytes": limit_bytes,
        "used_bytes": 0,
        "created_at": datetime.now().isoformat(),
        "active": True,
        "expires_at": expires_at,
        "speed_limit_bps": speed_limit_bps,
        "subscription_token": secrets.token_urlsafe(32),
        "route_via": payload.route_via,
    }
    async with LINKS_LOCK:
        # Persist first.  If SQLite rejects the write, no partially-created link
        # remains visible in memory.
        await _db_upsert_link(uid, snapshot)
        LINKS[uid] = dict(snapshot)
        SUBSCRIPTION_INDEX[snapshot["subscription_token"]] = uid
    logger.info("🔗 AUDIT link created uid=%s label=%r ip=%s", uid[:8], label, client_ip(request))
    asyncio.create_task(audit("link_created", client_ip(request), f"uid={uid} label={label}"))
    host = get_host()
    return {
        "uuid": uid,
        "label": label,
        "limit_bytes": limit_bytes,
        "used_bytes": 0,
        "active": True,
        "created_at": snapshot["created_at"],
        "expires_at": expires_at,
        "speed_limit_bps": speed_limit_bps,
        "route_via": payload.route_via,
        "vless_link": generate_vless_link(uid, host, remark=f"Vortex-{label}"),
        "sub_link": generate_sub_url(uid, host),
    }


@app.get("/api/links")
async def list_links(_=Depends(require_auth)):
    host = get_host()
    result = []
    async with LINKS_LOCK:
        for uid, data in LINKS.items():
            result.append({
                "uuid": uid,
                "label": data["label"],
                "limit_bytes": data["limit_bytes"],
                "used_bytes": data["used_bytes"],
                "active": data["active"],
                "created_at": data["created_at"],
                "expires_at": data.get("expires_at"),
                "speed_limit_bps": data.get("speed_limit_bps", 0),
                "expired": is_link_expired(data),
                "route_via": data.get("route_via") or "railway",
                "vless_link": generate_vless_link(uid, host, remark=f"Vortex-{data['label']}"),
                "sub_link": generate_sub_url(uid, host),
            })
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return {"links": result}


@app.get("/api/links/{uid}/traffic")
async def get_link_traffic(uid: str, _=Depends(require_auth)):
    async with LINKS_LOCK:
        if uid not in LINKS:
            raise HTTPException(status_code=404, detail="link not found")
    return {"hourly": dict(link_hourly_traffic.get(uid, {}))}


@app.patch("/api/links/{uid}")
async def update_link(uid: str, payload: LinkUpdateRequest, request: Request, _=Depends(require_auth_csrf)):
    provided = await request.json()
    async with LINKS_LOCK:
        current = LINKS.get(uid)
        if current is None:
            raise HTTPException(status_code=404, detail="link not found")
        updated = dict(current)
        if payload.active is not None:
            updated["active"] = payload.active
        if "limit_value" in provided:
            updated["limit_bytes"] = _limit_value_to_bytes(payload.limit_value if payload.limit_value is not None else 0, payload.limit_unit)
            _notified_pct.pop(uid, None)
        if payload.reset_usage:
            updated["used_bytes"] = 0
            _notified_pct.pop(uid, None)
        if payload.label is not None:
            updated["label"] = payload.label.strip()[:60] or "لینک جدید"
        if "expires_at" in provided:
            raw_expiry = payload.expires_at
            if raw_expiry:
                parsed_expiry = parse_expiry_input(raw_expiry)
                if parsed_expiry is None:
                    raise HTTPException(status_code=422, detail="invalid expires_at")
                updated["expires_at"] = parsed_expiry
            else:
                updated["expires_at"] = None
        if "speed_limit_value" in provided:
            updated["speed_limit_bps"] = _speed_value_to_bps(payload.speed_limit_value if payload.speed_limit_value is not None else 0, payload.speed_limit_unit)
        if payload.route_via is not None:
            updated["route_via"] = payload.route_via
        await _db_upsert_link(uid, updated)
        LINKS[uid] = updated
    logger.info("✏️  AUDIT link updated uid=%s fields=%s ip=%s", uid[:8], list(provided.keys()), client_ip(request))
    asyncio.create_task(audit("link_updated", client_ip(request), f"uid={uid} fields={list(provided.keys())}"))
    return {"ok": True}


@app.delete("/api/links/{uid}")
async def delete_link(uid: str, request: Request, _=Depends(require_auth_csrf)):
    async with LINKS_LOCK:
        removed = LINKS.get(uid)
        if removed is None:
            raise HTTPException(status_code=404, detail="link not found")
        await _db_delete_link(uid)
        LINKS.pop(uid, None)
        token = removed.get("subscription_token")
        if token:
            SUBSCRIPTION_INDEX.pop(token, None)
        _dirty_usage_uids.discard(uid)
    _notified_pct.pop(uid, None)
    link_hourly_traffic.pop(uid, None)
    logger.info("🗑️ AUDIT link deleted uid=%s ip=%s", uid[:8], client_ip(request))
    asyncio.create_task(audit("link_deleted", client_ip(request), f"uid={uid}"))
    return {"ok": True}


# ───────────────────────── Backup / Restore (manual) ─────────────────────────
# مکمل پرسیستنسِ خودکار SQLite: یک فایل JSON قابل‌دانلود که می‌توانید جدا از
# سرور نگه دارید (مثلاً قبل از یک تغییر بزرگ، یا برای انتقال به یک دیپلوی
# دیگر). شامل هش رمز عبور هم هست تا بازیابی، وضعیت را کامل برگرداند —
# پس با فایل بکاپ مثل یک رمز عبور رفتار کنید و آن را جای امنی نگه دارید.

BACKUP_VERSION = 3
ENCRYPTED_BACKUP_PREFIX = b"VORTEX-ENCRYPTED-BACKUP-V1\\n"

def _backup_cipher() -> Fernet:
    key = CONFIG["backup_encryption_key"]
    if not key:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY is required for encrypted backups")
    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY is not a valid Fernet key") from exc

def _encrypt_backup(payload: dict) -> bytes:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    return ENCRYPTED_BACKUP_PREFIX + _backup_cipher().encrypt(raw)

def _decrypt_backup(raw: bytes) -> dict:
    if not raw.startswith(ENCRYPTED_BACKUP_PREFIX):
        if not CONFIG["allow_plaintext_backup"]:
            raise HTTPException(status_code=400, detail="plain backup disabled; use an encrypted backup")
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="invalid backup JSON")
    try:
        decoded = _backup_cipher().decrypt(raw[len(ENCRYPTED_BACKUP_PREFIX):])
        return json.loads(decoded)
    except (InvalidToken, ValueError, TypeError, RuntimeError):
        raise HTTPException(status_code=400, detail="backup decryption failed")

@app.get("/api/backup")
async def export_backup(_=Depends(require_auth)):
    async with LINKS_LOCK:
        links_snapshot = {uid: dict(data) for uid, data in LINKS.items()}
    backup = {
        "version": BACKUP_VERSION,
        "app": APP_NAME,
        "exported_at": datetime.now().isoformat(),
        "password_hash": AUTH["password_hash"],
        "links": links_snapshot,
    }
    if not CONFIG["backup_encryption_key"]:
        raise HTTPException(status_code=503, detail="encrypted backups are not configured")
    content = _encrypt_backup(backup)
    filename = f"vortex-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.vortex"
    return Response(content=content, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})

def _validate_password_hash_format(value) -> bool:
    if not isinstance(value, str) or len(value) > 512:
        return False
    if value.startswith("$argon2id$"):
        try:
            PASSWORD_HASHER.check_needs_rehash(value)
            # Parse/validate the encoded parameters without verifying a password.
            from argon2 import extract_parameters
            extract_parameters(value)
            return True
        except Exception:
            return False
    if "$" not in value:
        return False
    salt_hex, _, hash_hex = value.partition("$")
    if len(salt_hex) != 32 or len(hash_hex) != 64:
        return False
    try:
        bytes.fromhex(salt_hex)
        bytes.fromhex(hash_hex)
    except ValueError:
        return False
    return True


@app.post("/api/backup/restore")
async def restore_backup(request: Request, _=Depends(require_auth_csrf)):
    content_length = request.headers.get("content-length")
    max_backup_bytes = 2 * 1024 * 1024
    if content_length and content_length.isdigit() and int(content_length) > max_backup_bytes:
        raise HTTPException(status_code=413, detail="backup too large")
    raw = await request.body()
    if len(raw) > max_backup_bytes:
        raise HTTPException(status_code=413, detail="backup too large")
    body = _decrypt_backup(raw)
    if not isinstance(body, dict) or body.get("version") not in (1, 2, BACKUP_VERSION):
        raise HTTPException(status_code=400, detail="نسخه‌ی بکاپ پشتیبانی نمی‌شود")

    links_data = body.get("links")
    if not isinstance(links_data, dict) or not links_data or len(links_data) > 10000:
        raise HTTPException(status_code=400, detail="بخش links نامعتبر یا بیش از حد بزرگ است")

    new_links = {}
    seen_subscription_tokens = set()
    for uid, data in links_data.items():
        if not isinstance(uid, str) or not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="رکورد لینک نامعتبر است")
        try:
            normalized_uid = str(uuidlib.UUID(uid))
            if normalized_uid != uid.lower():
                raise ValueError("uuid format")
            limit_bytes = int(data.get("limit_bytes", 0))
            used_bytes = int(data.get("used_bytes", 0))
            speed_bps = int(data.get("speed_limit_bps", 0) or 0)
            subscription_token = str(data.get("subscription_token") or "").strip()
            if subscription_token and not (32 <= len(subscription_token) <= 256):
                raise ValueError("invalid subscription token length")
            if not subscription_token:
                subscription_token = secrets.token_urlsafe(32)
            if subscription_token in seen_subscription_tokens:
                raise ValueError("duplicate subscription token")
            seen_subscription_tokens.add(subscription_token)
            if limit_bytes < 0 or used_bytes < 0 or speed_bps < 0:
                raise ValueError("negative value")
            if limit_bytes and used_bytes > limit_bytes:
                raise ValueError("usage exceeds limit")
            label = str(data.get("label", "لینک")).strip()[:60]
            if not label:
                label = "لینک"
            created_at = str(data.get("created_at") or datetime.now().isoformat())
            datetime.fromisoformat(created_at)
            expires_at = data.get("expires_at")
            if expires_at is not None:
                if not isinstance(expires_at, str):
                    raise ValueError("invalid expiry")
                datetime.fromisoformat(expires_at)
            new_links[normalized_uid] = {
                "label": label, "limit_bytes": limit_bytes, "used_bytes": used_bytes,
                "created_at": created_at, "active": bool(data.get("active", True)),
                "expires_at": expires_at, "speed_limit_bps": speed_bps,
                "subscription_token": subscription_token,
            }
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"رکورد لینک {uid!r} نامعتبر است")

    candidate = body.get("password_hash")
    if candidate is not None and not _validate_password_hash_format(candidate):
        raise HTTPException(status_code=400, detail="فرمت رمز عبور در فایل بکاپ نامعتبر است")

    # مهم: هیچ تغییر حافظه‌ای قبل از commit موفق DB انجام نمی‌شود.
    current_token = request.cookies.get(SESSION_COOKIE)
    async with LINKS_LOCK:
        async with DB_LOCK:
            await asyncio.to_thread(_db_restore_sync, new_links, candidate)
        LINKS.clear()
        LINKS.update(new_links)
        SUBSCRIPTION_INDEX.clear()
        for restored_uid, restored_data in new_links.items():
            token = restored_data.get("subscription_token")
            if token:
                SUBSCRIPTION_INDEX[token] = restored_uid
        _dirty_usage_uids.clear()

    restored_password = candidate is not None
    if restored_password:
        AUTH["password_hash"] = candidate
        # باگ واقعی: این بخش قبلاً فقط دیکشنری درون‌حافظه‌ای SESSIONS را
        # پاک می‌کرد. وقتی Redis پیکربندی شده باشد (چند instance)، سشن‌ها
        # واقعاً در Redis نگه‌داری می‌شوند (is_valid_session/create_session
        # وقتی redis_client ست باشد اصلاً به SESSIONS نگاه نمی‌کنند)، پس
        # بازیابیِ بکاپ همراه با رمز عبور جدید هیچ سشن فعالی را باطل
        # نمی‌کرد — دقیقاً همان تهدیدی که این پاک‌سازی قرار بود جلویش را
        # بگیرد (مثلاً یک سشن لو رفته که ادمین با تغییر/بازیابی رمز عبور
        # می‌خواهد باطلش کند). همان منطقِ api_change_password اینجا هم
        # اعمال می‌شود تا هر دو مسیر سازگار و امن باشند.
        if redis_client is not None:
            keys = []
            async for key in redis_client.scan_iter(match="vortex:session:*", count=100):
                keys.append(key)
            if keys:
                await redis_client.delete(*keys)
            if current_token:
                await redis_client.setex(f"vortex:session:{current_token}", SESSION_TTL, "1")
        else:
            async with SESSIONS_LOCK:
                SESSIONS.clear()
                if current_token:
                    SESSIONS[current_token] = time.time() + SESSION_TTL

    _notified_pct.clear()
    link_hourly_traffic.clear()
    asyncio.create_task(audit("backup_restore", client_ip(request), f"links={len(new_links)} password_restored={restored_password}"))
    logger.info("♻️ AUDIT backup restored: %d links, password_restored=%s, ip=%s", len(new_links), restored_password, client_ip(request))
    return {"ok": True, "restored_links": len(new_links), "restored_password": restored_password}


# ───────────────────────── VLESS relay ─────────────────────────

RELAY_BUF = 64 * 1024


class VlessHeaderIncomplete(ValueError):
    """VLESS header is valid so far, but more bytes are required."""


def _need(chunk: bytes, pos: int, n: int, what: str):
    """بررسی می‌کند که n بایت بعد از pos واقعاً در chunk موجود باشد.

    کمبود داده یک خطای «موقت» است، نه malformed packet: در WebSocket ممکن
    است بعضی کلاینت‌ها هدر اولیه‌ی VLESS را در بیش از یک message تحویل دهند.
    این تمایز اجازه می‌دهد caller تا کامل شدن هدر صبر کند، بدون این‌که packet
    واقعاً خراب با سکوت پذیرفته شود.
    """
    if pos + n > len(chunk):
        raise VlessHeaderIncomplete(f"incomplete VLESS header: need {n} more bytes for {what}")


async def parse_vless_header(chunk: bytes, expected_uuid: str | None = None):
    if len(chunk) < 24:
        raise VlessHeaderIncomplete("incomplete VLESS header: need at least 24 bytes")
    if chunk[0] != 0:
        raise ValueError("unsupported VLESS version")
    header_uuid = str(uuidlib.UUID(bytes=chunk[1:17]))
    if expected_uuid is not None:
        try:
            expected_uuid_norm = str(uuidlib.UUID(expected_uuid))
        except ValueError:
            raise ValueError("invalid link uuid")
        if not hmac.compare_digest(header_uuid, expected_uuid_norm):
            raise ValueError("VLESS UUID does not match tunnel path")
    pos = 17

    _need(chunk, pos, 1, "addon length")
    addon_len = chunk[pos]
    pos += 1
    _need(chunk, pos, addon_len, "addons")
    pos += addon_len
    _need(chunk, pos, 1, "command")
    command = chunk[pos]
    pos += 1
    if command != 1:
        raise ValueError("only TCP VLESS command is supported")

    _need(chunk, pos, 2, "port")
    port = int.from_bytes(chunk[pos:pos + 2], "big")
    pos += 2
    if port == 0:
        raise ValueError("invalid destination port")
    vless_allowed_ports = CONFIG.get("vless_allowed_ports", set())
    if vless_allowed_ports and port not in vless_allowed_ports:
        raise ValueError(f"VLESS destination port is not allowed: {port}")
    if len(chunk) > CONFIG["max_ws_initial_bytes"]:
        raise ValueError("initial VLESS frame too large")

    _need(chunk, pos, 1, "address type")
    addr_type = chunk[pos]
    pos += 1

    if addr_type == 1:
        _need(chunk, pos, 4, "IPv4 address")
        address = ".".join(str(b) for b in chunk[pos:pos + 4])
        pos += 4
    elif addr_type == 2:
        _need(chunk, pos, 1, "domain length")
        dlen = chunk[pos]
        pos += 1
        if dlen == 0 or dlen > 253:
            raise ValueError("invalid domain length")
        _need(chunk, pos, dlen, "domain name")
        raw_domain = chunk[pos:pos + dlen].decode("utf-8", errors="strict").strip().rstrip(".")
        try:
            address = raw_domain.encode("idna").decode("ascii")
        except UnicodeError:
            raise ValueError("invalid domain name")
        if not address or any(ord(c) < 32 or ord(c) == 127 for c in address):
            raise ValueError("invalid domain name")
        pos += dlen
    elif addr_type == 3:
        _need(chunk, pos, 16, "IPv6 address")
        raw = chunk[pos:pos + 16]
        address = ":".join(f"{raw[i]:02x}{raw[i+1]:02x}" for i in range(0, 16, 2))
        pos += 16
    else:
        raise ValueError(f"unknown address type: {addr_type}")

    if not address:
        raise ValueError("empty destination address")
    return address, port, chunk[pos:]


async def receive_vless_initial(websocket: WebSocket, expected_uuid: str, max_bytes: int, timeout: float = 15.0):
    """Receive enough WebSocket data to parse a complete VLESS request header.

    Some clients deliver the first VLESS request as multiple WebSocket messages.
    The previous implementation tried to parse only the first message, which
    turned a perfectly valid fragmented request into ValueError and immediately
    closed the tunnel. We buffer only the bounded initial request header/payload,
    then hand all bytes after the VLESS header to the normal upstream path.
    """
    buffer = bytearray()
    deadline = asyncio.get_running_loop().time() + timeout

    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise TimeoutError("timed out waiting for complete VLESS header")

        msg = await asyncio.wait_for(websocket.receive(), timeout=remaining)
        if msg.get("type") == "websocket.disconnect":
            raise WebSocketDisconnect(code=1000)

        data = msg.get("bytes")
        if data is None and msg.get("text"):
            data = msg["text"].encode()
        if not data:
            continue

        if len(buffer) + len(data) > max_bytes:
            raise ValueError("initial VLESS request too large")
        buffer.extend(data)

        try:
            return await parse_vless_header(bytes(buffer), expected_uuid=expected_uuid)
        except VlessHeaderIncomplete:
            continue


async def check_quota(uid: str, extra: int) -> bool:
    async with LINKS_LOCK:
        link = LINKS.get(uid)
        if link is None:
            # لینک ناشناس/حذف‌شده مطلقاً نباید اجازه‌ی عبور بگیرد — این خط
            # همان چیزی است که کل مکانیزم لینک/سهمیه را معنا می‌دهد.
            return False
        if not link["active"]:
            return False
        if is_link_expired(link):
            return False
        if link["limit_bytes"] == 0:
            return True
        return (link["used_bytes"] + extra) <= link["limit_bytes"]


async def reserve_usage(uid: str, n: int) -> tuple[bool, int]:
    """چک کردن سهمیه (و انقضا) و ثبت مصرف را در یک قفل واحد انجام می‌دهد.

    قبلاً check_quota و add_usage دو قفل جدا می‌گرفتند؛ بین این دو، چند
    chunk هم‌زمان می‌توانستند همه از یک quota باقی‌مانده‌ی یکسان عبور کنند
    و در مجموع کمی بیشتر از سقف مصرف ثبت شود (race). با یک قفل واحد این
    مشکل برطرف می‌شود.

    خروجی (ok, speed_limit_bps) است؛ speed_limit_bps را فراخوان برای
    throttle کردن ارسال همان chunk استفاده می‌کند (بدون نیاز به یک lookup
    جداگانه‌ی LINKS).
    """
    async with LINKS_LOCK:
        link = LINKS.get(uid)
        if link is None or not link["active"]:
            return False, 0
        if is_link_expired(link):
            return False, 0
        if link["limit_bytes"] != 0 and (link["used_bytes"] + n) > link["limit_bytes"]:
            return False, 0
        link["used_bytes"] += n
        _dirty_usage_uids.add(uid)  # به‌جای نوشتن فوری روی دیسک، فقط علامت می‌زنیم؛ _periodic_usage_flush آن را دوره‌ای ذخیره می‌کند
        speed_limit_bps = link.get("speed_limit_bps", 0)
        pct = (link["used_bytes"] / link["limit_bytes"] * 100) if link["limit_bytes"] else None
        label = link["label"]
    # چک/ارسال اعلان تلگرام عمداً بیرون از LINKS_LOCK انجام می‌شود تا مسیر
    # داغِ رله‌ی داده هرگز منتظر یک درخواست شبکه‌ای (تلگرام) نماند.
    if pct is not None:
        _maybe_schedule_quota_alert(uid, label, pct)
    return True, speed_limit_bps


def _track(uid: str, conn_id: str, size: int):
    stats["total_bytes"] += size
    stats["total_requests"] += 1
    connections[conn_id]["bytes"] += size
    hour_key = datetime.now().strftime("%H:00")
    hourly_traffic[hour_key] += size
    link_hourly_traffic[uid][hour_key] += size


async def upstream_to_client(ws: WebSocket, writer: asyncio.StreamWriter, conn_id: str, link_uid: str):
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            data = msg.get("bytes") or (msg.get("text", "").encode() if msg.get("text") else None)
            if not data:
                continue
            ok, speed_limit_bps = await reserve_usage(link_uid, len(data))
            if not ok:
                await ws.close(code=1008, reason="quota exceeded")
                break
            _track(link_uid, conn_id, len(data))
            await throttle(link_uid, speed_limit_bps, len(data))
            writer.write(data)
            await writer.drain()
    except WebSocketDisconnect:
        pass
    finally:
        try:
            writer.write_eof()
        except Exception:
            pass


async def downstream_to_client(ws: WebSocket, reader: asyncio.StreamReader, conn_id: str, link_uid: str):
    first = True
    try:
        while True:
            data = await reader.read(RELAY_BUF)
            if not data:
                break
            ok, speed_limit_bps = await reserve_usage(link_uid, len(data))
            if not ok:
                await ws.close(code=1008, reason="quota exceeded")
                break
            _track(link_uid, conn_id, len(data))
            await throttle(link_uid, speed_limit_bps, len(data))
            await ws.send_bytes((b"\x00\x00" + data) if first else data)
            first = False
    except Exception:
        pass



async def try_acquire_ip_slot(ip: str) -> bool:
    async with CONNECTIONS_LOCK:
        if connections_by_ip.get(ip, 0) >= CONFIG["max_connections_per_ip"]:
            return False
        connections_by_ip[ip] += 1
        return True

async def release_ip_slot(ip: str) -> None:
    async with CONNECTIONS_LOCK:
        current = connections_by_ip.get(ip, 0)
        if current <= 1:
            connections_by_ip.pop(ip, None)
        else:
            connections_by_ip[ip] = current - 1

def _allowed_origins(request_host_header: str | None = None) -> set[str]:
    """Compute the set of Origins allowed to talk to this gateway's panel/API/tunnel.

    باگ واقعی که اینجا پیدا شد: این لیست قبلاً فقط از روی RAILWAY_PUBLIC_DOMAIN
    ساخته می‌شد. اگر آن متغیر محیطی روی سرویس Railway تنظیم نشده باشد (یک
    اشتباه رایج: ساختن دامنه‌ی عمومی از Settings → Networking به‌خودی‌خود آن
    را به‌عنوان env var داخل کانتینر تزریق نمی‌کند)، get_host() به "localhost"
    سقوط می‌کرد و این لیست عملاً به {"http://localhost:8000"} محدود می‌شد.
    نتیجه: هر اتصال واقعی (وب‌سوکت یا CORS) که هدر Origin بفرستد — صفحه‌ی
    تست /test-ws در مرورگر، درخواست‌های AJAX پنل، یا برخی کلاینت‌های VLESS —
    با 1008/403 رد می‌شد؛ دقیقاً وقتی مستقیم به دامنه‌ی Railway وصل می‌شدی،
    نه وقتی از طریق Cloudflare Worker Relay (که ORIGIN را در زمان دیپلوی از
    هدر Host همان درخواست تشخیص می‌دهد، نه از این متغیر محیطی).

    برای اینکه این چک اصلاً به تنظیم دستیِ RAILWAY_PUBLIC_DOMAIN وابسته
    نباشد، هاست واقعیِ همین درخواست هم همیشه به‌عنوان مبدأ مجاز اضافه
    می‌شود — هم به‌صورت خودکار در get_host() (از طریق _note_request_host)
    و هم مستقیماً اینجا، تا حتی پیش از اولین بار "یادگرفتن" هاست هم درست
    کار کند.
    """
    allowed = {get_public_origin(), "http://localhost:8000"}
    parts = _worker_endpoint_parts()
    if parts:
        endpoint_host, _gate_path = parts
        worker_url = ACTIVE_WORKER_URL.strip().rstrip("/")
        parsed = urlparse(worker_url)
        if parsed.scheme and parsed.netloc:
            allowed.add(f"{parsed.scheme}://{parsed.netloc}")
    header_host = (request_host_header or "").strip()
    if header_host:
        allowed.add(f"https://{header_host}")
        allowed.add(f"http://{header_host}")
    return allowed


def _allowed_websocket_origins(websocket: WebSocket | None = None) -> set[str]:
    header_host = websocket.headers.get("host") if websocket is not None else None
    return _allowed_origins(header_host)


def websocket_client_ip(websocket: WebSocket) -> str:
    # نکته‌ی امنیتی (باگ واقعی که در این بازبینی پیدا شد): این تابع قبلاً
    # ساده‌ترین مقدار X-Forwarded-For یعنی سمت چپ‌ترین (parts[0]) را
    # به‌عنوان IP واقعی کلاینت می‌پذیرفت. آن مقدار توسط خودِ کلاینت قابل
    # جعل است (کلاینت هر مقداری برای X-Forwarded-For بفرستد، پراکسی مورد
    # اعتماد معمولاً آن را دست‌نخورده جلو می‌فرستد و فقط IP خودش را به
    # انتهای زنجیره اضافه می‌کند). یعنی یک کلاینت می‌توانست با تغییر همین
    # هدر، سقف «حداکثر اتصال هم‌زمان به‌ازای هر IP» (MAX_CONNECTIONS_PER_IP)
    # را کاملاً دور بزند و هم‌چنین آدرس نادرستی در آدیت‌لاگ ثبت شود.
    #
    # همان منطقِ درستِ client_ip() (بالا) اینجا هم پیاده می‌شود: از
    # راست‌ترین مقدار زنجیره شروع می‌کنیم و تا وقتی هاپ‌ها در محدوده‌ی
    # پراکسی‌های مورد اعتماد هستند جلو می‌رویم؛ اولین هاپِ غیرمورداعتماد،
    # IP واقعی کلاینت است.
    peer = websocket.client.host if websocket.client else "unknown"
    if not CONFIG["trust_proxy"] or not TRUSTED_PROXY_NETWORKS:
        return peer
    try:
        peer_addr = ipaddress.ip_address(peer)
    except ValueError:
        return peer
    if not any(peer_addr in network for network in TRUSTED_PROXY_NETWORKS):
        return peer
    forwarded = websocket.headers.get("x-forwarded-for", "")
    values = [p.strip() for p in forwarded.split(",") if p.strip()]
    values.append(peer)
    for value in reversed(values):
        try:
            ip = ipaddress.ip_address(value)
        except ValueError:
            continue
        if not any(ip in net for net in TRUSTED_PROXY_NETWORKS):
            return str(ip)
    return peer


def _tune_socket(writer: asyncio.StreamWriter) -> None:
    """TCP_NODELAY + بافر بزرگ‌تر روی سوکت خروجی به مقصد.

    باگ واقعی که اینجا پیدا شد: سوکت خروجی هیچ tuning ای نداشت، یعنی
    الگوریتم Nagle روی آن فعال می‌ماند. برای بسته‌های کوچک و پشت‌سرهم
    (مثل ClientHello تی‌ال‌اس یا چانک‌های اولیه‌ی VLESS) این باعث تأخیر
    قابل توجه (Nagle + Delayed-ACK) می‌شود که روی زیرساخت شبکه‌ی Railway
    به اندازه‌ای کش پیدا می‌کند که کلاینت یا خودِ شبکه کانکشن را به‌عنوان
    بی‌فعالیت ببندد — دقیقاً همان الگوی «چند ثانیه وصل، بعد پینگ -۱».
    """
    try:
        sock = writer.get_extra_info("socket")
        if sock is not None:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    except Exception as exc:
        logger.warning("tune_socket failed: %s", exc)


@app.websocket("/tunnel/{uid}")
async def websocket_tunnel_tunnel_path(websocket: WebSocket, uid: str):
    return await _websocket_tunnel_impl(websocket, uid)


@app.websocket("/ws/{uid}")
async def websocket_tunnel_ws_path(websocket: WebSocket, uid: str):
    return await _websocket_tunnel_impl(websocket, uid)


async def _websocket_tunnel_impl(websocket: WebSocket, uid: str):
    _note_request_host(websocket.headers.get("host"))
    origin = websocket.headers.get("origin")
    allowed_origins = _allowed_websocket_origins(websocket)
    if origin and origin not in allowed_origins:
        await websocket.close(code=1008, reason="origin not allowed")
        return
    peer_ip = websocket_client_ip(websocket)
    if not await try_acquire_ip_slot(peer_ip):
        await websocket.close(code=1008, reason="too many connections from client")
        return
    await websocket.accept()

    # سقف تعداد اتصال هم‌زمان (کلی و به‌ازای هر لینک) — قبل از ثبت در
    # connections بررسی می‌شود تا یک لینک نتواند با باز کردن اتصال‌های
    # بی‌شمار سرور را از منابع خالی کند.
    if not await try_acquire_connection_slot(uid):
        await websocket.close(code=1008, reason="too many concurrent connections")
        await release_ip_slot(peer_ip)
        return

    conn_id = secrets.token_urlsafe(8)
    connections[conn_id] = {"uuid": uid, "connected_at": datetime.now().isoformat(), "bytes": 0}
    logger.info("✅ tunnel open [%s] link=%s active=%d", conn_id, uid[:8], len(connections))
    current_task = asyncio.current_task()
    if current_task is not None:
        RELAY_TASKS.add(current_task)
    writer = None
    try:
        if not await check_quota(uid, 0):
            await websocket.close(code=1008, reason="quota exceeded or link disabled")
            return
        address, port, initial_payload = await receive_vless_initial(
            websocket,
            expected_uuid=uid,
            max_bytes=CONFIG["max_ws_initial_bytes"],
            timeout=15.0,
        )

        # محافظت SSRF: قبلاً این بررسی فقط برای HTTP Proxy انجام می‌شد، اما
        # تونل VLESS هم یک راه مستقیم برای اتصال به هر IP:port دلخواه است.
        # بدون این چک، هر کسی که یک UUID لینک معتبر داشته باشد (که طبیعتاً
        # قرار است بین چند کاربر به اشتراک گذاشته شود) می‌توانست از طریق
        # سرور به شبکه‌ی داخلی هاست (localhost، رنج‌های خصوصی، متادیتای
        # کلاود مثل 169.254.169.254 و ...) دسترسی پیدا کند. همان تابع
        # resolve_safe_ip که برای پروکسی HTTP نوشته شده اینجا هم استفاده
        # می‌شود و مستقیماً به IP امن resolve‌شده وصل می‌شویم (نه به hostname)
        # تا از DNS rebinding هم در امان باشیم.
        safe_ips = await resolve_safe_ips(address)
        if not safe_ips:
            raise ValueError(f"blocked/unresolvable destination: {address}:{port}")

        # Count only application payload, not the VLESS framing/header.
        if initial_payload:
            ok, speed_limit_bps = await reserve_usage(uid, len(initial_payload))
            if not ok:
                await websocket.close(code=1008, reason="quota exceeded")
                return
            _track(uid, conn_id, len(initial_payload))
            await throttle(uid, speed_limit_bps, len(initial_payload))
        logger.info("➡️  [%s] CONNECT %s:%s candidates=%s", conn_id, address, port, len(safe_ips))

        last_connect_error = None
        for safe_ip in safe_ips:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(safe_ip, port), timeout=10.0
                )
                logger.info("✅ [%s] connected via %s:%s", conn_id, safe_ip, port)
                break
            except (OSError, asyncio.TimeoutError) as exc:
                last_connect_error = exc
                logger.warning("⚠️ [%s] connect failed via %s:%s: %s: %s", conn_id, safe_ip, port, type(exc).__name__, exc)
        else:
            raise last_connect_error or ConnectionError(f"unable to connect to {address}:{port}")
        _tune_socket(writer)
        if initial_payload:
            writer.write(initial_payload)
            await writer.drain()

        up = asyncio.create_task(upstream_to_client(websocket, writer, conn_id, uid), name=f"vortex-up-{conn_id}")
        down = asyncio.create_task(downstream_to_client(websocket, reader, conn_id, uid), name=f"vortex-down-{conn_id}")
        done, pending = await asyncio.wait({up, down}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            with contextlib.suppress(Exception):
                task.result()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        stats["total_errors"] += 1
        error_logs.append({"error": "tunnel request failed", "time": datetime.now().isoformat()})
        logger.error("tunnel error [%s]: %s: %s", conn_id, type(exc).__name__, exc)
    finally:
        if writer:
            try:
                writer.close()
            except Exception:
                pass
        connections.pop(conn_id, None)
        if current_task is not None:
            RELAY_TASKS.discard(current_task)
        await release_connection_slot(uid)
        await release_ip_slot(peer_ip)
        logger.info("🔌 tunnel closed [%s] active=%d", conn_id, len(connections))


# ───────────────────────── HTTP Proxy (authenticated + SSRF-protected) ─────────────────────────

PROXY_MAX_BODY_BYTES = CONFIG["max_http_body_bytes"]

_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "content-length",
}


@app.api_route("/api/proxy/{target_url:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"])
async def http_proxy(target_url: str, request: Request):
    await require_auth(request)
    if request.method not in {"GET", "HEAD"}:
        await require_auth_csrf(request)
    if len(target_url) > CONFIG["proxy_max_url_length"]:
        raise HTTPException(status_code=414, detail="proxy URL too long")
    if not target_url.lower().startswith(("http://", "https://")):
        target_url = "https://" + target_url
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    if len(target_url) > CONFIG["proxy_max_url_length"]:
        raise HTTPException(status_code=414, detail="proxy URL too long")

    allowed, reason, safe_ip = await is_proxy_target_allowed(target_url)
    if not allowed:
        raise HTTPException(status_code=403, detail=f"proxy target rejected: {reason}")

    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > PROXY_MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="request body too large")

    try:
        body = await request.body()
        if len(body) > PROXY_MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="request body too large")
        parsed = urlparse(target_url)
        if parsed.username or parsed.password:
            raise HTTPException(status_code=400, detail="userinfo in proxy URL is not allowed")
        headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_HEADERS and k.lower() != "host"}
        pinned_netloc = safe_ip if ":" not in safe_ip else f"[{safe_ip}]"
        if parsed.port:
            pinned_netloc += f":{parsed.port}"
        pinned_url = parsed._replace(netloc=pinned_netloc).geturl()
        headers["host"] = parsed.hostname

        response_ctx = http_client.stream(
            method=request.method, url=pinned_url, headers=headers, content=body,
            extensions={"sni_hostname": parsed.hostname},
        )
        resp = await response_ctx.__aenter__()

        async def stream_response():
            total = 0
            try:
                async for chunk in resp.aiter_bytes(RELAY_BUF):
                    total += len(chunk)
                    if total > CONFIG["proxy_max_response_bytes"]:
                        raise RuntimeError("proxy response exceeded configured limit")
                    stats["total_bytes"] += len(chunk)
                    stats["total_requests"] += 1
                    hourly_traffic[datetime.now().strftime("%H:00")] += len(chunk)
                    yield chunk
            finally:
                await resp.aclose()
                await response_ctx.__aexit__(None, None, None)

        resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in _HOP_HEADERS}
        return StreamingResponse(stream_response(), status_code=resp.status_code, headers=resp_headers)
    except HTTPException:
        raise
    except Exception as exc:
        stats["total_errors"] += 1
        error_logs.append({"error": "proxy request failed", "time": datetime.now().isoformat()})
        logger.error("proxy request failed: %s", exc)
        raise HTTPException(status_code=502, detail="proxy error: unable to reach target")


# ───────────────────────── Web UI ─────────────────────────

from templates import DASHBOARD_HTML, LOGIN_HTML, SUB_HTML, SUB_NOTFOUND_HTML  # noqa: E402


def _with_csp_nonce(page_html: str, nonce: str) -> str:
    # فقط تگ‌های <script> بدون src (اسکریپت inline خودمان) را nonce می‌زنیم؛
    # تگ <script src="https://cdnjs..."> دست‌نخورده می‌ماند چون از طریق
    # host-source در CSP مجاز شده، نه نیاز به nonce دارد.
    return page_html.replace("<script>", f'<script nonce="{nonce}">')


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if await is_valid_session(token):
        return RedirectResponse(url="/dashboard")
    return HTMLResponse(content=_with_csp_nonce(LOGIN_HTML, request.state.csp_nonce))


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not await is_valid_session(token):
        return RedirectResponse(url="/login")
    await ensure_default_link()
    return HTMLResponse(content=_with_csp_nonce(DASHBOARD_HTML, request.state.csp_nonce))


# ───────────────────────── Subscription page ─────────────────────────
# آدرس عمومی (بدون نیاز به لاگین پنل — دقیقاً مثل /tunnel/{uid}، خودِ uuid
# لینک نقش «رمز اشتراک» را بازی می‌کند) که با کاربر نهایی به اشتراک گذاشته
# می‌شود. دو نوع کلاینت این آدرس را می‌زنند:
#   ۱) مرورگر یک انسان → صفحه‌ی HTML خوانا با وضعیت/مصرف/QR
#   ۲) اپ‌های VPN (V2rayNG/NekoBox/Clash/...) که این آدرس را به‌عنوان
#      subscription URL اضافه کرده‌اند و خودشان دوره‌ای فچش می‌کنند →
#      محتوای base64 استاندارد + هدرهای Subscription-Userinfo
# تشخیص بر اساس User-Agent است؛ اگر اپی شناسایی نشد، صفحه‌ی انسانی برگردانده
# می‌شود (بی‌ضرر — فقط یعنی آن اپ لینک را در صفحه پیدا نمی‌کند، نه خطا).

SUBSCRIPTION_CLIENT_UA_MARKERS = (
    "v2rayng", "v2rayn", "nekobox", "nekoray", "clash", "clashx", "clash-verge",
    "flclash", "shadowrocket", "streisand", "hiddify", "sing-box", "sfa", "sfi",
    "sfm", "v2box", "furious", "matsuri", "kitsunebi", "quantumult", "surge",
    "loon", "stash", "karing", "husi", "happ",
)


def _is_subscription_client(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return any(marker in ua for marker in SUBSCRIPTION_CLIENT_UA_MARKERS)


def _fmt_bytes_fa(n: int) -> str:
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.2f} GB"
    if n >= 1024 ** 2:
        return f"{n / 1024 ** 2:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


def _fmt_speed_fa(bps: int) -> str:
    if not bps:
        return "نامحدود"
    if bps >= 1024 ** 2:
        return f"{bps / 1024 ** 2:.1f} MB/s"
    return f"{bps / 1024:.0f} KB/s"


def _days_left(expires_at: str | None) -> int:
    """تعداد روزهای باقی‌مانده تا انقضا (سقف‌گرد به بالا، حداقل ۰). فرض بر
    این است که قبلاً is_link_expired چک شده و لینک هنوز منقضی نیست."""
    if not expires_at:
        return 0
    try:
        exp = datetime.fromisoformat(expires_at)
    except ValueError:
        return 0
    remaining_seconds = int((exp - datetime.now()).total_seconds())
    if remaining_seconds <= 0:
        return 0
    return -(-remaining_seconds // 86400)  # ceiling division


@app.get("/sub/{token}")
async def subscription_page(token: str, request: Request):
    async with LINKS_LOCK:
        uid = SUBSCRIPTION_INDEX.get(token)
        snapshot = dict(LINKS[uid]) if uid and uid in LINKS else None
        # Constant-time comparison is still used for the token itself at the
        # security boundary; the index only narrows the candidate to O(1).
        if snapshot is not None:
            stored_token = str(snapshot.get("subscription_token", ""))
            if not hmac.compare_digest(stored_token, token):
                snapshot = None
                uid = None
        # Optional compatibility window for old UUID-based subscription URLs.
        if snapshot is None and CONFIG["allow_legacy_subscription_uuid"]:
            candidate = LINKS.get(token)
            if candidate is not None:
                uid = token
                snapshot = dict(candidate)

    if snapshot is None:
        return HTMLResponse(
            content=_with_csp_nonce(SUB_NOTFOUND_HTML, request.state.csp_nonce),
            status_code=404,
        )

    host = get_host()
    vless_link = generate_vless_link(uid, host, remark=f"Vortex-{snapshot['label']}")
    sub_link = generate_sub_url(uid, host)
    expired = is_link_expired(snapshot)

    accept = (request.headers.get("accept") or "").lower()
    user_agent = request.headers.get("user-agent", "")
    browser_like = "mozilla/" in user_agent.lower() or "chrome/" in user_agent.lower() or "safari/" in user_agent.lower()
    wants_machine_subscription = (
        _is_subscription_client(user_agent)
        or (not browser_like and "text/html" not in accept)
        or (not browser_like and accept in {"", "*/*"})
        or request.query_params.get("format", "").lower() in {"sub", "base64", "vless"}
    )
    if wants_machine_subscription:
        # Machine-readable subscription: one VLESS URI per line, base64 encoded.
        content = base64.b64encode((vless_link + "\n").encode()).decode()
        expire_ts = 0
        if snapshot.get("expires_at"):
            try:
                expire_ts = int(datetime.fromisoformat(snapshot["expires_at"]).timestamp())
            except ValueError:
                expire_ts = 0
        headers = {
            # اکثر کلاینت‌ها هر چند ساعت یک‌بار (طبق این هدر) ساب را خودکار
            # رفرش می‌کنند تا تغییرات ادمین (فعال/غیرفعال، سقف جدید) اعمال شود.
            "Profile-Update-Interval": "12",
            "Profile-Title": base64.b64encode(snapshot["label"].encode()).decode(),
            "Subscription-Userinfo": (
                f"upload=0; download={snapshot['used_bytes']}; "
                f"total={snapshot['limit_bytes']}; expire={expire_ts}"
            ),
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "no-store, no-cache, must-revalidate",
        }
        return PlainTextResponse(content=content, headers=headers)

    # پاسخ انسانی: صفحه‌ی HTML با وضعیت لینک
    if expired:
        status_badge = '<span class="badge warn"><i class="ti ti-clock-off"></i> منقضی‌شده</span>'
    elif not snapshot["active"]:
        status_badge = '<span class="badge warn"><i class="ti ti-player-pause"></i> غیرفعال</span>'
    else:
        status_badge = '<span class="badge ok"><i class="ti ti-circle-check"></i> فعال</span>'

    limit_bytes = snapshot["limit_bytes"]
    used_bytes = snapshot["used_bytes"]
    percent = min(100, round(used_bytes / limit_bytes * 100, 1)) if limit_bytes else 0
    used_str = _fmt_bytes_fa(used_bytes)
    limit_str = "نامحدود" if limit_bytes == 0 else _fmt_bytes_fa(limit_bytes)

    if not snapshot.get("expires_at"):
        days_str = "بدون انقضا"
    elif expired:
        days_str = "منقضی‌شده"
    else:
        days_str = f"{_days_left(snapshot['expires_at'])} روز"

    speed_str = _fmt_speed_fa(snapshot.get("speed_limit_bps", 0))

    page = (
        SUB_HTML
        .replace("__LABEL__", html.escape(snapshot["label"]))
        .replace("__STATUS_BADGE__", status_badge)
        .replace("__PERCENT__", str(percent))
        .replace("__USED__", html.escape(used_str))
        .replace("__LIMIT__", html.escape(limit_str))
        .replace("__DAYS__", html.escape(days_str))
        .replace("__SPEED__", html.escape(speed_str))
        .replace("__VLESS_LINK_TEXT__", html.escape(vless_link))
        .replace("__VLESS_LINK_JSON__", json.dumps(vless_link))
        .replace("__SUB_LINK_JSON__", json.dumps(sub_link))
    )
    return HTMLResponse(content=_with_csp_nonce(page, request.state.csp_nonce))


if __name__ == "__main__":
    # ws_max_size: سقف اندازه‌ی هر فریم وب‌سوکت (پیش‌فرض کتابخانه‌ی websockets معمولاً
    # ۱۶ مگابایت است که برای یک تونل عمومی زیاده؛ این‌جا محدودش می‌کنیم تا یک کلاینت
    # بدخواه نتواند با فریم‌های غول‌آسا حافظه‌ی سرور را مصرف کند).
    uvicorn.run(
        app, host="0.0.0.0", port=CONFIG["port"], ws_max_size=4 * 1024 * 1024,
        proxy_headers=False,  # client IP forwarding is validated by our own trusted-CIDR logic
    )

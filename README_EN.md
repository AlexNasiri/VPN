# 🌀 Vortex Gateway

**Vortex Gateway** is a hardened VLESS-over-WebSocket gateway with an administrative dashboard, traffic quotas, speed limits, a controlled HTTP proxy, encrypted SQLite backups, optional Redis-backed distributed session/rate-limit state, and optional Cloudflare Worker relay deployment.

Current application version: **4.1-hardened**.

> **Security note:** Treat every VLESS UUID, subscription URL/token, admin session, and backup-encryption key as sensitive credentials. Never commit secrets or production databases to Git.

## Features

- 🔐 First-run admin password setup; there is **no built-in/default admin password**.
- 🔑 Argon2id password hashing with transparent PBKDF2 migration for older installations.
- 🛡️ CSRF protection for state-changing dashboard operations.
- 🚦 Per-IP and global login throttling with bounded request bodies.
- 🌐 `X-Forwarded-For` is accepted only from explicitly trusted proxy CIDRs.
- 🧱 SSRF protections covering private/loopback/link-local/multicast/reserved/unspecified targets, alternate IPv4 forms, and IPv4-mapped IPv6 addresses.
- 🔒 Resolved destination IP pinning to reduce DNS-rebinding risk.
- 🚫 HTTP proxy fail-closed by default, with explicit domain and port controls.
- 🌊 Streaming proxy responses with configurable response and request limits.
- 📏 Strict VLESS validation for version, UUID, command, destination, and ports.
- ♻️ Transactional/atomic SQLite restore semantics.
- 🗃️ Persistent audit log and connection/traffic statistics.
- ❤️ Liveness and readiness endpoints for deployment platforms.
- 🔐 Encrypted backups using Fernet; plaintext backups require explicit opt-in.
- ⚡ Optional Redis for distributed sessions and login rate limiting.
- ☁️ Optional Cloudflare Worker relay deployment directly from the dashboard.
- 🐳 Non-root Docker image and Railway deployment configuration.
- 🧪 Security-focused automated test suite.

## Architecture

```text
                         ┌──────────────────────┐
                         │   Admin Dashboard     │
                         │  login / links / ops  │
                         └──────────┬───────────┘
                                    │
                                    ▼
┌───────────────┐        ┌──────────────────────┐        ┌────────────────┐
│ VLESS Clients │───────▶│    Vortex Gateway    │───────▶│ Public targets │
└───────────────┘   WS   │  Railway / Docker    │ Proxy  └────────────────┘
                         │                      │
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

The Cloudflare Worker is **only a relay**. VLESS parsing, authentication, quotas, proxy policy, and database state remain in Vortex Gateway.

## Requirements

- Python **3.13** for local development.
- Docker with a Python 3.13-compatible runtime, or Railway.
- Persistent storage for SQLite in production.
- Optional Redis if running more than one application instance or if distributed session/login state is required.

## Quick start

### 1. Clone and install

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

### 2. Configure local storage

The application default for `DB_PATH` is `/data/vortex_data.db`, which is appropriate for the container/Railway layout. For a normal local checkout, set a writable local path explicitly:

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

### 3. Start

```bash
python main.py
```

Open:

```text
http://localhost:8000/login
```

On the first run, the login page becomes the one-time setup page. Choose an admin password of **at least 4 characters**. There are no requirements for uppercase/lowercase letters, digits, or symbols.

`ADMIN_PASSWORD` is optional. When set as a deployment secret, the first startup without an existing password hash stores only its Argon2id hash. In Railway, `REQUIRE_PERSISTENT_VOLUME=0` is the default, so the app can start without a mounted Volume, but data under `/data` is ephemeral and may be lost across redeploys or container replacement. For persistent data, set `REQUIRE_PERSISTENT_VOLUME=1` and attach a real Volume at `/data`.

## Railway deployment

1. Push the repository to GitHub.
2. Create a Railway project from the GitHub repository.
3. Use the repository's `Dockerfile` build.
4. For automated persistence, after `railway link` run `scripts/deploy-railway.ps1` on Windows or `scripts/deploy-railway.sh` on Linux/macOS; if `/data` is missing, the script creates the Volume before deploying.
5. If you deploy directly from GitHub through the Railway dashboard, attach a Volume at `/data` once; a normal `railway.toml` deployment cannot safely create and attach the Volume before its own first run.
6. Set:

```text
DB_PATH=/data/vortex_data.db
```

6. Deploy and open `/login`.
7. Complete the one-time admin password setup.

The bundled `railway.toml` configures the Docker build, readiness endpoint, and restart policy. Railway should provide `PORT` automatically.

### Important persistence rule

A container filesystem is not a durable database. Without a persistent volume, a redeploy can lose the SQLite database and therefore links, settings, audit history, and the stored admin password hash.

## Docker

Build:

```bash
docker build -t vortex-gateway .
```

Run locally with a bind-mounted data directory:

```bash
docker run --rm \
  -p 8000:8000 \
  -v "$PWD/data:/data" \
  -e DB_PATH=/data/vortex_data.db \
  -e LOG_PATH=/data/vortex.log \
  vortex-gateway
```

Then open `http://localhost:8000/login`.

## Environment variables

The following table reflects the current code defaults.

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | HTTP server port. Railway normally injects this. |
| `RAILWAY_PUBLIC_DOMAIN` | `localhost` | Public hostname used when generating public links. Do not include `https://`. |
| `DB_PATH` | `/data/vortex_data.db` | SQLite database path. Use persistent storage in production. |
| `LOG_PATH` | `vortex.log` | Rotating application log file. |
| `TRUST_PROXY` | `0` | Trust forwarding headers only when explicitly enabled. |
| `TRUSTED_PROXY_CIDRS` | empty | Allowed source networks for trusted reverse proxies. Required when `TRUST_PROXY=1`. |
| `REDIS_URL` | empty | Optional Redis URL for distributed sessions and login rate limiting. |
| `SESSION_SECRET` | empty | Required when `REDIS_URL` is enabled; stable secret for consistent CSRF across replicas. |
| `BACKUP_ENCRYPTION_KEY` | empty | Fernet key used for encrypted backups. Required for encrypted backup creation. |
| `ALLOW_PLAINTEXT_BACKUP` | `0` | Explicit opt-in for restoring legacy/plaintext backups. Keep disabled in production. |
| `ALLOW_LEGACY_SUBSCRIPTION_UUID` | `0` | Temporarily accepts old UUID-based subscription URLs. Disable after migration. |
| `PROXY_ALLOWED_DOMAINS` | empty | Comma-separated proxy destination allowlist; supports entries such as `example.com` and `*.example.org`. |
| `PROXY_REQUIRE_ALLOWLIST` | `1` | When enabled, HTTP proxy requests are rejected until an allowlist is configured. |
| `PROXY_ALLOWED_PORTS` | `80,443,8080,8443` | Allowed outbound HTTP proxy ports. |
| `TUNNEL_ALLOWED_PORTS` | `80,443,8080,8443` | Allowed VLESS destination ports. |
| `PROXY_MAX_RESPONSE_BYTES` | `52428800` | Maximum streamed HTTP proxy response size (50 MiB). |
| `PROXY_MAX_URL_LENGTH` | `8192` | Maximum proxy URL length. |
| `MAX_HTTP_BODY_BYTES` | `2097152` | Maximum control-plane HTTP request body size (2 MiB). |
| `MAX_LOGIN_BODY_BYTES` | `16384` | Maximum login/setup request body size. |
| `MAX_WS_INITIAL_BYTES` | `16384` | Maximum initial VLESS WebSocket frame size. |
| `MAX_CONNECTIONS_GLOBAL` | `500` | Global concurrent WebSocket connection limit. |
| `MAX_CONNECTIONS_PER_IP` | `25` | Per-client-IP concurrent WebSocket limit. |
| `MAX_CONNECTIONS_PER_LINK` | `50` | Per-link concurrent WebSocket limit. |
| `AUTO_BACKUP_INTERVAL_HOURS` | `24` | Automatic encrypted backup interval. Set `<=0` to disable. |
| `AUTO_BACKUP_KEEP` | `7` | Number of automatic encrypted backups retained. |
| `AUTO_BACKUP_DIR` | `/data/backups` | Automatic backup directory. |
| `TELEGRAM_BOT_TOKEN` | empty | Optional Telegram bot token for traffic alerts. |
| `TELEGRAM_CHAT_ID` | empty | Optional Telegram destination chat ID. |

### Environment variables intentionally not used

`ADMIN_PASSWORD` is optional and may be set as a deployment secret to bootstrap the admin password on a deployment without persistent storage. Never commit it to source control.

## Backup and restore

### Generate a Fernet key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store the result as a secret, for example:

```text
BACKUP_ENCRYPTION_KEY=<generated-key>
```

Do **not** store the encryption key next to the backups. Losing the key means encrypted backups cannot be restored.

Automatic backups are encrypted before the final backup file is atomically installed. Plaintext backup restore is disabled unless explicitly enabled with `ALLOW_PLAINTEXT_BACKUP=1`.

## HTTP proxy safety

The dashboard proxy endpoint is authenticated and state-changing methods also require the CSRF token. Outbound destinations are subjected to SSRF checks and resolved IP pinning.

By default:

```text
PROXY_REQUIRE_ALLOWLIST=1
```

and an empty `PROXY_ALLOWED_DOMAINS` therefore means **proxy disabled/fail-closed**.

If you deliberately set `PROXY_REQUIRE_ALLOWLIST=0`, the proxy may reach any target that passes the SSRF checks and allowed-port policy. Only use that mode when the operational requirement is understood.

## Cloudflare Worker relay

The dashboard can create an optional Cloudflare Worker relay.

Flow:

```text
Client → Cloudflare Worker → Vortex Gateway → destination
```

The Worker does not replace the Vortex Gateway. It forwards requests to the public Vortex origin and keeps the actual VLESS/authentication logic on the gateway.

The deployment endpoint accepts the Cloudflare API token in the authenticated request body, validates it against Cloudflare, discovers an account, creates a uniquely named Worker, and stores the resulting Worker URL/settings. The token itself is not stored in the database.

For this feature, the gateway must already be reachable from the public internet. A localhost origin cannot be used as the Worker origin.

## API surface

### Public / health

- `GET /` — service metadata.
- `GET /health` — liveness/status summary.
- `GET /health/live` — lightweight liveness check.
- `GET /health/ready` — readiness check including SQLite integrity and optional Redis connectivity.
- `GET /sub/{subscription_token}` — subscription endpoint.
- `WS /tunnel/{uuid}` — VLESS WebSocket tunnel.

### Authentication/setup

- `GET /api/setup-status`
- `POST /api/setup-password`
- `POST /api/login`
- `POST /api/logout`
- `GET /api/me`
- `POST /api/change-password`

### Dashboard/operations

- `GET /api/system/status`
- `POST /api/system/storage-test`
- `GET /api/stats`
- `GET /api/audit`
- `GET /api/connections`
- `POST /api/notify/test`
- `POST /api/cloudflare/deploy-worker`

### Links and backups

- `GET /api/links`
- `POST /api/links`
- `PATCH /api/links/{uid}`
- `DELETE /api/links/{uid}`
- `GET /api/links/{uid}/traffic`
- `GET /api/backup`
- `POST /api/backup/restore`

### Authenticated proxy

- `GET|POST|PUT|DELETE|PATCH|HEAD /api/proxy/{target_url}`

## Redis and multiple instances

Redis currently provides distributed **sessions and login rate limiting** when `REDIS_URL` is configured.

SQLite remains the source of link data and other persistent state. This means the current release should still be treated primarily as a **single-instance architecture** for database-backed state. Running multiple instances requires shared/persistent SQLite storage semantics that are not a substitute for a true multi-writer database.

For a future horizontally scaled deployment, PostgreSQL is the natural next persistence step, while Redis can continue handling ephemeral/distributed state.

## TLS and reverse proxies

The application does not terminate TLS itself. In production, terminate TLS at Railway, a reverse proxy, or a load balancer.

Only set:

```text
TRUST_PROXY=1
```

when the application is actually behind a trusted proxy and the proxy overwrites forwarding headers correctly. Also configure the exact proxy networks through `TRUSTED_PROXY_CIDRS`.

## Testing

The project uses Python's standard `unittest` framework, so the test suite does not require pytest.

Run:

```bash
python -m unittest discover -s tests -v
```

The CI syntax check parses every Python source file without generating bytecode. To reproduce it locally:

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

CI additionally runs `pip check` and verifies that no generated Python bytecode artefacts are committed.

## Project structure

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

## Security guidance

Before publishing the repository:

- Never commit `.env`, SQLite databases, logs, generated backups, credentials, or API tokens.
- Never paste production `BACKUP_ENCRYPTION_KEY` into issues, pull requests, README files, or commit messages.
- Treat subscription URLs as credentials.
- Use persistent storage for production SQLite.
- Keep the HTTP proxy fail-closed unless a concrete allowlist/operational requirement exists.
- Use a long, unique admin password and change it if it has ever been exposed.

See [SECURITY.md](SECURITY.md) for the repository-specific security notes and deployment rules.

## Roadmap

- PostgreSQL-backed persistent state for true multi-instance deployment.
- Redis-backed distributed quota/connection accounting.
- Prometheus metrics.
- End-to-end WebSocket/HTTP proxy integration tests.
- Further modularization of the monolithic `main.py` into auth/proxy/tunnel/database modules.
- Static analysis/linting and dependency vulnerability checks in CI.

## License

No license file is included in the current repository. GitHub users should not assume permission to copy, modify, or redistribute the project unless the copyright holder adds an explicit license.

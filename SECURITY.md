# Security Notes

Vortex Gateway is an internet-facing gateway. Treat every VLESS UUID, subscription URL/token, admin session, and backup-encryption key as a credential.

## Security controls

- No built-in/default admin password; first-run setup is mandatory.
- Admin passwords require at least 4 characters; there are no character-class requirements.
- Passwords are stored as Argon2id hashes; older PBKDF2 hashes are transparently upgraded after successful authentication.
- CSRF protection is applied to state-changing dashboard operations.
- Login throttling is enforced per IP and with a global cap.
- `X-Forwarded-For` is trusted only when `TRUST_PROXY=1` and the peer belongs to `TRUSTED_PROXY_CIDRS`.
- SSRF checks block private, loopback, link-local, multicast, reserved, unspecified, and common alternate IP forms.
- Resolved destination IPs are pinned for outbound proxy connections to reduce DNS-rebinding exposure.
- HTTP proxy access is authenticated and fail-closed by default when no allowlist is configured.
- Outbound proxy and VLESS destination ports are allowlisted by default.
- Proxy request/response sizes and WebSocket initial frames are bounded.
- VLESS version, UUID, command, address and destination port are validated.
- SQLite restore is persisted transactionally and in-memory state is updated only after a successful restore commit.
- Automatic backups are encrypted and written atomically; plaintext backup restore is opt-in only.
- Audit events are persisted in SQLite.
- Security response headers and a per-request CSP nonce are applied to web responses.

## Deployment rules

1. Complete first-run password setup with a password of at least 4 characters. A longer, unique password is still recommended for internet-facing deployments.
2. Do not create or expect an `ADMIN_PASSWORD` environment variable; it is intentionally outside the configuration contract.
3. Put SQLite on persistent storage in production.
4. Keep TLS in front of the application.
5. Enable `TRUST_PROXY=1` only when a trusted reverse proxy overwrites forwarding headers and its source CIDRs are explicitly configured.
6. Keep `PROXY_REQUIRE_ALLOWLIST=1` unless there is a reviewed reason to disable fail-closed behavior.
7. Keep encrypted backup keys separate from backup files and application data.
8. Never commit `.env`, databases, logs, backup files, tokens, or API credentials.
9. For multi-instance deployments, use shared Redis for distributed sessions/login throttling and plan a migration to PostgreSQL for durable multi-writer state.

## Cloudflare Worker relay

The dashboard can accept a Cloudflare API token to deploy a Worker relay. The token is used for the API operation and is not written to the application database. Operators should still treat browser history, debugging output, reverse-proxy logs, and support artifacts as potentially sensitive when working with provider tokens.

## Reporting a vulnerability

Do not publish a suspected credential or a detailed exploit chain in a public GitHub issue. Contact the repository maintainer through a private security channel and include enough information to reproduce the problem safely.

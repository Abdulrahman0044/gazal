# GAZAL. production deployment guide

The delivered package is a tested development application. Production launch still needs live infrastructure verification and the authentication/operational work listed below. The Supabase project URL is configured, but no database credential has been supplied or live project migration applied.

## 1. Choose the runtime
Use a Python-capable container host or a VPS behind an HTTPS reverse proxy. Use requirements.lock.txt for the tested Linux/Python 3.12 dependency set. The included Dockerfile is a starting configuration; its image has not been built in this environment. Ordinary static hosting cannot run FastAPI. If using shared cPanel hosting, confirm Python ASGI support and managed background processes first; otherwise use a separate backend host. Serve the landing page, shared auth pages and /app from the same origin.

## 2. Configure secrets and environments
.env.local is included with development values and blank credentials; it loads automatically in development. .env.example documents local settings. .env.production.example lists deployment settings but is not loaded automatically. Process/hosting settings take precedence. Never expose database or SMTP passwords in browser code, previews, Git, build logs or images. .gitignore and .dockerignore exclude real local env files and certificates. The shipped .env.local contains no private values.

Set GAZAL_ENV=production, GAZAL_PUBLIC_URL to the real HTTPS origin and GAZAL_ALLOWED_HOSTS to the actual hostnames. Set SUPABASE_DB_URL using the backend-only connection URI copied from Supabase Connect. For an IPv4 persistent backend, use the session pooler; do not build a pooler hostname from the project URL. Download the project's CA certificate, mount it read-only and set SUPABASE_SSLROOTCERT to its file path. Production startup rejects missing database credentials, missing CA files, non-HTTPS public URLs and wildcard hosts.

This app uses Supabase PostgreSQL, not Supabase Auth. Supabase's project URL or public API key does not configure the database connection or replace Gazal's authentication. SMTP settings are for invitation emails; configure SMTP_HOST, SMTP_PORT, SMTP_FROM, SMTP_USER and SMTP_PASSWORD if email delivery is required.

## 3. Apply and verify the database
Take a backup before upgrading a real database. Use a migration-owner connection to run `python migrate.py` for the plan and `python migrate.py --apply` to apply numbered migrations with checksums. Fresh installations can instead run supabase/schema.sql in the SQL Editor. The internal schema remains promptto for compatibility and must not be exposed through Supabase's Data API. Migrations currently reach 006_numeric_precision.sql.

Migration 006 changes traction values to NUMERIC(20,2) and reviewed quality to DOUBLE PRECISION. It prevents future PostgreSQL REAL rounding but cannot reconstruct amounts already rounded; reconcile/re-import older affected snapshots against the original billing data. Ingestion now accepts monetary amounts to two decimal places, whole-number user counts, finite nonnegative values and a maximum of 1 trillion per snapshot. Existing source policy and import deduplication remain intact.

Use supabase/runtime_permissions.sql to prepare a restricted gazal_app role. Securely enable its login credentials using your database administration process. Use that role for runtime connections; keep the migration-owner credential separate and unavailable to the web process. Reapply runtime grants after later migrations. The runtime script denies updates/deletes on append-only policy and audit tables. It is a starting least-privilege policy, not tenant RLS: account isolation is enforced by FastAPI.

Run bootstrap_admin.py once on an empty installation to provision the initial administrator, then create business accounts and invite staff. New public registrations cannot create business accounts or grant themselves admin roles. Verify real signup, signin, workspace joining, task submission, policy assessment, spreadsheet import, signed webhook ingestion, remote sessions and email invitation delivery on a staging copy.

## 4. Finish authentication before a public launch
Replace browser sessionStorage bearer tokens with secure HttpOnly, Secure, SameSite cookies and an appropriate CSRF design, or migrate to a verified managed identity integration. Add email ownership verification, a secure password-reset flow, login/registration rate limits, abuse protection and administrator MFA. Current password hashing and role checks are implemented, but those remaining controls are not. Do not assume Supabase Auth is automatically integrated.

## 5. HTTPS, runtime and operations
Terminate TLS at the host or reverse proxy. Trust forwarded headers only from the actual proxy. Use a process supervisor/container restart policy, readiness checks at /readyz and liveness checks at /healthz. Production disables API docs and adds HSTS; host validation, no-sniff, frame denial and no-store API responses are included. A strict Content Security Policy still needs frontend inline-handler cleanup.

Set up database backups and test restoring them. Add error monitoring, secret-redacted logs, alerting and a durable email job queue with retries. Tune connection reuse/pooling and load-test the 30-second presence polling with your expected staff count; each database operation currently opens a connection through the configured endpoint. Test multiple application instances and webhook/correction race conditions in staging. Encrypt retained webhook secrets at rest using a managed secret-encryption key before exposing integrations publicly.

Document notification/email retention and remote-work tracking to staff. Configure retention/deletion rules and audit access. Verify that admins can access only their business accounts and that employees cannot access performance results. Presence and recorded time remain separate from performance calculations; forecasts are not enabled.

## 6. Evidence from this build
Automated API tests and frontend authentication regression checks run locally. PostgreSQL-engine migrations are also checked using PGlite in an isolated test database (separate from Supabase). That checks actual PostgreSQL SQL execution, grants, indexes and precision; it does not validate your hosted network, TLS certificate or database credentials. Browser visual QA and a live Supabase smoke test remain necessary. Docker deployment itself remains unverified.

Official deployment references:
https://supabase.com/docs/guides/database/connecting-to-postgres
https://supabase.com/docs/guides/platform/ssl-enforcement
https://fastapi.tiangolo.com/deployment/docker/

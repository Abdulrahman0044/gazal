# Gazal — Multi-Account MVP

## Current frontend: Next.js

The primary frontend is now in `frontend/` using Next.js App Router, React and TypeScript. Run FastAPI on port 8000 and Next.js on port 3000. See [frontend setup](frontend/README.md). The Python-served HTML below remains a compatibility fallback.

Working web app with SQLite persistence, login, tenant-isolated accounts, projects, employees, task lifecycle, supervisor approvals, dashboards, audit events, and early performance indicators.

## Run locally

```bash
cd gazal
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Visit **http://127.0.0.1:8000**. Interactive API docs: **http://127.0.0.1:8000/docs**.

Demo users (initial password for all: `DemoPass123!`):

- `admin@promptto.local` — global super administrator
- `manager@promptto.local` — Novetiv account administrator
- `employee@promptto.local` — Novetiv employee; Business B project manager

Override the seeded demo password with `PROMPTTO_DEMO_PASSWORD` **before** first initialization. Set `PROMPTTO_DB` to choose the database file. Delete the development database to reinitialize demo data.

## Security / deployment caveats

**Development MVP, not production ready.** The default seed password is public. Do not expose to the internet. Replace demo accounts and bootstrap credentials; add account invitations, email verification, reset-password, MFA, rate limiting, CSRF hardening, stronger employee onboarding, session management, audited employee updates, HTTPS, database migrations, backups and tenant isolation testing before production. For production migrate SQLite to PostgreSQL and consider row-level security. The current employee creation endpoint supports new users; for an existing user it requires their password as a temporary proof-of-ownership, which is **not** appropriate for production and should be replaced with email invitations.

Account membership is verified server-side, including task and project ownership. Employee access to task lists and performance indicators is scoped to their own assignments. No AI predictions or formal employee performance scores are claimed.

## Test

```bash
pytest -q
```

## Milestone 2

Implement secure invitations, task reassignment and deadlines/versioned edits, project-level team permissions, quality rubrics, scoring policies, score appeals, and PostgreSQL migration.

## Version 0.2 — Product traction
New pages: Product traction and Data sources, alongside Overview, Tasks, Projects, Employees and Performance.
Each project has seven widgets. CSV/XLSX uploads are validated and previewed before explicit commit. Columns: date (YYYY-MM-DD text), metric, value. Supported keys: total_users, active_users (DAU), paying_customers (current paying customers), billed, collected, refunds, mrr. Amounts are NGN and daily periods use Africa/Lagos. Flow widgets sum daily totals over the selected period; user and MRR widgets show the latest snapshot in that period. Unavailable metrics are null, never zero. Billed and collected amounts remain separate.

A widget has one primary source, spreadsheet or webhook. Switching to webhook rotates its secret; secrets are returned once and not exposed by list endpoints. Existing dated snapshots remain history. Daily values replace existing values for the same metric/date. Imports are atomic and repeat commits do not add data. A preview is bound to its contributor, account and project. Team leads have read-only traction access; employees and HR have no traction access.

Webhook payload: {"event_id":"unique-event","date":"2026-10-12","metric":"total_users","value":100}. Send the returned endpoint an HMAC-SHA256 hex signature of timestamp + "." + the exact raw JSON bytes, using the returned secret, in X-PromptTo-Signature. X-PromptTo-Timestamp is Unix seconds, within five minutes. Resend failed requests with a fresh timestamp and signature, retaining the event_id. Duplicate IDs are ignored. Payloads represent absolute daily snapshots, not individual registrations or payment increments; product backends must aggregate first. Same-day corrections require new event IDs.

Run: python -m uvicorn app:app --reload. Tests: python -m pytest tests -q.
This remains a development MVP. Production needs HTTPS, secret encryption at rest, request rate limits, monitoring, secure invitations and deployment configuration. Scoring calibration and predictions are still unavailable. No billing processing is performed by Gazal.

## Version 0.3 — Supabase PostgreSQL and pilot scoring
The backend selects Supabase PostgreSQL when SUPABASE_DB_URL is set. Otherwise it uses SQLite for development. Supabase Auth is not integrated; existing FastAPI authentication and account permissions remain in place. Credentials are backend-only; never put a database URL in browser JavaScript.

1. Install requirements and set `SUPABASE_DB_URL` in the backend environment. For local development, put the PostgreSQL connection URI from Supabase's Connect panel in `.env.local`; do not commit that file. Run `python migrate.py --apply` to apply all ordered SQL files in `supabase/` and create the isolated `promptto` schema. Do not add `promptto` to exposed Data API schemas. This creates the schema and tables but does not copy existing SQLite records.
2. In your backend host's secret environment settings, set SUPABASE_DB_URL to the connection URI from Supabase's Connect panel. Prefer the session pooler for this persistent Python backend on IPv4. Use a backend-only database credential. The schema isolation is not database-level tenant RLS: FastAPI enforces tenant access. Do not give users direct database credentials. A narrowly granted backend login should replace the project-owner login before public deployment.
3. SSL is required. For certificate verification, also set SUPABASE_SSLROOTCERT to the downloaded Supabase root certificate's local path. Prepared statements are disabled for pooler compatibility.
4. After migrations succeed, run `python bootstrap_admin.py` to create the first administrator using a hidden password prompt. Cloud mode never seeds demo users. Start `python -m uvicorn app:app`. After login, GET /api/system/database confirms the selected backend and a successful database query. No actual Supabase connection has been verified in the delivered environment.
5. Create accounts/projects/memberships through the app. The original SQLite file remains unchanged when cloud mode is selected. Migration of existing real records requires a separate reviewed data-transfer step.

Performance page now shows component scores, evidence counts and the policy. Scoring policy: SCORING_POLICY.md. POST /api/accounts/{account}/tasks/{task}/score-exception accepts adjusted_due, excluded and a reason; account admins can use it, with audit history retained. Predictions are deliberately disabled pending immutable snapshots and validation.


## Gazal branding and Supabase project
System name: Gazal. Organization: PromptTo. Configured public project URL: https://xjezlymsqusvuzrvbaru.supabase.co. Version: 0.3.1.
The URL identifies the project but does not authorize database access. SUPABASE_DB_URL still must be set securely on the backend host. During non-production local development, the backend loads `.env.local` and `.env` from the project directory; process environment variables take precedence. Production reads secrets from the hosting environment and does not load those files.
For compatibility, the existing promptto database schema, local database filename, demo email addresses and X-PromptTo webhook headers remain valid. GAZAL_DB overrides the legacy PROMPTTO_DB local setting. Existing records and integrations do not need renaming.


## Version 0.4 — team onboarding, inbox and modern UI
Routes: /employee/login and /admin/login. Both use the same secure user store; the admin portal checks management access and all API routes enforce account roles. No public account self-registration: users join via a seven-day, single-use invitation. Existing users must authenticate as the invited email; accepting an invitation never resets their password or promotes an existing membership. Employees can belong to accounts and specific projects.

Administrators open Employees → Invite employee, choose role and optional project, then share the generated link. New users create a password of at least 14 characters. The account/project membership is created at acceptance. Invitations use hashed tokens; their links carry tokens in the fragment rather than the query string. Invite-list output never reveals token hashes or live tokens.

Apply supabase/002_invitations_notifications.sql after 001_initial.sql for new installs, or as the upgrade for an already migrated database. Configure GAZAL_PUBLIC_URL and SMTP_HOST / SMTP_PORT / SMTP_FROM / SMTP_USER / SMTP_PASSWORD in backend secrets to deliver invitations via STARTTLS. Invitation creation returns pending when email delivery is scheduled; the invitation list API reports sent or failed after the attempt. Email delivery is attempted once; admins can share the link or generate a new invitation after failure. SMTP delivery and a live Supabase connection remain untested without provider credentials.

Notification inbox: new assignment, project invitation for existing account members, work ready for manager review, approval/revision decisions, and due-task reminders. Inbox unread count refreshes once per minute while signed in. Notifications are visible only to their recipient and authorized account. Managers can click Send due-task reminders in Notifications; reminders deduplicate per task/date. Automatic scheduling, background task email alerts, mobile push notifications and password-reset emails are not implemented in this release. Staff should use the in-app inbox for task updates.

The dashboard now uses a light sidebar, indigo accents, rounded cards, a workspace welcome panel, clearer tables and responsive navigation. Existing data/widget configuration and scoring policy are preserved.

## Version 0.5 — admin-only performance, dropdown inbox and schema package
Performance visibility now requires account_admin or super_admin, enforced on all score/policy/legacy performance endpoints. Score exceptions are also admin-only. Employees, project managers, team leads and HR cannot view performance results.
Notifications now open as a header dropdown; there is no Notifications page. Inbox ownership checks remain unchanged.
Complete fresh-install SQL: supabase/schema.sql. Ordered upgrade migrations: 001_initial.sql, 002_invitations_notifications.sql, 003_backend_management.sql. Use python migrate.py to review and --apply to execute with backend credentials. API_GUIDE.md documents all implemented routes. Added project membership management and invitation revocation.

## Version 0.6 — integrated schema and live data controls
schema_core.sql is now the single table/index definition used by local backend initialization and embedded verbatim in the Supabase SQL export. Schema creation has been removed from individual feature modules. In Supabase mode, startup checks all expected tables and refuses an incomplete schema with migration instructions instead of silently creating missing cloud tables. Apply migrations before starting the backend.

Projects → View members now loads the real project-members API; authorized managers can add/remove existing account members. Employees → Invitations loads invitation status, email status and revocation state; administrators can revoke pending invitations from the interface. Tasks → Scoring exception connects to the audited admin-only exception endpoint. Notification dropdown, task workflow, traction imports and scores use backend API records.

The downloadable app is the backend-connected version. The separate preview remains an explicitly labeled sample-data demonstration. No live Supabase connection or remote migration has been performed without a configured database credential.

## Version 0.7 — mathematical policy system
Apply supabase/004_policy_system.sql (or ordered migrate.py --apply). The shared schema now contains 25 application tables. New admin-only Scoring policies page: publish weighted policies, inspect version history and capture/view immutable score snapshots.
Workflow: publish policy → create assigned task → Tasks / Set criteria → employee submits evidence and work → admin uses Approve to open the policy assessment. Bound rubric tasks require the verified assessment; the legacy approval API returns 409. Requirements and documentation criteria remain visible to the assignee, while scores, policies, NLP suggestions and assessments are admin-only.
NLP currently uses lexical evidence matching only. Reviewers verify coverage and correctness; external AI models, semantic embeddings and trained deadline forecasting are not enabled. See SCORING_POLICY.md for the implemented formula and limitations.


## Version 0.7.1 — policy controls within Performance
Scoring policy is now an admin-only tab inside Performance. The standalone policy navigation/page and displayed formulas are removed. The frontend loads a safe policy summary (name, version and history) rather than calculation settings. Publishing a named version from the UI retains the current server-side rules. Numerical policy configuration and quality calculations stay in the backend. Task exceptions are managed in the Performance policy tab; task requirement and evidence review remain normal work controls. No schema migration is needed for this UI/API change.

## Version 0.8 — visible remote-work module
Apply supabase/005_remote_work.sql (or the ordered migration runner) before starting Supabase mode. The shared schema now contains 31 application tables.
My Workday: start/end a session, select your own open task, set working/meeting/break/away, submit priorities/achievements/blockers, inspect recorded sessions and request time corrections. A partial unique index guarantees one active session per account/user; repeated starts return that session. Availability and task switches are recorded as server-stamped events. Refreshes and missed heartbeats do not close sessions.
Remote Team: account admin/super admin views account members' availability, current task, elapsed session, last connection and blockers; opens session/task-time breakdowns and reviews corrections. Connection heartbeats are sent roughly every 30 seconds while the page is visible; timers update every second in the browser. Connected means last heartbeat within 90 seconds; recently disconnected is within 300 seconds; later is offline; never received is unknown. Browser throttling/suspension can delay updates. These states never affect scores or deduct time.
Daily reports use Africa/Lagos calendar boundaries and split overnight sessions. Recorded duration includes all availability states; working/break/task time is separately derived from events. Approved time corrections preserve original timestamps and show an adjusted duration separately; they do not rewrite original task/status breakdowns. Corrections require a reason, a different administrator's decision, a past interval of at most 48 hours and no overlap with other sessions. Audit history includes session events, daily-update revisions and correction decisions.
Blocker changes notify account admins in the existing dropdown inbox. Reports and corrections are in-app; automated end-of-day sessions, external computer monitoring, screenshots, keystroke capture and remote-work email/push alerts are not implemented.
Local automated tests cover ownership, cross-account access, multiple concurrent starts, lost connections, task selection, overnight duration, day-boundary reports, blocker alerts and correction history. Supabase/PostgreSQL and browser visual testing remain pending in this environment.

## Version 0.8.1 — dedicated signup and signin
Sign in: /signin, /employee/login, /admin/login. Sign up: /signup, /employee/signup, /admin/signup. Invitation links at /join also open the dedicated signup design. All pages use static/auth.html, auth.css and auth.js with a responsive split layout.
Sign-up validates a share link/code, displays the invited name/email/account/project, requires matching passwords of at least 14 characters, then calls the existing single-use invitation acceptance API. Admin sign-up requires an administrator-role invitation; users cannot select their own access role. Existing invited users sign in with their existing credentials. The backend admin portal rejects users without management roles. Public unauthenticated registration, forgotten-password email delivery and SSO remain unimplemented. Access/password recovery assistance directs users to their workspace administrator; contact workflow is manual.
The app redirects unsigned-in visitors to /signin and opens the workspace after successful authentication. Sign-out clears and revokes the session. These changes require no new database migration. The separate signup/signin previews use sample API responses and do not create real accounts.

## Version 0.8.2 — signup routing fix
Create an account points to /signup. /create-account redirects to /signup. Standalone previews switch between signin/signup within the same document, so they do not depend on opening sibling HTML files. The continue-to-signin button also stays within the preview. Real signup still requires a valid invitation, and real signin opens the backend-connected workspace. Frontend regression check: node tests/frontend/test_auth.cjs.

## Version 0.9 — one shared auth flow and 3D landing
Home / now serves the public landing page with a CSS 3D cube, layered workspace cards, responsive feature sections and role-entry buttons. Admin sign in and Employee sign in both link to /signin; roles are determined by backend memberships after login. Workspace lives at /app.
Shared signup /signup immediately shows name, email, password and confirmation. POST /api/signup creates an ordinary user with no business memberships or admin privileges. After login, unassigned users see a join-workspace form. Invitations remain optional at signup and establish authorized business/project membership. First super admin is still provisioned through bootstrap_admin.py; later management roles are assigned through authorized invitations.
Legacy employee/admin login URLs redirect to /signin; legacy signup URLs redirect to /signup. The shared login API no longer uses portal selection. Legacy portal fields are ignored, while protected endpoint permissions remain enforced. No schema migration is needed. Email verification, password-reset delivery, registration rate limiting and production deployment remain future hardening work.
Landing/signin/signup previews use sample responses only. No real account is created by a preview.


## Version 0.10 — GAZAL. branding, environment setup and precision fixes
A shared outlined SVG wordmark appears across landing, auth, workspace, mobile and illustrated logo surfaces. SVG assets have no external font dependency; dark and light variants are supplied in static/brand.
.env.local now loads automatically for development with process settings taking precedence. It contains development defaults and blank credentials. .env.example and .env.production.example document settings. Production never loads .env.local; startup validates the database URL, certificate path, HTTPS public URL and explicit allowed hosts. .gitignore and .dockerignore protect private configuration.
Apply migration 006_numeric_precision.sql for accurate monetary storage and fractional reviewed quality. The complete schema export and all six migrations were executed successfully in an isolated PostgreSQL engine (PGlite), including repeats, role privileges and precision checks. This is separate from live Supabase verification.
Production assets: Dockerfile, requirements.lock.txt, health/readiness routes and PRODUCTION_GUIDE.md. The guide identifies remaining work before public launch. Authentication, email and deployed infrastructure are not fully production-hardened yet.
Run locally: pip install -r requirements.lock.txt; python -m uvicorn app:app --reload. PostgreSQL schema regression check: npm ci then npm run test:schema. Frontend regression: npm run test:frontend.

## Version 0.10.1 — responsive layout review
Landing: simplified contained 3D illustration on phones; wrapping CTAs; smaller narrow-screen header; tablet decorative overflow containment. Authentication: single-column layout below 900px; safe wrapping; 16px mobile fields; 44px touch targets; viewport-aware height. Workspace: mobile navigation below 760px; contained horizontally scrolling tables; responsive metrics and forms; constrained notification dropdowns/dialogs; wrapped long text and readable task controls.
Standalone landing preview now scopes authentication CSS to its modal so auth styles do not alter landing-page styles. The separate responsive viewer renders sample pages at 320, 360, 390, 414, 768, 820, 1024, 1280 and 1440px widths and checks overflow in the user's browser. Those widths are review targets, not proof of cross-browser certification.
CSS structure/breakpoint safeguards, backend tests and frontend auth regression checks pass. Actual automated browser visual tests, Chrome/Firefox/Safari checks and real iOS/Android keyboard/zoom verification remain pending due to unavailable supported browser QA in this environment.

# Gazal backend v0.5

## Install and schema
Install requirements. For a fresh Supabase database, run supabase/schema.sql in the Supabase SQL Editor. Alternatively run the ordered migration runner: `python migrate.py` prints a plan; `python migrate.py --apply` applies 001–003 atomically after SUPABASE_DB_URL is configured securely. The runner records migration filenames and checksums, skips previously applied versions and rejects modified versions. Existing installations using SQL Editor can run only unapplied numbered migrations; all migrations use CREATE IF NOT EXISTS and preserve application records. Do not modify previously tracked migrations.

Tables cover users, accounts, memberships, projects, tasks, task events, reviews, sessions, traction sources/values/imports/receipts, score exceptions and their audit events, project members, invitations and revocations, notification inboxes and reminder receipts. Indexed queries support account-scoped task, notification, review and analytics access.

Gazal retains the internal promptto schema. It is backend-only: API roles are denied schema/table access. Do not expose it through Supabase's Data API. Tenant access is enforced by FastAPI rather than tenant RLS; keep database credentials server-side. Supabase Auth is not integrated. After migration use `python bootstrap_admin.py` and `python -m uvicorn app:app`. Demo accounts are created only in local SQLite mode.

## Authentication
`POST /api/login` takes email, password and portal (`admin`, `employee`; legacy `any` remains supported). The admin portal checks management membership. Use the returned token as `Authorization: Bearer <token>` for protected routes. `POST /api/logout` revokes the current session; `GET /api/me` returns identity.

Employee page: /employee/login. Admin page: /admin/login. Invitation page: /join#token=... . Invitation onboarding requires a new password of at least 14 characters. Existing accounts must authenticate as the invited email; invitation acceptance cannot reset an existing password or promote an existing membership.

## Accounts and work
GET/POST /api/accounts — authorized accounts; super admin creates accounts.
GET/POST /api/accounts/{a}/employees — member list and legacy member creation; use invitations for onboarding.
GET/POST /api/accounts/{a}/projects — list and create projects.
GET/POST /api/accounts/{a}/tasks — scoped task list/create; employees see their assignments.
POST /api/accounts/{a}/tasks/{t}/transition — status and notes; transition rules and assignee access enforced.
POST /api/accounts/{a}/tasks/{t}/review — decision, quality, notes; manager approval/revision flow.
GET /api/accounts/{a}/tasks/{t}/events — task audit history.
GET /api/accounts/{a}/dashboard — authorized summary.

## Project members and invitations
GET /api/accounts/{a}/projects/{p}/members — staff see their own membership; management sees project members.
POST /api/accounts/{a}/projects/{p}/members — user_id; account admin/project manager/team lead can add an active account member.
DELETE /api/accounts/{a}/projects/{p}/members/{user} — account admin/project manager removes membership. Existing tasks remain assigned.
POST /api/accounts/{a}/invitations — account admin; email, name, role, optional project_id. Returns one-time share link and email delivery status.
GET /api/accounts/{a}/invitations — account admin; invitation metadata and email delivery status, no secret tokens.
POST /api/accounts/{a}/invitations/{i}/revoke — account admin; prevents future acceptance. Accepted invitations cannot be revoked.
POST /api/invitations/inspect — token; displays onboarding information for a valid invite.
POST /api/invitations/accept — token, optional password; a valid invite establishes account/project membership.

SMTP invitation delivery needs GAZAL_PUBLIC_URL plus SMTP settings. It is attempted once. Task alerts are in-app, not email or mobile push. Automatic reminder scheduling is not implemented.

## Notification dropdown
GET /api/accounts/{a}/notifications — recipient-only inbox, up to 100 newest records.
POST /api/accounts/{a}/notifications/{n}/read — only that recipient can mark a record read.
POST /api/accounts/{a}/task-reminders — management triggers due-task reminders; duplicate tasks are skipped per calendar date.
Header button opens/closes the inbox dropdown. Outside click and Escape close it. There is no separate Notifications page. Unread counts refresh every minute while logged in.

## Admin-only performance
Account admin or super admin ONLY:
GET /api/accounts/{a}/performance — legacy performance indicators.
GET /api/accounts/{a}/scores — current pilot score and components.
GET /api/accounts/{a}/scoring-policy — current policy.
POST /api/accounts/{a}/tasks/{t}/score-exception — adjusted_due, excluded, reason (minimum ten characters).
Employees, project managers, team leads and HR receive HTTP 403 for all performance routes. UI navigation also hides Performance. Notification and normal task access remain role-scoped. Forecasts remain disabled pending validated history.

## Traction
GET /api/traction/definitions — metric keys and aggregation definitions.
GET /api/accounts/{a}/projects/{p}/traction?start=YYYY-MM-DD&end=YYYY-MM-DD — values and history.
GET/POST /api/accounts/{a}/projects/{p}/sources — configure metric and mode.
POST /api/accounts/{a}/projects/{p}/imports/preview — multipart file (CSV/XLSX).
POST /api/accounts/{a}/projects/{p}/imports/{i}/commit — commit validated import.
POST /api/webhooks/{source} — signed, timestamped, deduplicated daily snapshots.
Traction read roles: account admin/project manager/team lead and super admin; writes: account admin/project manager and super admin. See README for webhook signature format.

## Verification
Run `python -m pytest tests -q`. OpenAPI is available at /docs when the backend runs. GET /api/system/database requires super admin and confirms backend selection and a query, without exposing credentials. The shipped version has been tested locally; live Supabase, SMTP and browser visual verification are pending.

## v0.6 schema/frontend integration
schema_core.sql is the canonical application DDL. The local backend initializes from it. In Supabase mode the backend checks the expected table set before route registration; incomplete schemas require running migrations first. The complete supabase/schema.sql embeds the same DDL.
The Projects page exposes project-member list/add/remove operations, Employees exposes invitation state and revocation, and the Tasks page exposes admin-only scoring exceptions. These controls call the documented backend endpoints and render returned database records. The sample preview is independent of live data.

## Policy system v0.7
Admin-only GET/POST /api/accounts/{a}/policies: inspect history or publish {name, weights:{quality,on_time,completion}, nlp_weight, minimum_approved, minimum_due, reason}. Weights sum to 100; λ is at most .25; minimum evidence thresholds are at least five.
POST /api/accounts/{a}/tasks/{t}/rubric: admin freezes {requirements:[{id,text,weight}],documentation:[{id,text,weight}]} before work starts. GET rubric is available to authorized task viewers.
GET/POST /api/accounts/{a}/tasks/{t}/evidence: assignee or authorized management reads/adds {text}. Closed tasks reject new evidence.
GET /api/accounts/{a}/tasks/{t}/nlp-suggestions: admin-only lexical evidence suggestions.
POST /api/accounts/{a}/tasks/{t}/policy-assessment: admin-only; correctness, acceptance_human, validation, documentation_human (all 0–1); requirements/documentation maps keyed by criterion ID, each containing status (0/.5/1) and evidence_id; notes. Calculates quality, stores the assessment and approves a submitted task atomically. GET returns the latest assessment to admins only.
GET/POST /api/accounts/{a}/score-snapshots: admin-only immutable aggregate score history/manual capture.
Supabase migration 004 adds policy_versions, account_policy, task_rubrics, task_evidence, policy_assessments and score_snapshots. The live cloud migration and email service remain unverified without configured credentials.

## Remote work v0.8
GET /api/accounts/{a}/workday — recipient-owned active/recent sessions, today's update, corrections and daily summary.
POST /api/accounts/{a}/work-sessions — {task_id?}; starts or returns the existing active session. Task must be your own open assignment.
POST /api/accounts/{a}/work-sessions/{s}/status — {status,task_id?,note?}; server-stamped, optimistic update. Valid status: working, meeting, break, away.
POST /api/accounts/{a}/work-sessions/{s}/end — idempotent session ending.
POST /api/accounts/{a}/presence — heartbeat for authenticated user/account. No task/keyboard activity is collected.
POST /api/accounts/{a}/daily-updates — {priorities,achievements,blockers}; today's Lagos-date update, with append-only revisions and account-admin blocker notifications.
GET /api/accounts/{a}/work-report?day=YYYY-MM-DD&employee=... — self report by default; only account admin/super admin may request another member's report. Splits recorded/adjusted time at Lagos midnight.
GET /api/accounts/{a}/remote-team — admin-only presence and workday overview.
GET /api/accounts/{a}/remote-team/{employee}/sessions — admin-only detailed session summaries.
POST /api/accounts/{a}/time-corrections — {session_id,requested_start,requested_end,reason}; timezone-aware timestamps, past interval up to 48 hours. Own closed sessions only; one pending request per session.
GET /api/accounts/{a}/time-corrections — own requests; admins see account requests.
POST /api/accounts/{a}/time-corrections/{id}/decision — admin-only {decision:approved|rejected,notes}; cannot approve your own correction or overlap another session. Original records remain intact.
Migration 005 adds work_sessions, work_session_events, employee_presence, daily_updates, daily_update_events and time_corrections. Remote work does not feed the performance formula. All new endpoints require authenticated account access.

## Dedicated authentication pages v0.8.1
GET /signin, /employee/login, /admin/login — dedicated signin UI, using POST /api/login.
GET /signup, /employee/signup, /admin/signup, /join — dedicated invitation-based signup UI. Signup calls POST /api/invitations/inspect, then /api/invitations/accept; existing accounts sign in before acceptance. Inspect now returns the assigned invitation role. A caller cannot override the role at registration.
No schema upgrade is needed. First super administrator remains created through bootstrap_admin.py. Subsequent administrators must be invited with a suitable role. Password-reset email and open self-registration endpoints are not implemented.

## Shared authentication and landing v0.9
GET / — public 3D landing page. Both role-entry CTAs open /signin.
GET /app — workspace shell; frontend redirects unsigned-in visitors to shared signin.
GET /signin, /signup — single signin/signup UI with no employee/admin selector.
POST /api/signup — {name,email,password}; creates only a non-super user, with no memberships. Duplicate normalized email returns 409. Email/name validation and password length are enforced.
POST /api/login — {email,password}; all roles use the same endpoint. Membership permissions determine protected access after login. Legacy portal fields do not grant privileges.
Legacy /admin/login and /employee/login redirect to /signin. /admin/signup, /employee/signup and /create-account redirect to /signup. /join supports existing invitation links. New users without memberships join their workspace using an invitation after signin.

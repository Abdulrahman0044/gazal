# GAZAL. Next.js frontend

Next.js App Router + React + TypeScript. Landing, sign-in, sign-up and invitation pages are React components. The workspace is a React shell with the existing interaction controller isolated in `lib/workspace-runtime.js` to preserve all business flows during migration. That controller still renders dynamic tables/forms imperatively; it is not yet a full React component rewrite. It cancels polling, pending requests and document listeners on unmount.

## Development

Requires Node.js 20.9+ and the Python backend dependencies.

From the repository root, start FastAPI:

```sh
python3 -m uvicorn app:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Open http://localhost:3000. Routes: `/`, `/signin`, `/signup`, `/join#token=...`, `/app`. Admin and employee login links both use `/signin`; access is enforced by FastAPI. The old Python-served frontend remains a compatibility fallback on port 8000. Use port 3000 for the new frontend.

## Verification and production

```sh
npm test
npm run typecheck
npm run build
# Requires Python backend dependencies; reserves ports 3000 and 8000 temporarily.
npm run test:integration
npm start
```

Deploy Next.js as a Node service separately from FastAPI. `GAZAL_BACKEND_URL` is server-only and is compiled into the API rewrite at build time; rebuild if the backend origin changes. Browser requests stay on `/api/*` and are proxied to FastAPI, including authorization, uploads and errors. Never place database passwords or service-role keys in `NEXT_PUBLIC_*` variables.

Configure FastAPI `GAZAL_PUBLIC_URL` with the public Next.js origin so invitations open the new frontend. Include the backend host in `GAZAL_ALLOWED_HOSTS` (for Docker, `backend`) and apply the backend production requirements in `../PRODUCTION_GUIDE.md`. Provision the production database, HTTPS, SMTP, backups and secure session improvements before public use. Backend scoring remains private; no AI model or performance prediction is added by this UI migration.

The frontend Dockerfile builds a standalone Next.js service. Pass `GAZAL_BACKEND_URL` as a build argument. The existing root Dockerfile runs only FastAPI. Do not use static export: API proxying requires a server.

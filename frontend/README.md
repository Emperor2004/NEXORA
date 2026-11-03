# NEXORA frontend

React and TypeScript client for the existing local FastAPI API. It provides a
discovery request, dashboard, opportunity/source/evidence review, and manual
application status tracking. It does not submit external applications.

## Run

```powershell
Copy-Item .env.example .env.local
npm install
npm run dev
```

The API base defaults to `http://127.0.0.1:8000`; set
`VITE_API_BASE_URL` in `.env.local` to change it. Do not put an API token in a
Vite environment variable. Enter a configured bearer token on Settings; the
client retains it in memory only until the tab reloads.

Use `npm run build` for the TypeScript production build and `npm test` for
frontend unit tests.

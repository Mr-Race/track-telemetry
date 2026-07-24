# Track Telemetry Dashboard

React + Vite + TypeScript SPA for the Track Telemetry Platform (see
the repo root `README.md`). Deployed to Azure Static Web Apps
(`swa-track-telemetry-dashboard`); calls `function_app.py`'s API
directly (no linked backend, to stay on the SWA free tier).

## Local development

```
npm install
npm run dev
```

Vite proxies `/api/*` to `http://localhost:7071` (see
`vite.config.ts`), so run the Function app locally alongside this
(`func start` from the repo root) to get real API responses. Auth
config (`VITE_MSAL_*`, `VITE_API_SCOPE`) lives in `.env`, committed —
it's a public SPA client ID + tenant authority, not a secret.

## Build & deploy

```
npm run build
npx @azure/static-web-apps-cli deploy ./dist \
  --deployment-token "$(az staticwebapp secrets list -n swa-track-telemetry-dashboard -g Track-telemetry --query 'properties.apiKey' -o tsv)" \
  --env production
```

`.env.production` points `VITE_API_BASE` at the live Function App —
redeploy the Function app first if the API changed, since there's no
linked backend to auto-sync.

## Layout

- `src/pages/` - route-level pages (session list/detail, tracks,
  consumables, events, dashboard home, landing)
- `src/api/client.ts` - typed fetch wrappers for every API endpoint,
  MSAL bearer-token attachment
- `src/authConfig.ts` / `src/msalInstance.ts` - MSAL (Entra ID) setup

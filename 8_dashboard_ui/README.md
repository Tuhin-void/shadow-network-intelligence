# Shadow Network Intelligence — Dashboard (`8_dashboard_ui`)

The operator-facing dashboard for the GraphRAG investigation platform.
React 19 + TypeScript + Vite 8 + TailwindCSS + Cytoscape + Framer Motion.

This module is one of three independently runnable surfaces in the
project — see the root `README.md` for the platform-level overview and
the `10_research/` directory for design rationale.

## Role in the platform

The dashboard is a **thin operator UI** over the orchestrator API at
`http://localhost:8000/api/v1`. It does not implement retrieval,
benchmarking, or ingestion logic — every action issues an HTTP call
against the FastAPI orchestrator (`4_orchestrator_api`). All
state-bearing logic lives server-side; the UI is responsible only for
visualizing the platform's truth.

Major routes:

- `/` — Command Center (active case, operations panel, recent sessions)
- `/investigate` — Manual Workstation (graph canvas, suspect rail,
  streaming timeline, evidence panel, cognitive reasoning)
- `/benchmark` — Shootout (Scenario walkthrough · Evidence panel ·
  live `/benchmark/run/stream` console)
- `/sources` — Activation lifecycle, uploads, schema detection,
  ecosystem promotion, readiness gates

Every route is wrapped in an `ErrorBoundary` so a render error in one
view never blacks out the navigation chrome.

## Running locally

```bash
# From the repo root — install Python + Node deps
make install-all

# Start the backend (terminal 1)
make demo-backend          # http://localhost:8000

# Start this dashboard (terminal 2)
make dev-frontend          # http://localhost:5173
```

Open `http://localhost:5173`. The TopBar status pill flips to `LIVE`
once the orchestrator responds. The default landing is the deliberate
"Launch Sample Fraud Ecosystem" empty state — click it to activate and
the rest of the UI lights up.

## Environment

The dashboard reads two Vite build-time variables (both optional):

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | orchestrator base URL |
| `VITE_API_PREFIX` | `/api/v1` | API path prefix |

Override these in `8_dashboard_ui/.env` for non-localhost deploys
(Vite reads them at build time, not runtime — restart `npm run dev`
after editing).

## Requirements

- **Node.js 18+** (enforced via `package.json` `engines` field)
- npm 9+ (or compatible package manager)
- The orchestrator API running at the configured `VITE_API_BASE_URL`

## Scripts

```bash
npm run dev       # Vite dev server with HMR
npm run build     # tsc -b && vite build → dist/
npm run preview   # Serve the production build locally
npm run lint      # eslint against the source tree
```

`make type-check` at the repo root runs `tsc --noEmit` over this
package for CI-style type validation.

## Architecture notes

- **State:** `zustand` (`src/store/intel-store.ts`) with selective
  persistence. No Redux, no React Context for app state.
- **API layer:** `src/lib/api-client.ts` is the single point of
  contact with the orchestrator; downstream adapters reshape API
  responses into view-model types in `src/lib/adapters/`.
- **Graph rendering:** Cytoscape via `react-cytoscapejs`. Atmosphere
  effects (Worldspace) persist across route changes so layout state
  survives navigation.
- **Streaming:** Server-Sent Events for `/investigate/stream`,
  `/investigate/deep/stream`, `/benchmark/run/stream`, and the demo
  presets. Parsed in `src/lib/sse-client.ts` with explicit
  per-event-type handlers.
- **Error containment:** Per-route `ErrorBoundary` (see
  `src/components/shared/ErrorBoundary.tsx`).

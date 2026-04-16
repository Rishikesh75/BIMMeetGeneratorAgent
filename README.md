# BIM Meet Generator Agent

Turn construction and design **meeting notes** into **IFC4** building models you can open in standard BIM tools—without manually modeling every wall, space, and opening from scratch.

---

## Overview: the problem

On AEC (architecture, engineering, construction) projects, important decisions live in **meetings**: room names, structural intent, rough dimensions, and material direction. That information is usually captured as **unstructured text** (transcripts, notes, bullet lists).

Meanwhile, downstream workflows expect **structured BIM data**—often as **IFC** (Industry Foundation Classes), an open exchange format used across authoring and coordination tools.

The gap is manual and slow: someone must interpret notes and rebuild geometry and semantics in a model. This project targets that gap by **automating extraction from text** and **emitting a starter IFC** aligned with what was discussed.

---

## Proposed solution

1. **Ingest** meeting notes (and optional title/date) as the single source of truth.
2. **Extract** a structured inventory of building elements using a large language model: spaces, walls, doors, windows, columns, beams, slabs, plus project/building metadata. Missing details are filled with **reasonable defaults** where the model can infer them.
3. **Generate** an **IFC4**-oriented text file from that structured data so teams get a **downloadable `.ifc`** for review or further editing.
4. **Track** work as **async jobs** with **step-by-step progress**, persisted history, and **download** when complete.

The UI (`gmeet-bim`) is positioned as a **Google Meet–oriented** experience (paste notes from a meet), but the pipeline is **note-driven**: any project text that describes the building can be used.

---

## Architecture

High-level data flow:

```mermaid
flowchart LR
  subgraph client [Web client]
    UI[gmeet-bim React app]
  end
  subgraph api [API server]
    Routes[Express BIM routes]
    LLM[Gemini extraction]
    IFC[IFC text generation]
  end
  subgraph data [Persistence]
    PG[(PostgreSQL)]
  end
  UI -->|POST /api/bim/generate| Routes
  UI -->|GET job status / list / download| Routes
  Routes -->|async job| LLM
  LLM --> IFC
  Routes --> PG
  IFC --> PG
```

### Components

| Layer | Role |
|--------|------|
| **`artifacts/gmeet-bim`** | React + Vite frontend: generator page (notes, title, date), live processing steps, job history, IFC download. Uses generated API client hooks (TanStack Query). |
| **`artifacts/api-server`** | Express 5 server. Mounts routes under `/api`. BIM endpoints create jobs, run background processing, expose status and file download. |
| **`lib/api-spec`** | OpenAPI 3.1 contract; **Orval** codegen drives shared types and clients. |
| **`lib/api-zod`** | Zod schemas generated from the spec (validation on the server). |
| **`lib/api-client-react`** | Generated React Query hooks + fetch client for the frontend. |
| **`lib/db`** | Drizzle ORM + PostgreSQL; `bim_jobs` stores notes, status, progress, steps, extracted element counts, and generated IFC content. |
| **`lib/integrations-openai-ai-server`** (package **`@workspace/integrations-gemini-server`**) | **Google Gemini** via the [OpenAI-compatible HTTP API](https://ai.google.dev/gemini-api/docs/openai). Set **`GEMINI_API_KEY`**, **`GEMINI_BASE_URL`**, and optional **`BIM_EXTRACTION_MODEL`**. |

### BIM job pipeline (server)

When `POST /api/bim/generate` runs:

1. A row is inserted with status **pending** and a fixed list of **named steps** (parsing, AI extraction, IFC schema build, file write).
2. Processing continues **asynchronously**; the HTTP response returns immediately with a **`jobId`**.
3. The worker updates **progress**, **current step**, and per-step status as it advances.
4. On success: **IFC text** is stored, **file size** and **extracted element counts** are saved, status becomes **completed**.
5. On failure: status **failed** with an **error message**.

The client polls **`GET /api/bim/jobs/:jobId`** (or lists jobs) until completion, then uses **`GET /api/bim/jobs/:jobId/download`** for the `.ifc` file.

### Repository layout

```text
├── artifacts/
│   ├── api-server/          # Express API (BIM routes, IFC generation)
│   └── gmeet-bim/           # React + Vite UI
├── lib/
│   ├── api-spec/            # openapi.yaml + Orval config
│   ├── api-zod/             # Generated Zod schemas
│   ├── api-client-react/    # Generated hooks + client
│   ├── db/                  # Drizzle schema, DB connection
│   └── integrations*/       # Gemini client (`@workspace/integrations-gemini-server`) and related
├── scripts/                 # Workspace utility scripts
├── pnpm-workspace.yaml
└── package.json             # Root scripts (build, typecheck)
```

---

## API summary

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/bim/generate` | Start a job (`meetingNotes`, optional `meetingTitle`, `meetingDate`) |
| `GET` | `/api/bim/jobs` | List jobs (newest-oriented list in handler) |
| `GET` | `/api/bim/jobs/:jobId` | Poll status, progress, steps, extracted counts |
| `GET` | `/api/bim/jobs/:jobId/download` | Download completed `.ifc` |
| `GET` | `/api/healthz` | Health check |

See `lib/api-spec/openapi.yaml` for the full contract.

---

## Tech stack

- **Runtime**: Node.js 24, **pnpm** workspaces, **TypeScript** 5.9  
- **API**: Express 5, **Zod** validation  
- **Data**: PostgreSQL, **Drizzle ORM**  
- **Frontend**: React, Vite, TanStack Query, Tailwind/shadcn-style UI  
- **Contract**: OpenAPI → Orval → shared Zod + React client  
- **LLM**: **Google Gemini** only — [OpenAI-compatible endpoint](https://ai.google.dev/gemini-api/docs/openai), keys from [Google AI Studio](https://aistudio.google.com/apikey). Env: **`GEMINI_API_KEY`**, **`GEMINI_BASE_URL`**, optional **`BIM_EXTRACTION_MODEL`**.

---

## Development

- **Install**: `pnpm install` (this repo expects **pnpm**, not npm/yarn).  
- **Typecheck**: `pnpm run typecheck` from the repo root (uses TypeScript project references).  
- **Build**: `pnpm run build`  
- **Regenerate API types**: `pnpm --filter @workspace/api-spec run codegen`  

Database schema changes use Drizzle in `lib/db`; see that package’s scripts for push/migrate workflows in your environment.

### Docker (Postgres + API + UI)

Use the same layout locally or on a VM with [Docker Compose](https://docs.docker.com/compose/):

1. Copy **`.env.example`** to **`.env`**. Set **`GEMINI_API_KEY`** and **`GEMINI_BASE_URL`** (defaults target Google’s Gemini API). Optionally **`BIM_EXTRACTION_MODEL`**, **`POSTGRES_PASSWORD`**, **`WEB_PORT`**, **`API_PORT`**, etc.
2. From the repo root: **`docker compose up --build`**
3. Open **`http://localhost:3000`** (or **`WEB_PORT`**) — nginx serves the UI and proxies **`/api`** to the API container.
4. The API is also bound on the host at **`http://localhost:8080`** by default (override with **`API_PORT`** in `.env`), e.g. **`http://localhost:8080/api/healthz`**. Express already enables **CORS** for direct calls from other origins.

**Postgres only** (run API/UI on the host with `pnpm`): **`docker compose up -d db`**, then point **`DATABASE_URL`** at `postgresql://bim:YOUR_PASSWORD@localhost:5432/bim` and run **`pnpm --filter @workspace/db run push`** before starting the API.

On a server, open the host firewall for **`WEB_PORT`** and **`API_PORT`** as needed, or set **`WEB_PORT=80`** in `.env` if you bind the UI to port 80.

---


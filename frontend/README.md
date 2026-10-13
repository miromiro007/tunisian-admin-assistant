# Tunisian Admin Assistant — Frontend

Web UI for the Tunisian Admin Assistant RAG project: a chat-style interface that
streams grounded, cited answers about Tunisian labor law and CNSS from the FastAPI
backend in `../app`.

## Run

```bash
npm install
npm run dev       # http://localhost:5173
```

Other scripts:

```bash
npm run build     # tsc -b && vite build
npm run lint      # oxlint
npm run test      # vitest run
```

The backend (FastAPI + Postgres/pgvector + Ollama) must be running separately for
the app to answer questions — see the repository root `README.md`. With only
`npm run dev` running and no backend reachable, the UI loads but every question
will surface the "could not reach the server" error state.

## Environment

Copy `.env.example` to `.env` and set:

```
VITE_API_URL=http://127.0.0.1:8000
```

The base URL of the FastAPI backend. Always `127.0.0.1`, never `localhost` (the
backend's CORS allow-list is keyed on the literal origin). If `VITE_API_URL` is
unset, the app falls back to this same default.

## SSE event contract (`POST /ask/stream`)

The backend streams the answer as Server-Sent Events over a POST request (not GET),
so the client reads the response body manually with `fetch` +
`response.body.getReader()` + `TextDecoder`, rather than the `EventSource` API
(which only supports GET). See `src/api/askStream.ts`.

Request body:

```json
{ "question": "string, 3–1000 chars", "top_k": "1–10, optional", "language": "fr|ar, optional", "provider": "ollama|groq" }
```

`provider` comes from the Local (Ollama) / Cloud (Groq) selector in the header
(default Local, persisted in `localStorage`). The Groq path does not stream: it sends
the whole answer as a single `token` event followed by `done`. The UI also copes with
zero `token` events before `done`, showing a "writing the answer" placeholder.

Each frame is `event: <name>\ndata: <json>\n\n`. Frames — and even individual
multi-byte UTF-8 characters (e.g. Arabic letters) — can be split across network
chunks; the client buffers and reassembles both.

Events, always in this order:

1. `sources` — `{ "sources": Source[] }` — every source shown to the model, before
   any are marked as cited.
2. `token` — `{ "text": string }` — zero or more; appended live to the answer as it
   streams. A refusal produces **no** `token` events at all.
3. exactly one terminal event:
   - `done` — the full `AskResponse` (the source of truth — the UI replaces the
     streamed text with `done.answer` once this arrives), or
   - `error` — `{ "status": number, "detail": string }`, if generation fails
     mid-stream.

Before the stream starts, the backend may instead return a plain HTTP error (422
invalid input, 429 cloud rate limit, 502/503 embedding or database unavailable) with
a JSON `{ "detail": string }` body — handled as a normal rejected request, not as
SSE. A 429, either as an HTTP status or as an `error` event with `status: 429`, shows
a dedicated "rate limit reached" message with a Retry button.

## What was not verified against the live API

This UI was built and tested (`npm run build` / `npm run lint` / `npm run test`)
without a running backend, database, or Ollama instance in this environment. Not
verified against the real system:

- Actual SSE streaming behavior over a live connection (only simulated via unit
  tests against the pure frame/decoder logic).
- Real cold-start timing and the "warming up" message against an actual slow first
  request.
- Rendering of real Arabic model output and real citation markers end-to-end.
- CORS in practice between the Vite dev server and the FastAPI server.
- Visual appearance in an actual browser — no browser automation tool was available
  in this session; only `npm run build`'s static output was checked.

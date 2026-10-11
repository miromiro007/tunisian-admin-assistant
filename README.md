# Tunisian Admin Assistant

A learning project: an AI assistant for Tunisian administrative questions (labor law, CNSS
social security, company creation), built step by step as a RAG (Retrieval-Augmented
Generation) system. Free tools only, everything runs locally.

**Status:** Week 1 (LLM foundations) and Week 2 (embeddings + vector database + semantic
search) are done. Week 3 will add the LLM answer generation with cited sources.

## Architecture

```
PDFs (data/raw) --> extract + clean --> chunks --> embeddings (bge-m3) --> PostgreSQL + pgvector
                                                                              |
question --> embedding (bge-m3) --> cosine search (HNSW) --> top-k chunks <---+
                    ^                                            |
                    |                                   POST /search (FastAPI)
              Ollama (local)
```

| Service | Role | Host port |
|---|---|---|
| `api` | FastAPI app (`/health`, `/chat`, `/analyze`, `/search`) | 8000 |
| `db` | PostgreSQL 17 + pgvector 0.8 | 5433 (localhost only) |
| `ollama` | local models: `bge-m3` (embeddings), `qwen2.5:7b` (chat) | 11435 |

## Project layout

```
app/
  main.py              FastAPI routes
  schemas.py           request / response models (Pydantic)
  config.py            settings read from .env (pydantic-settings)
  db.py                PostgreSQL connection
  search.py            semantic search (pgvector, cosine distance)
  evaluation.py        hit@k and MRR to compare chunking strategies
  embeddings/          embedding providers (Ollama) behind one interface
  llm/                 chat providers (Ollama, Groq) behind one interface
  ingestion/           pdf_loader, chunking, configs, pipeline, repository
scripts/               ingest.py, search_demo.py, compare_configs.py, experiments
db/init/               SQL run on the first start of the database (schema, HNSW indexes)
eval/                  questions.json (10 labeled questions) and results.md
tests/                 pytest suite
```

## Quick start

1. **Configuration.** Copy `.env.example` to `.env` and set your own values
   (database password, optional `GROQ_API_KEY`). Never commit `.env`.
2. **Start the services.**
   ```bat
   docker compose up -d --build
   docker compose exec ollama ollama pull bge-m3
   ```
3. **Add the documents.** The PDFs are not in the repository. Put them in `data/raw/`,
   named `<name>_<fr|ar>[_year].pdf` (the language is read from the file name).
4. **Python environment** (for the scripts and the tests).
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```
5. **Ingest.** Safe to re-run: unchanged files are skipped, nothing is duplicated.
   ```bat
   python scripts/ingest.py
   python scripts/ingest.py --config fixed_500 fixed_1000
   ```
6. **Search.** Open http://127.0.0.1:8000/docs and try `POST /search`, or from the command line:
   ```bat
   python scripts/search_demo.py "Quelles sont les cotisations CNSS ?" --language fr
   ```
7. **Tests.**
   ```bat
   python -m pytest tests -v
   ```
   The repository tests need a separate PostgreSQL database: set `TEST_DATABASE_URL`
   to run them (they are skipped otherwise).

## `POST /search`

```json
{"question": "Quelles sont les cotisations de sécurité sociale à la charge de l'employeur ?",
 "top_k": 5, "chunk_config": "article_1500", "language": "fr"}
```

Returns the closest chunks with `score` (cosine similarity), `document`, `page`, `article`
and `content`. `language` is optional (`fr` or `ar`). Cross-language search works (a French
question can find Arabic text) but with lower scores.

## Which chunking strategy? (Week 2 experiment)

Three strategies are stored side by side in the same table (`chunk_config` column):
`article_1500` (one chunk per legal article, max 1500 characters), `fixed_500` and
`fixed_1000` (fixed windows with overlap). I compared them with
`python scripts/compare_configs.py` on 10 labeled questions (5 French, 5 Arabic).
A search "hits" when the right chunk, identified by keywords, is in the top results.

| config | hit@1 | hit@5 | MRR |
|---|---:|---:|---:|
| **article_1500** | 70% | **100%** | **0.80** |
| fixed_1000 | 60% | 80% | 0.70 |
| fixed_500 | 40% | 80% | 0.55 |

`article_1500` is the default. Limits of this experiment: only 10 questions, the metric is
keyword-based, and bigger chunks are more likely to contain the keywords by chance.
Details per question: `eval/results.md`.

## Known limitations

- Page headers and footers are repeated inside the chunks (visible in the Arabic code).
- Some Arabic words are split across lines by the PDF extraction (about 3% of lines).
- The CNSS PDF is a collection of many laws, so article numbers repeat; the chunk's law
  title is not stored yet, which makes citations ambiguous.
- Vector search finds the right neighbourhood but not always the best chunk in first place.
- The French Labor Code and the company-creation guide are not ingested yet.
- The HNSW indexes exist but PostgreSQL prefers an exact scan at this size (about 1,400
  chunks per strategy); they matter at larger scale.

## What I learned (Week 2)

- **Embeddings:** a text becomes a vector (1024 numbers with bge-m3) where closeness means
  closeness of meaning, across French, Arabic and English. Direction matters, not length,
  so I compare with cosine similarity.
- **Chunking is the biggest lever on retrieval quality.** Cutting by legal article beat blind
  fixed sizes on my test set. I measured it (hit@k, MRR) instead of guessing, and I state
  the limits of a 10-question sample.
- **PDF extraction is real work:** Arabic PDFs use presentation forms that need Unicode NFKC
  normalization, and headers or footers pollute chunks.
- **pgvector:** `vector(1024)` column, `<=>` is cosine distance (similarity = 1 - distance),
  HNSW is an approximate index that only pays off at scale. I checked with `EXPLAIN ANALYZE`.
- **Idempotent ingestion:** file hash, upserts and a unique constraint make re-runs safe;
  embeddings are computed before the database transaction so a failure never leaves a
  half-written document.
- **Async vs blocking:** psycopg is synchronous, so the async route calls it in a worker thread.
- **Testing without the infrastructure:** fakes for the embedder and the database test the
  API quickly; real database tests are gated behind an environment variable.
- **Windows gotcha:** `localhost` can resolve to IPv6 first and make each connection wait
  minutes; `127.0.0.1` fixed it.
- **Security habits:** secrets only in `.env`, database published on 127.0.0.1 only,
  `.env.example` holds placeholders, and a leaked key is rotated at once.

## What I learned (Week 1)

- **Tokens:** LLMs read tokens, not words. Arabic cost ~2.8x more tokens than English
  for the same sentence (25 vs 9), which impacts cost and context window.
- **Context window:** shared by prompt and answer; LLMs are stateless, so history
  must be resent on every request.
- **Temperature:** 0 gave identical outputs; 1.2 gave varied (and riskier) ones.
  I use low values for factual/admin tasks.
- **Prompts:** system role (developer rules) vs user role; few-shot examples
  improve format consistency.
- **Structured output:** JSON schema + Pydantic validation; never trust LLM output.
- **Local vs API:** Qwen 7B (private, free, ~25 tok/s) vs gpt-oss-120b on Groq
  (~240 tok/s, richer answers, rate limits, data leaves the machine).
- **Design:** provider abstraction (abstract class + factory) so adding a provider
  needs one new class. Model names live in config because Groq retired a model
  during the project.
- **Hallucinations:** both models gave plausible but unverified legal details,
  which is why the next phase uses RAG with cited sources.
- **Docker:** Compose services reach each other by service name; secrets are injected
  at runtime, never baked into the image.

## Next (Week 3)

Generate answers with the LLM from the retrieved chunks, with citations (document, page,
article), and refuse to answer when nothing relevant is found.
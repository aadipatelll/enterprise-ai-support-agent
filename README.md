# Enterprise AI Support Agent

[![CI](https://github.com/aadipatelll/enterprise-ai-support-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/aadipatelll/enterprise-ai-support-agent/actions/workflows/ci.yml)

**An AI help desk that answers employee questions from internal policy documents with cited sources, and opens a support ticket through an MCP server when the documents don't have the answer.**

<!-- Demo GIF: record the app and save it as docs/demo.gif, then uncomment the line below. -->
<!-- ![Demo of asking a question, opening a citation, and creating a ticket](docs/demo.gif) -->

> 📽️ *Demo GIF coming soon.*

Everything runs locally and for free: the language model and embeddings come from [Ollama](https://ollama.com), so no API key is needed.

## Features

- **Answers with citations.** Each answer cites the policy sections it used, like `[1]`. Clicking a citation opens the original document.
- **Declines instead of guessing.** If no document chunk is relevant enough, or the model says the sources don't answer the question, the agent says so and offers to open a ticket.
- **Ticketing through MCP.** A separate [Model Context Protocol](https://modelcontextprotocol.io) server exposes `create_ticket`, `update_ticket`, and `get_ticket_status` tools, backed by PostgreSQL.
- **Section-aware ingestion.** Markdown documents are split on their headings, embedded, and stored in pgvector with title, section, and source metadata.
- **Measurable quality.** An evaluation script compares chunk sizes, top-k values, and prompt versions on 30 labelled questions.
- **Accessible chat UI.** Every control is labelled and keyboard-friendly, with live regions for screen readers.
- **Provider-agnostic.** Model names live in `.env`, and models are built with LangChain's `init_chat_model` and `init_embeddings`, so switching to a hosted provider needs no code changes.

## Architecture

```mermaid
flowchart LR
    user([Employee]) --> ui["React UI<br/>:5173"]
    ui -- "POST /ask" --> api["FastAPI backend<br/>:8000"]
    ui -- "/tickets, /documents" --> api
    api -- "embed question, generate answer" --> ollama["Ollama<br/>llama3.1:8b + nomic-embed-text"]
    api -- "top-k cosine search" --> pg[("PostgreSQL + pgvector")]
    api -- "MCP tools over Streamable HTTP" --> mcp["Ticket MCP server<br/>:8001"]
    mcp -- "tickets table" --> pg
    docs[/"data/docs/*.md"/] --> ingest["Ingestion job"]
    ingest -- "embed chunks" --> ollama
    ingest -- "chunks + metadata" --> pg
```

**How a question is answered:**

1. The question is embedded, and the top-k nearest chunks are fetched from pgvector by cosine similarity.
2. Chunks below `MIN_RELEVANCE_SCORE` are dropped. If none are left, the API answers "I couldn't find this" and suggests a ticket, without calling the LLM.
3. The remaining chunks go into a versioned prompt as numbered sources, each labelled with its title, section, and file.
4. The model must cite sources like `[n]`, or reply `INSUFFICIENT_CONTEXT` if the sources don't contain the answer, which also triggers the ticket offer.
5. The cited numbers are mapped back to their source metadata and returned as citations.

## Tech stack

| Layer | Tools |
|---|---|
| Backend | Python 3.12, FastAPI, LangChain, Pydantic, SQLAlchemy 2 |
| Database | PostgreSQL 16 + pgvector |
| LLM and embeddings | Ollama (`llama3.1:8b`, `nomic-embed-text`), configurable in `.env` |
| Tickets | Python MCP SDK (`MCPServer`), Streamable HTTP transport |
| Frontend | React 19, TypeScript, Vite |
| Testing | pytest, Vitest, React Testing Library |
| Tooling | Docker Compose, GitHub Actions, ruff, ESLint (with `jsx-a11y`) |

## Project structure

```
backend/      FastAPI app, RAG pipeline, ingestion CLI, MCP ticket client
mcp_server/   MCP server with the ticket tools and the tickets table
frontend/     React + TypeScript chat UI
eval/         30 labelled questions and the evaluation script
data/docs/    30 policy documents and runbooks for a fictional company, Corvane Labs
```

## Setup on Windows

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Ollama for Windows](https://ollama.com/download/windows)
- Only for local development and tests: [Python 3.12](https://www.python.org/downloads/) and [Node.js 24 or newer](https://nodejs.org)

### 1. Download the models

After installing Ollama (it runs in the background and listens on `http://localhost:11434`):

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### 2. Configure

```powershell
copy .env.example .env
```

The defaults work as they are. `.env` is git-ignored, so change `POSTGRES_PASSWORD` there if you like.

### 3. Start everything

```powershell
docker compose up --build
```

This starts PostgreSQL, the MCP ticket server, the backend, and the frontend. It also runs a one-time `ingest` job that embeds `data/docs` into pgvector. Ollama stays on the host, and containers reach it through `host.docker.internal`.

- Chat UI: http://localhost:5173
- API docs (Swagger): http://localhost:8000/docs
- MCP endpoint: http://localhost:8001/mcp

To re-embed the documents after editing them or changing `CHUNK_SIZE`:

```powershell
docker compose run --rm ingest
```

### Try it

- *"How many PTO days carry over into next year?"* gets an answer with a citation to the PTO policy.
- *"Can I bring my dog to the office?"* is not covered by the documents, so the agent declines and offers to create a ticket.

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/ask` | `{ "question": "..." }` returns the answer, `answered`, citations, and a suggested ticket |
| `GET` | `/documents/{source}` | Returns the full source document for a citation |
| `POST` | `/tickets` | Creates a ticket (through the MCP `create_ticket` tool) |
| `GET` | `/tickets/{id}` | Gets a ticket's status (`get_ticket_status`) |
| `PATCH` | `/tickets/{id}` | Changes status or priority, or adds a note (`update_ticket`) |

Errors are explicit: `503` when the model or database is down, `502` when the ticket service fails, `404` for a missing ticket or document, and `422` for invalid input.

## Running tests and linters

The tests use fake embeddings, a fake LLM, and in-process MCP servers, so **no Ollama or Docker is needed**. GitHub Actions runs everything below on every push and pull request, plus pgvector integration tests against a Postgres service container.

```powershell
# Backend + evaluation (one virtual environment)
cd backend
py -3.12 -m venv .venv; .venv\Scripts\activate
pip install -e ".[dev]"
ruff check .; pytest
cd ..\eval; ruff check .; pytest

# MCP server
cd ..\mcp_server
py -3.12 -m venv .venv; .venv\Scripts\activate
pip install -e ".[dev]"
ruff check .; pytest

# Frontend
cd ..\frontend
npm ci; npm run lint; npm run typecheck; npm test
```

To run the pgvector integration tests locally, start the database with `docker compose up -d db` and set `TEST_DATABASE_URL` (format: `postgresql+psycopg://user:password@localhost:5432/dbname`) before running `pytest`.

## Evaluation

`eval/questions.json` holds 30 hand-written questions:

- **26 answerable questions.** Each has an expected answer, the expected source document(s), and the key facts a correct answer must contain (for example `"$350"` or `"March 31"`).
- **4 unanswerable questions.** The correct behaviour for these is to decline. One of them is a trap: dental coverage is mentioned in the documents, but no annual maximum is given.

A test checks that every key fact really appears in its expected source document, so the dataset can't drift from the corpus.

### Run it

Ollama must be running. Postgres is **not** needed: the script builds an in-memory index for each chunk size, using the same cosine search as pgvector, so it never changes the app's database.

```powershell
cd backend; .venv\Scripts\activate; cd ..
python eval/run_eval.py --chunk-sizes 300 800 --top-ks 2 4 --prompts v1 v2
```

These arguments are the defaults. They make 8 configurations × 30 questions, which is 240 LLM calls, so the run takes a while on a laptop CPU. For a quick check, use `--limit 5` or fewer values.

The script writes `eval/results/results.md` (the comparison table) and `eval/results/details.json` (every answer and every retrieved source).

### Metrics

| Metric | Meaning |
|---|---|
| Retrieval hit@k | Share of answerable questions where an expected source is in the top-k chunks |
| Answer accuracy | Share of all questions handled correctly: an answer containing every key fact, or a refusal for unanswerable questions |
| Correct abstentions | Share of unanswerable questions the agent declined |
| Citation accuracy | Share of answered, answerable questions whose citations include an expected source |
| Mean latency | Average seconds per `/ask` call (embedding + retrieval + generation) |

Answer accuracy uses deterministic key-fact matching rather than an LLM judge. Results are reproducible and easy to audit, at the cost of being strict about wording (alternatives like `three years|3 years` help with this).

> No results are published here on purpose. Run the script on your machine to produce them.

## Configuration

All settings are environment variables (see [`.env.example`](.env.example)):

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` / `LLM_MODEL` | `ollama` / `llama3.1:8b` | Chat model (any LangChain `init_chat_model` provider) |
| `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` | `ollama` / `nomic-embed-text` | Embedding model |
| `EMBEDDING_DIM` | `768` | Vector column size; must match the embedding model |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `100` | Maximum characters per chunk, and overlap when a section is split |
| `TOP_K` | `4` | Chunks retrieved per question |
| `MIN_RELEVANCE_SCORE` | `0.55` | Cosine similarity below which a chunk counts as irrelevant |
| `PROMPT_VERSION` | `v1` | Answer prompt (`v1` concise, `v2` stricter rules) |
| `MCP_SERVER_URL` | `http://localhost:8001/mcp` | Ticket MCP server |

## Design decisions

### Why section-based chunking?

Policy documents are written in self-contained sections ("Carryover", "Limits", "Lost Cards"). Splitting on `##` headings first means a chunk never mixes two topics, and each chunk carries a meaningful section name for its citation. Only sections longer than `CHUNK_SIZE` are split again, with overlap. Each chunk is embedded as `Title > Section` plus its text, so short chunks keep their context.
*Trade-off:* chunk sizes vary, and a document with poor headings would get weaker chunks. Fixed-size chunking is simpler but cuts across topics and makes citations less precise.

### Why pgvector?

The app already needs PostgreSQL for tickets, so pgvector adds vector search without another service to run, back up, or secure. Chunks, metadata, and tickets live in one place with normal SQL and transactions: re-ingestion replaces the whole index in a single transaction, so a failed run never leaves a half-built index.
*Trade-off:* a dedicated vector database scales further and offers features like hybrid search out of the box. For thousands of chunks, Postgres is more than enough. At 30 documents, search is an exact scan; an HNSW index would be the next step as the corpus grows.

### Why MCP for tickets?

The ticket tools are a separate server that speaks a standard protocol, rather than functions inside the API. The same `create_ticket` and `get_ticket_status` tools can be used by this app, by an agent framework, or by an MCP client like Claude Desktop, with no changes. It also keeps the boundaries clean: the backend never touches the tickets table.
*Trade-offs:* an extra service and a network hop. The MCP Python SDK is also young: version 2.3's new protocol negotiation dropped connections over HTTP, so the client uses the classic initialize handshake and the server runs stateless (both commented in the code).

### Other choices

- **Two-layer refusal.** A similarity threshold catches clearly unrelated questions cheaply, before any LLM call. The `INSUFFICIENT_CONTEXT` instruction catches questions that look related but aren't answered (like the dental-maximum trap question).
- **Dependency injection over globals.** The API takes its services as a `Services` object, so tests can swap in fakes without patching.
- **Errors as domain exceptions.** Model, database, and ticket failures raise typed errors that map to clear HTTP status codes, instead of leaking stack traces.

## What I'd improve next

- **Hybrid search and re-ranking.** Combine BM25 keyword search with vector search, then re-rank with a cross-encoder. This helps exact-term questions like error messages.
- **Streaming answers.** Stream tokens to the UI so a slow local model feels responsive.
- **LLM-as-judge evaluation.** Add it alongside key-fact matching to score paraphrased answers, and track evaluation results in CI over time.
- **Agentic tool use.** Let the LLM call the MCP tools itself, for example "check my ticket 12", instead of the UI calling them through the API.
- **Auth and multi-tenancy.** Add SSO login, tickets tied to the signed-in employee, and document-level access control based on data classification.
- **Incremental ingestion.** Re-embed only changed documents, using content hashes, instead of rebuilding the whole index.
- **Observability.** Add tracing for retrieval scores, prompt versions, and latency per request.

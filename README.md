# Enterprise AI Support Agent

A RAG agent that answers employee questions from internal company documents and opens support tickets through an MCP server when the documents can't answer.

> Work in progress. Full documentation is coming soon.

## Quick start

```powershell
copy .env.example .env
ollama pull llama3.1:8b
ollama pull nomic-embed-text
docker compose up --build
```

Open the chat UI at http://localhost:5173. The API docs are at http://localhost:8000/docs, and the MCP ticket server is at http://localhost:8001/mcp.
To re-embed the documents, run `docker compose run --rm ingest`.

## Running tests

```powershell
cd backend; py -3.12 -m venv .venv; .venv\Scripts\activate; pip install -e ".[dev]"; pytest
cd ..\mcp_server; py -3.12 -m venv .venv; .venv\Scripts\activate; pip install -e ".[dev]"; pytest
cd ..\frontend; npm ci; npm run lint; npm test
```

# Enterprise AI Support Agent

A RAG agent that answers employee questions from internal company documents and opens support tickets through an MCP server when the documents can't answer.

> Work in progress. Full documentation is coming soon.

## Quick start (ingestion)

```powershell
copy .env.example .env
docker compose up -d db
ollama pull nomic-embed-text
cd backend
py -3.12 -m venv .venv; .venv\Scripts\activate
pip install -e ".[dev]"
python -m app.ingestion
pytest
```

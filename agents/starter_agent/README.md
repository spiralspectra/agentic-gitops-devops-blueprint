# Starter Agent Service

A production-ready AI agent service blueprint powered by FastAPI and Google GenAI SDK (`gemini-2.5-pro`).

## Features
- **FastAPI Core**: Provides `/healthz` for health checks and `/query` for synchronous agent execution.
- **Google GenAI SDK**: Standard public model configuration supporting Vertex AI backend.
- **Runtime Metadata**: Tracks deployment consistency in `deployment_metadata.json`.
- **Container Ready**: Packaged with a slim Python 3.11 Dockerfile.

## Local Execution
```bash
uv run uvicorn app:app --reload --port 8080
```

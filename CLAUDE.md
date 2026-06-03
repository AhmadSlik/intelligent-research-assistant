# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Intelligent Research Assistant** — a multi-agent AI system that researches topics, reads and analyzes sources, and produces written reports.

**Developer:** Ahmad — beginner level. Explain concepts clearly, avoid unexplained jargon, and prefer simple explicit code over clever abstractions.

**Environment:** Windows 10, PowerShell. Use PowerShell-compatible commands when giving terminal instructions.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Vector DB | ChromaDB |
| LLM API | OpenRouter (multi-model, per-agent routing via `ModelRouter`) |
| Frontend | Next.js |
| Agents | Custom multi-agent system (see below) |

---

## Architecture

```
User (Next.js frontend)
        │
        ▼
FastAPI backend  ──►  OpenRouter API (LLM)
        │
        ├──► ChromaDB (vector store for research memory)
        │
        └──► Multi-Agent Pipeline:
               1. Researcher  — finds and gathers sources
               2. Reader      — reads and extracts key info from sources
               3. Analyst     — synthesizes and evaluates the information
               4. Writer      — produces the final written report
               5. FactChecker — verifies report claims against sources
```

---

## Multi-Model Support (Day 21)

Each agent uses a dedicated free model, managed by `backend/core/model_router.py`.

| Agent | Model | Role |
|---|---|---|
| researcher | `meta-llama/llama-3.2-3b-instruct:free` | Fast URL gathering (no LLM call yet) |
| reader | `google/gemma-4-31b-it:free` | Extracts key points from sources |
| analyst | `deepseek/deepseek-v4-flash:free` | Synthesizes and finds contradictions |
| writer | `qwen/qwen3-next-80b-a3b-instruct:free` | Writes the final report |
| fact_checker | `meta-llama/llama-3.3-70b-instruct:free` | Verifies report claims against sources, returns confidence score |

**Fallback:** If any model returns 429 (rate limit) or 402 (provider quota), the system automatically falls back to `openrouter/auto` and logs a warning.

**Logging format:**
```
[INFO] research_assistant.model_router: Agent reader using model google/gemma-4-31b-it:free
[WARNING] research_assistant.model_router: Rate limited on X (error: RateLimitError), falling back to openrouter/auto
```

**New endpoint:** `GET /api/models/info` — returns all models, fallbacks, and fallback chains.

**Note:** Free model availability on OpenRouter changes frequently. If a model slug stops working, check `https://openrouter.ai/models` for current free models and update `MODELS` dict in `backend/core/model_router.py`.

---

## Wikipedia Source Fetching (Day 22)

`backend/agents/web_scraper.py` queries the Wikipedia API for both Arabic and English articles. It cleans the raw wikitext and returns plain-text excerpts.

`backend/rag/source_cache.py` — in-memory source cache keyed by `(lang, title)`. Prevents duplicate Wikipedia requests within a session.

---

## PDF Processing (Day 23)

`backend/agents/pdf_processor.py` — extracts text and metadata (page count, title, author) from a PDF binary using `pypdf`. Raises `PDFExtractionError` on corrupt files.

`backend/api/pdf.py` endpoints:
- `POST /pdf/upload` — accepts `multipart/form-data`, validates file type + size (≤ 10 MB), stores chunks in ChromaDB, returns `doc_id` + `pages` + `preview`.
- `POST /pdf/research` — accepts `{ "doc_id": "...", "question": "..." }`, retrieves top-5 relevant chunks, runs Reader → Analyst → Writer pipeline.

---

## FactChecker Agent (Day 24)

`backend/agents/fact_checker.py` — 5th and final agent in the pipeline.

Takes the finished report + source list, prompts the LLM to verify each claim, and returns:
```json
{ "confidence": 0.92, "flagged_claims": ["Claim X contradicts source 2"] }
```
Confidence is a float 0–1 (1 = fully verified). The FactCheck card in the frontend displays this result.

---

## Arabic Source Handling (Day 26)

`backend/utils/arabic.py` normalizes Arabic text before it reaches the LLM:
- Alef variants (أ / إ / آ) → ا
- Removes tashkeel (diacritics)
- Strips Wikipedia boilerplate (edit links, citation-needed markers)

AR fallback: if an English Wikipedia article is not found, the Researcher retries with the Arabic Wikipedia API.

---

## Streaming via SSE (Day 28)

`POST /research/stream` returns a `StreamingResponse` with `text/event-stream` content type. Each event has the format:
```
data: {"type": "token", "content": "..."}
```

`ModelRouter.stream_chat(agent_type, messages)` — async generator that yields tokens from the Writer. The same primary/fallback logic applies: if the primary model raises `RateLimitError` or `APIStatusError`, the fallback generator takes over transparently.

---

## Performance Optimizations (Day 29)

**Parallel Reader** — `backend/agents/reader.py` uses `asyncio.gather()` to read all sources concurrently instead of sequentially. Reduces total reader time from `N × latency` to `max(latency)`.

**LRU embedding cache** — `backend/rag/rag_engine.py::_encode_cached` wraps `sentence-transformers` encode with `functools.lru_cache`. Re-encoding the same string is free after the first call.

**Result cache** — `backend/core/result_cache.py`: thread-safe dict with a 10-minute TTL and a 64-entry cap (LRU eviction). Keyed by normalized topic string (lowercase, stripped). If the same topic arrives within the window, the cached response is returned without re-running any agents.

---

## Commands

> Update this section once commands are established.

### Backend
```powershell
# Install dependencies
pip install -r requirements.txt

# Start dev server (to be confirmed)
uvicorn main:app --reload
```

### Frontend
```powershell
# Install dependencies
npm install

# Start dev server
npm run dev
```

### Tests
```powershell
# Run all tests
pytest

# Run a single test file
pytest tests/test_filename.py
```

---

## Key Conventions

- Model routing: `backend/core/model_router.py` — each agent gets its own free model with automatic fallback
- Agent pipeline: Researcher → Reader (parallel) → Analyst → Writer → FactChecker
- ChromaDB stores research context/embeddings for retrieval during a session
- Result cache invalidates after 10 minutes (`backend/core/result_cache.py`)
- All endpoints:
  - `POST /research/full` — blocking 5-agent pipeline
  - `POST /research/stream` — same pipeline with SSE token streaming
  - `POST /pdf/upload` — PDF ingestion into ChromaDB
  - `POST /pdf/research` — pipeline on uploaded PDF
  - `GET /api/models/info` — per-agent models + fallback chains
  - `POST /rag/add`, `POST /rag/search`, `GET /rag/count` — RAG operations
  - `GET /`, `GET /health` — status + Railway healthcheck

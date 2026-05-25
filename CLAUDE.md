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
| fact_checker | `meta-llama/llama-3.3-70b-instruct:free` | Reserved for future use |

**Fallback:** If any model returns 429 (rate limit) or 402 (provider quota), the system automatically falls back to `openrouter/auto` and logs a warning.

**Logging format:**
```
[INFO] research_assistant.model_router: Agent reader using model google/gemma-4-31b-it:free
[WARNING] research_assistant.model_router: Rate limited on X (error: RateLimitError), falling back to openrouter/auto
```

**New endpoint:** `GET /api/models/info` — returns all models, fallbacks, and fallback chains.

**Note:** Free model availability on OpenRouter changes frequently. If a model slug stops working, check `https://openrouter.ai/models` for current free models and update `MODELS` dict in `backend/core/model_router.py`.

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
- Agent pipeline runs sequentially: Researcher → Reader → Analyst → Writer
- ChromaDB stores research context/embeddings for retrieval during a session

<div align="center">

# 🧠 Intelligent Research Assistant

**From question to cited report — autonomously.**
**من سؤال إلى تقرير موثق — بشكل مستقل.**

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-5_Free_Models-FF6B35?style=for-the-badge&logo=openai&logoColor=white)](https://openrouter.ai)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-9B59B6?style=for-the-badge)](https://trychroma.com)
[![Railway](https://img.shields.io/badge/Railway-Deploy-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)
[![Netlify](https://img.shields.io/badge/Netlify-Deploy-00C7B7?style=for-the-badge&logo=netlify&logoColor=white)](https://netlify.com)
[![Release](https://img.shields.io/badge/Release-v2.0.0-success?style=for-the-badge)](https://github.com/AhmadSlik/intelligent-research-assistant/releases/tag/v2.0.0)
[![License](https://img.shields.io/badge/License-MIT-F7DC6F?style=for-the-badge)](LICENSE)

</div>

---

## 🌐 Live Demo

| | Link |
|---|---|
| 🖥️ **Frontend** | [research-assistant-ai.netlify.app](https://research-assistant-ai.netlify.app) |
| ⚙️ **Backend API** | [web-production-e01f8.up.railway.app](https://web-production-e01f8.up.railway.app) |
| 📚 **Interactive API Docs** | [web-production-e01f8.up.railway.app/docs](https://web-production-e01f8.up.railway.app/docs) |

> Type any research topic and get a full structured report with citations in under two minutes.

---

## 📖 About

A multi-agent AI system that fully automates the research process. Submit a topic, and five specialized AI agents collaborate — one gathers sources from Wikipedia (Arabic + English), one reads and extracts key information in parallel, one synthesizes and detects contradictions, one writes a polished cited report, and a fifth **FactChecker** verifies every claim and returns a confidence score. All findings are stored in a ChromaDB vector store for semantic memory and retrieval. You can also upload a PDF and run the full pipeline on its content.

<div dir="rtl" lang="ar">

نظام ذكاء اصطناعي متعدد الوكلاء يؤتمت عملية البحث بالكامل. أرسل أي موضوع، وسيتعاون خمسة وكلاء متخصصون: الأول يجمع المصادر من ويكيبيديا (عربي + إنجليزي)، والثاني يقرأ ويستخرج النقاط المحورية بشكل متوازٍ، والثالث يحلل ويكشف التناقضات، والرابع يكتب تقريراً علمياً موثقاً بالمراجع، والخامس — **مدقق الحقائق** — يتحقق من كل ادعاء ويعطي درجة ثقة. يمكنك أيضاً رفع ملف PDF وتشغيل الـpipeline كاملاً عليه.

</div>

---

## 🏗️ Architecture

```
                    ┌─────────────────────────────────────┐
                    │        Next.js Frontend (RTL/AR)     │
                    │  Cairo font · FactCheck card · SSE  │
                    └──────────────┬──────────────────────┘
                                   │  POST /research/full
                                   │  POST /research/stream (SSE)
                                   │  POST /pdf/upload + /pdf/research
                                   ▼
                    ┌─────────────────────────────────────┐
                    │          FastAPI Backend             │
                    │   Result Cache (10-min TTL, 64 max) │
                    └──────────────┬──────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
┌──────────────────┐   ┌───────────────────────┐  ┌──────────────────────┐
│  1. Researcher   │   │    PDF Processor       │  │   ModelRouter        │
│  Wikipedia AR+EN │   │  (pypdf + ChromaDB)    │  │   5 free models      │
│  + source cache  │   │  POST /pdf/upload      │  │ + openrouter/auto    │
└────────┬─────────┘   └───────────┬───────────┘  │   fallback on 429    │
         │                         │               └──────────────────────┘
         ▼                         │
┌──────────────────────────────────▼────────────────┐
│  2. Reader  (parallel asyncio.gather per source)  │
│  gemma-4-31b · extracts 3 key points per source  │
└──────────────────────────┬────────────────────────┘
                           ▼
              ┌────────────────────────┐
              │  3. Analyst            │
              │  deepseek-v4-flash     │
              │  synthesis + conflicts │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  4. Writer             │
              │  qwen3-next-80b        │
              │  academic report +     │ ──► SSE token stream
              │  [1][2][3] citations   │     to frontend
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  5. FactChecker        │
              │  llama-3.3-70b         │
              │  confidence 0–1 +      │
              │  flagged claims        │
              └────────────┬───────────┘
                           ▼
          ┌────────────────────────────────────┐
          │   ChromaDB  ·  RAG Memory          │
          │  _encode_cached (LRU embed cache)  │
          │  all-MiniLM-L6-v2 embeddings       │
          └────────────────────────────────────┘
```

---

## ✨ Features

- 🤖 **5-agent autonomous pipeline** — Researcher · Reader · Analyst · Writer · **FactChecker**
- 🔍 **Real Wikipedia scraping** — Arabic + English with in-memory source cache (no duplicate requests)
- 🧩 **Multi-Model routing** — 5 dedicated free models per agent + auto-fallback to `openrouter/auto` on 429/402
- 📄 **PDF upload & research** — upload any PDF (up to 10 MB), run the full pipeline on its content
- ✅ **FactChecker agent** — verifies report claims against sources, returns confidence score 0–1 + flagged claims
- 🌍 **Arabic-first UI** — Cairo font, full RTL layout, FactCheck card, responsive design
- ⚡ **Streaming responses** — token-by-token SSE so the report appears in real time as it's written
- 🚀 **Parallel reading** — Reader processes all sources simultaneously with `asyncio.gather`
- 🗄️ **Two-level cache** — LRU embedding cache (re-encode prevention) + 10-min result cache per topic
- ✍️ **Academic writing style** — formal tone, Introduction / Main Findings / Contradictions / Conclusion structure
- 🧠 **RAG memory** — ChromaDB + `all-MiniLM-L6-v2` embeddings for semantic retrieval across sessions
- ☁️ **Production-deployed** — Railway (backend) + Netlify (frontend), auto-deploys on push

---

## 🛠️ Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **Frontend** | Next.js, React, Tailwind CSS, TypeScript | 16 / 19 / 4 / 5 |
| **Backend** | Python, FastAPI, Uvicorn | 3.14 / 0.115 / 0.30 |
| **LLM** | 5 free models via OpenRouter (`openai` SDK compat.) — see [`GET /api/models/info`](#-api-reference) | per-agent |
| **PDF parsing** | `pypdf` | 5.x |
| **Embeddings** | `sentence-transformers` — `all-MiniLM-L6-v2` | 3.0 |
| **Vector DB** | ChromaDB | 0.5 |
| **HTTP Client** | `httpx` (async) | 0.27 |
| **Validation** | Pydantic | 2.9 |
| **Hosting — Backend** | Railway (Nixpacks build, auto healthcheck on `/health`) | — |
| **Hosting — Frontend** | Netlify (Next.js plugin, CDN edge delivery) | — |
| **Testing** | pytest + pytest-asyncio + httpx `ASGITransport` | — |

---

## 🔄 How It Works

### Standard research flow (`POST /research/full` or `POST /research/stream`)

1. **User** types a research topic into the Next.js interface and clicks Submit.
2. The frontend sends `POST /research/full` (blocking JSON) or `POST /research/stream` (SSE tokens appear live) to the FastAPI backend.
3. **Result cache check** — if the same topic was researched within the last 10 minutes, the cached report is returned immediately.
4. **Researcher Agent** — queries Wikipedia in both Arabic and English, fetches each article (cached to avoid duplicate requests).
5. **Reader Agent** — processes all sources **in parallel** (`asyncio.gather`), prompting the LLM to distill exactly **3 key points** per source.
6. **Analyst Agent** — consolidates all key points, produces a unified `SUMMARY` and a `CONTRADICTIONS` list.
7. **Writer Agent** — writes a **formal academic report** (Introduction, Main Findings, Contradictions & Debates, Conclusion) with `[1][2][3]` inline citations and a numbered References section. Tokens are streamed live to the frontend via SSE.
8. **FactChecker Agent** — verifies each claim in the report against the source material, returns a `confidence` score (0–1) and a list of `flagged_claims`.
9. The finished report, sources, key points, and fact-check result are returned to the UI and rendered in the Arabic RTL interface.

### PDF research flow (`POST /pdf/upload` → `POST /pdf/research`)

1. User uploads a PDF (up to 10 MB). `POST /pdf/upload` extracts text via `pypdf`, chunks it, and stores it in ChromaDB. Returns a `doc_id`.
2. User submits a question + `doc_id` to `POST /pdf/research`. The backend retrieves the most relevant chunks, then runs the Reader → Analyst → Writer pipeline on them.

---

## 🚀 Local Setup

### Prerequisites

- Python ≥ 3.11
- Node.js ≥ 18
- An [OpenRouter](https://openrouter.ai) API key (free tier works)

### Backend

```bash
# 1. Clone the repo
git clone https://github.com/AhmadSlik/intelligent-research-assistant.git
cd intelligent-research-assistant

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate           # Linux / macOS
# venv\Scripts\Activate.ps1       # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Open .env and fill in your OPENROUTER_API_KEY

# 5. Start the backend
cd backend
uvicorn main:app --reload --port 8000
```

API is now live at `http://localhost:8000` · Swagger UI at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI is now at `http://localhost:3000`

> **Local dev note:** `frontend/app/page.tsx` has the Railway production URL hardcoded. For local development, change it to `http://localhost:8000` (or extract it to a `NEXT_PUBLIC_API_URL` environment variable).

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service status |
| `GET` | `/health` | Healthcheck (polled by Railway every 30s) |
| `POST` | `/research/full` | Run the full 5-agent pipeline, return final JSON |
| `POST` | `/research/stream` | Same pipeline — streams Writer output token-by-token via SSE |
| `POST` | `/pdf/upload` | Upload a PDF (≤ 10 MB), extract text + metadata, store in ChromaDB |
| `POST` | `/pdf/research` | Run Reader → Analyst → Writer on an uploaded PDF by `doc_id` |
| `GET` | `/api/models/info` | Returns per-agent models, fallbacks, and fallback chains |
| `POST` | `/rag/add` | Store a document in ChromaDB |
| `POST` | `/rag/search` | Semantic search over stored documents |
| `GET` | `/rag/count` | Total document count in the vector store |

#### Example — Run a Research Pipeline

```bash
curl -X POST https://web-production-e01f8.up.railway.app/research/full \
  -H "Content-Type: application/json" \
  -d '{"topic": "quantum computing"}'
```

**Response:**

```json
{
  "topic": "quantum computing",
  "report": "## Introduction\n\nQuantum computing represents...",
  "sources": [
    {
      "title": "Wikipedia — quantum computing",
      "url": "https://en.wikipedia.org/wiki/quantum_computing",
      "summary": "Quantum computing uses quantum-mechanical phenomena..."
    }
  ],
  "key_points_count": 9,
  "fact_check": {
    "confidence": 0.92,
    "flagged_claims": []
  }
}
```

#### Example — Streaming (SSE)

```bash
curl -X POST https://web-production-e01f8.up.railway.app/research/stream \
  -H "Content-Type: application/json" \
  -d '{"topic": "quantum computing"}'
```

Each SSE event arrives as:
```
data: {"type": "token", "content": "Quantum "}
data: {"type": "token", "content": "computing "}
...
data: {"type": "done", "sources": [...], "fact_check": {...}}
```

---

## 📸 Screenshots

| Home | Researching... | Results |
|:---:|:---:|:---:|
| ![Home screen](docs/screenshots/home.png) | ![Loading state](docs/screenshots/loading.png) | ![Report results](docs/screenshots/results.png) |

---

## 🧪 Testing

The test suite covers the health endpoint and all RAG operations using an in-process ASGI transport — no live server needed.

```bash
# From the repo root
pytest
```

Tests live in `tests/test_api.py`. `pytest.ini` sets `asyncio_mode = auto`.

---

## 📁 Project Structure

<details>
<summary>Click to expand</summary>

```
intelligent-research-assistant/
├── backend/
│   ├── main.py                      # FastAPI app, CORS, router wiring
│   ├── api/
│   │   ├── research.py              # POST /research/full · POST /research/stream (SSE)
│   │   ├── pdf.py                   # POST /pdf/upload · POST /pdf/research
│   │   └── models.py                # GET /api/models/info
│   ├── agents/
│   │   ├── researcher.py            # Agent 1 — Wikipedia AR+EN source discovery
│   │   ├── reader.py                # Agent 2 — parallel key-point extraction (LLM)
│   │   ├── analyst.py               # Agent 3 — synthesis + contradiction detection (LLM)
│   │   ├── writer.py                # Agent 4 — academic report generation + SSE stream
│   │   ├── fact_checker.py          # Agent 5 — claim verification + confidence score
│   │   ├── web_scraper.py           # Wikipedia API client (AR + EN)
│   │   └── pdf_processor.py         # PDF text + metadata extraction (pypdf)
│   ├── core/
│   │   ├── model_router.py          # Per-agent free model routing + openrouter/auto fallback
│   │   └── result_cache.py          # 10-min topic-level result cache (64 entries max)
│   ├── rag/
│   │   ├── rag_engine.py            # ChromaDB client · _encode_cached (LRU) · chunking
│   │   ├── rag_api.py               # POST /rag/add · /rag/search · GET /rag/count
│   │   └── source_cache.py          # In-memory Wikipedia source cache
│   └── utils/
│       └── arabic.py                # Alef normalization · diacritic removal · AR source cleaning
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Single-page Arabic RTL UI with Cairo font + FactCheck card
│   │   ├── layout.tsx               # Root layout — RTL, Cairo font, Arabic metadata
│   │   └── globals.css
│   └── package.json
├── tests/
│   └── test_api.py                  # Async pytest suite (ASGI transport)
├── docs/
│   └── daily/                       # 30 daily learning logs (Arabic)
├── CHANGELOG.md
├── .env.example
├── requirements.txt
├── Procfile
├── railway.json
└── netlify.toml
```

</details>

---

## 🗺️ Roadmap

- [ ] **Real web search** — replace Wikipedia-only sources with a live search API (SerpAPI, Brave, or DuckDuckGo)
- [ ] **Persistent ChromaDB** — switch from in-memory to file-based client so RAG memory survives restarts
- [ ] **Env-based API URL** — `NEXT_PUBLIC_API_URL` in the frontend instead of a hardcoded Railway URL
- [ ] **User authentication** — multi-user sessions with saved research history
- [ ] **Report export** — download reports as PDF or Markdown
- [ ] **Multi-language output** — generate reports in Arabic as well as English

---

## 👨‍💻 Author

<div align="center">

### Ahmad Slik

**17-year-old entrepreneur · AI builder · Full-stack developer**

I started building AI products at 16, teaching myself Python, FastAPI, and modern LLM tooling from scratch. This project — built over 30 days of focused daily sessions — is my first deployed multi-agent system, proving that autonomous AI pipelines can automate complex knowledge workflows end-to-end.

<div dir="rtl" lang="ar">

أحمد سليق — مطوّر برمجيات ورائد أعمال عمره 17 عامًا. بدأتُ بناء منتجات الذكاء الاصطناعي وأنا في السادسة عشرة، وتعلّمتُ Python وFastAPI وأدوات نماذج اللغة الحديثة بشكل ذاتي. هذا المشروع — الذي بنيتُه خلال 30 يومًا — هو أول نظام متعدد الوكلاء أنشره.

</div>

<br>

📧 [ahmadslike1@gmail.com](mailto:ahmadslike1@gmail.com)

[![GitHub](https://img.shields.io/badge/GitHub-Follow-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/AhmadSlik)
[![X / Twitter](https://img.shields.io/badge/X-Follow-000000?style=for-the-badge&logo=x&logoColor=white)](https://x.com/Ahmad_slik)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ahmad-slik-99661840b/)

</div>

---

<div align="center">

**MIT License** · © 2026 Ahmad Slik · بنيتُه في 30 يوم · v2.0.0 · نشرتُه. أتعلّم في العلن.

</div>

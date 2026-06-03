# Changelog

All notable changes to the Intelligent Research Assistant are documented here.
This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] — 2026-06-03

Day 30 release. 9 major features added across Days 21-29.

### Added

- **Multi-Model routing** (Day 21) — `backend/core/model_router.py`: dedicated free model per agent + `openrouter/auto` fallback on 429 / 402. Endpoint: `GET /api/models/info`.
- **Real Wikipedia scraping** (Day 22) — `backend/agents/web_scraper.py` + `backend/rag/source_cache.py`: AR + EN articles with in-memory source cache.
- **PDF upload + research** (Day 23) — `backend/agents/pdf_processor.py` + `backend/api/pdf.py`: `POST /pdf/upload` (extract + chunk into ChromaDB), `POST /pdf/research` (Reader → Analyst → Writer on PDF content).
- **FactChecker agent** (Day 24) — `backend/agents/fact_checker.py`: 5th pipeline agent. Returns `{ confidence: 0–1, flagged_claims: [...] }`.
- **Arabic UI polish** (Day 25) — Cairo font, full RTL layout, FactCheck card, responsive design.
- **Arabic source handling** (Day 26) — `backend/utils/arabic.py`: Alef normalization, diacritic removal, Wikipedia boilerplate stripping, AR Wikipedia fallback.
- **Streaming responses** (Day 28) — `POST /research/stream` via `ModelRouter.stream_chat()`. SSE format: `data: {"type": "token", "content": "..."}`.
- **Performance optimizations** (Day 29):
  - Parallel Reader via `asyncio.gather` in `backend/agents/reader.py`.
  - LRU embedding cache: `backend/rag/rag_engine.py::_encode_cached`.
  - Result cache: `backend/core/result_cache.py` — 10-min TTL, 64-entry cap.

### Changed

- Pipeline extended from **4 to 5 agents**: Researcher → Reader → Analyst → Writer → **FactChecker**.
- Writer adopts **academic writing style** (Day 27) — formal tone, structured Introduction / Main Findings / Contradictions / Conclusion, with numbered References.
- Reader now runs sources **in parallel** (was sequential).
- OpenRouter integration updated from single Gemini model to 5 dedicated free models.

### Fixed

- Arabic Wikipedia sources are now normalized (Alef variants, diacritics) before LLM processing, preventing tokenization noise.

---

## [1.0.0] — 2026-05-22

Initial public release after Day 20. 4-agent pipeline deployed on Railway + Netlify.

### Added

- 4-agent pipeline: Researcher → Reader → Analyst → Writer.
- `POST /research/full` — full pipeline endpoint returning JSON report.
- RAG endpoints: `POST /rag/add`, `POST /rag/search`, `GET /rag/count`.
- ChromaDB RAG memory with `all-MiniLM-L6-v2` sentence-transformers embeddings.
- Next.js 16 frontend with Arabic RTL single-page UI.
- Railway backend deployment (Nixpacks, `/health` healthcheck).
- Netlify frontend deployment (Next.js plugin, CDN).
- pytest test suite using `httpx` ASGI transport (no live server needed).

---

[2.0.0]: https://github.com/AhmadSlik/intelligent-research-assistant/releases/tag/v2.0.0
[1.0.0]: https://github.com/AhmadSlik/intelligent-research-assistant/releases/tag/v1.0.0

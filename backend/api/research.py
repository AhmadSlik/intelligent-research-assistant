import json
import logging
import uuid
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.researcher import ResearcherAgent, Source
from agents.reader import ReaderAgent, ReaderResult
from agents.analyst import AnalystAgent
from agents.writer import WriterAgent
from agents.fact_checker import FactCheckerAgent, FactCheckResult
from rag.rag_engine import add_document

logger = logging.getLogger("research_assistant")

# --- إنشاء الراوتر مع بادئة /research ---
router = APIRouter(prefix="/research", tags=["research"])


# --- نماذج البيانات للطلب والاستجابة ---

class FullResearchRequest(BaseModel):
    topic: str


class FullResearchResponse(BaseModel):
    topic: str
    report: str
    sources: list[Source]
    key_points_count: int
    fact_check: FactCheckResult | None = None


# --- نماذج البيانات لـ streaming ---

class StreamResearchRequest(BaseModel):
    topic: str


# --- نقطة النهاية: streaming عبر SSE ---

@router.post("/stream")
async def stream_research(request: StreamResearchRequest):
    topic = request.topic.strip()

    if not topic:
        raise HTTPException(status_code=400, detail="الموضوع لا يمكن أن يكون فارغاً.")

    async def event_generator() -> AsyncGenerator[bytes, None]:
        try:
            # 1) Researcher
            researcher = ResearcherAgent()
            research_result = await researcher.research(topic)
            sources = research_result.sources

            # 2) Reader
            reader = ReaderAgent()
            reader_results: list[ReaderResult] = []
            for source in sources:
                reader_text = source.content if source.content else source.summary
                reader_results.append(
                    await reader.read(text=reader_text, url=source.url)
                )

            # 3) Analyst
            analyst = AnalystAgent()
            analyst_result = await analyst.analyse(reader_results)

            # 4) Writer — stream tokens
            writer = WriterAgent()
            full_report = ""
            async for token in writer.stream_write(
                topic=topic,
                analyst_result=analyst_result,
                sources=sources,
            ):
                full_report += token
                payload = json.dumps(
                    {"type": "token", "content": token},
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n".encode("utf-8")

            # 5) FactChecker (non-fatal)
            fact_check_result: FactCheckResult | None = None
            try:
                fact_checker = FactCheckerAgent()
                fact_check_result = await fact_checker.check(
                    report=full_report, sources=sources,
                )
            except Exception as e:
                logger.warning(f"FactChecker failed in stream: {e}")

            # 6) RAG persist (non-fatal)
            try:
                doc_id = f"report_{topic.replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
                add_document(
                    doc_id=doc_id,
                    text=full_report,
                    metadata={"topic": topic, "sources_count": len(sources)},
                )
            except Exception:
                pass

            # 7) Done event
            done_payload = {
                "type": "done",
                "sources": [s.model_dump() for s in sources],
                "fact_check": fact_check_result.model_dump() if fact_check_result else None,
                "key_points_count": sum(len(r.key_points) for r in reader_results),
            }
            yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n".encode("utf-8")

        except Exception as e:
            logger.exception("Stream pipeline failed")
            err_payload = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n".encode("utf-8")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# --- نقطة النهاية الرئيسية: تشغيل خط الأنابيب كاملاً ---

@router.post("/full", response_model=FullResearchResponse)
async def full_research(request: FullResearchRequest):
    topic = request.topic.strip()

    # --- التحقق من أن الموضوع ليس فارغاً ---
    if not topic:
        raise HTTPException(status_code=400, detail="الموضوع لا يمكن أن يكون فارغاً.")

    # --- الخطوة 1: وكيل الباحث — جمع المصادر ---
    try:
        researcher = ResearcherAgent()
        research_result = await researcher.research(topic)
        sources = research_result.sources
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في وكيل الباحث: {e}")

    # --- الخطوة 2: وكيل القارئ — استخراج النقاط الرئيسية من كل مصدر ---
    try:
        reader = ReaderAgent()
        reader_results: list[ReaderResult] = []
        for source in sources:
            reader_text = source.content if source.content else source.summary
            result = await reader.read(text=reader_text, url=source.url)
            reader_results.append(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في وكيل القارئ: {e}")

    # --- الخطوة 3: وكيل المحلل — تلخيص النقاط وكشف التناقضات ---
    try:
        analyst = AnalystAgent()
        analyst_result = await analyst.analyse(reader_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في وكيل المحلل: {e}")

    # --- الخطوة 4: وكيل الكاتب — صياغة التقرير النهائي ---
    try:
        writer = WriterAgent()
        writer_result = await writer.write(
            topic=topic,
            analyst_result=analyst_result,
            sources=sources,
        )
        report = writer_result.report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في وكيل الكاتب: {e}")

    # --- الخطوة 5: وكيل المدقّق — التحقق من صحة التقرير مقابل المصادر ---
    fact_check_result: FactCheckResult | None = None
    try:
        fact_checker = FactCheckerAgent()
        fact_check_result = await fact_checker.check(report=report, sources=sources)
    except Exception as e:
        # فشل FactChecker لا يكسر الـpipeline — التقرير يُرجع بدون fact_check
        logger.warning(f"FactChecker failed, continuing without fact-check: {e}")

    # --- الخطوة 6: حفظ التقرير في ChromaDB عبر نظام RAG ---
    try:
        doc_id = f"report_{topic.replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        add_document(
            doc_id=doc_id,
            text=report,
            metadata={"topic": topic, "sources_count": len(sources)},
        )
    except Exception:
        # خطأ في الحفظ لا يوقف الاستجابة — نُرجع التقرير في كل الأحوال
        pass

    # --- حساب إجمالي عدد النقاط الرئيسية من جميع المصادر ---
    key_points_count = sum(len(r.key_points) for r in reader_results)

    return FullResearchResponse(
        topic=topic,
        report=report,
        sources=sources,
        key_points_count=key_points_count,
        fact_check=fact_check_result,
    )

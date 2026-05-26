import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.researcher import ResearcherAgent, Source
from agents.reader import ReaderAgent, ReaderResult
from agents.analyst import AnalystAgent
from agents.writer import WriterAgent
from rag.rag_engine import add_document

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

    # --- الخطوة 5: حفظ التقرير في ChromaDB عبر نظام RAG ---
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
    )

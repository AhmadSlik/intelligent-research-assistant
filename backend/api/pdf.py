import logging
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from agents.analyst import AnalystAgent
from agents.pdf_processor import PDFExtractionError, PDFProcessor
from agents.reader import ReaderAgent
from agents.researcher import Source
from agents.writer import WriterAgent
from rag.rag_engine import add_document_chunked, collection, model

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdf", tags=["pdf"])

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


class PdfResearchRequest(BaseModel):
    doc_id: str
    question: str


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    filename = file.filename or "uploaded.pdf"
    if not filename.lower().endswith(".pdf") and file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="يُقبل ملفات PDF فقط.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="حجم الملف يتجاوز 10 ميغابايت.")

    processor = PDFProcessor()
    try:
        text = processor.extract_text(file_bytes)
        meta = processor.extract_metadata(file_bytes)
    except PDFExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))

    doc_id = f"pdf_{uuid.uuid4().hex[:12]}"
    try:
        result = add_document_chunked(
            doc_id=doc_id,
            text=text,
            metadata={"source": "pdf", "filename": filename, "pages": meta["pages"]},
        )
    except Exception as e:
        logger.exception("ChromaDB add_document_chunked failed")
        raise HTTPException(status_code=500, detail=f"خطأ في تخزين الـPDF: {e}")

    return {
        "doc_id": doc_id,
        "filename": filename,
        "pages": meta["pages"],
        "chunks_count": result["total_chunks"],
        "preview": text[:500],
        "metadata": meta,
    }


@router.post("/research")
async def research_pdf(req: PdfResearchRequest):
    if not req.doc_id.strip() or not req.question.strip():
        raise HTTPException(status_code=400, detail="doc_id والسؤال مطلوبان.")

    # get the chunk count for this doc first so we don't exceed n_results
    try:
        existing = collection.get(
            where={"parent_doc_id": req.doc_id},
            include=["documents"],
        )
    except Exception as e:
        logger.exception("ChromaDB get failed")
        raise HTTPException(status_code=500, detail=f"خطأ في البحث: {e}")

    n_chunks = len(existing.get("documents") or [])
    if n_chunks == 0:
        raise HTTPException(
            status_code=404,
            detail="لم نجد محتوى لهذا الملف. تأكد من doc_id أو أعد رفع الـPDF.",
        )

    try:
        q_emb = model.encode(req.question).tolist()
        raw = collection.query(
            query_embeddings=[q_emb],
            n_results=min(5, n_chunks),
            where={"parent_doc_id": req.doc_id},
        )
    except Exception as e:
        logger.exception("ChromaDB query failed")
        raise HTTPException(status_code=500, detail=f"خطأ في البحث: {e}")

    docs = raw.get("documents", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]
    filename = (metas[0].get("filename") if metas else None) or "uploaded.pdf"
    combined_text = "\n\n".join(docs)

    try:
        reader_result = await ReaderAgent().read(text=combined_text, url=f"pdf://{filename}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في وكيل القارئ: {e}")

    try:
        analyst_result = await AnalystAgent().analyse([reader_result])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في وكيل المحلل: {e}")

    source = Source(title=filename, url=f"pdf://{filename}", summary=docs[0][:300])
    try:
        writer_result = await WriterAgent().write(
            topic=req.question,
            analyst_result=analyst_result,
            sources=[source],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في وكيل الكاتب: {e}")

    return {
        "doc_id": req.doc_id,
        "filename": filename,
        "question": req.question,
        "report": writer_result.report,
        "key_points": reader_result.key_points,
        "contradictions": analyst_result.contradictions,
        "chunks_used": len(docs),
    }

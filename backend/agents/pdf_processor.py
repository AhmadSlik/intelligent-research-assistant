import io
import logging

import pdfplumber

logger = logging.getLogger(__name__)

MAX_CHARS = 50_000


class PDFExtractionError(Exception):
    """رفع عند فشل الاستخراج أو عند PDF مسحي بلا نص."""


class PDFProcessor:
    """يستخرج النص و metadata من ملف PDF (bytes)."""

    def extract_text(self, file_bytes: bytes) -> str:
        text_parts: list[str] = []
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_parts.append(page_text)
        except Exception as e:
            logger.exception("PDF extract_text failed")
            raise PDFExtractionError(f"فشل قراءة الـPDF: {e}") from e

        full_text = "\n\n".join(text_parts).strip()
        if not full_text:
            raise PDFExtractionError(
                "لم نجد نصاً قابلاً للاستخراج. قد يكون الملف مسحاً ضوئياً (صور). "
                "يلزم OCR وهو غير مدعوم حالياً."
            )

        if len(full_text) > MAX_CHARS:
            logger.info("PDF text truncated from %d to %d chars", len(full_text), MAX_CHARS)
            full_text = full_text[:MAX_CHARS]
        return full_text

    def extract_metadata(self, file_bytes: bytes) -> dict:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                meta = pdf.metadata or {}
                return {
                    "pages": len(pdf.pages),
                    "title": (meta.get("Title") or "").strip() or None,
                    "author": (meta.get("Author") or "").strip() or None,
                    "file_size_kb": round(len(file_bytes) / 1024, 2),
                }
        except Exception as e:
            logger.exception("PDF extract_metadata failed")
            raise PDFExtractionError(f"فشل قراءة بيانات الـPDF: {e}") from e

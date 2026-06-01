import re
from pydantic import BaseModel

from agents.researcher import Source
from core.model_router import ModelRouter


# --- نماذج البيانات ---

class FactCheckResult(BaseModel):
    """النتيجة التي يُرجعها وكيل المدقّق."""
    confidence_score: int           # درجة الثقة في التقرير (0-100)
    verified_claims: list[str]      # ادعاءات مؤكدة من المصادر
    questionable_claims: list[str]  # ادعاءات غير مدعومة بالمصادر
    notes: str                      # ملاحظة عامة عن جودة التقرير


# --- وكيل المدقّق ---

class FactCheckerAgent:
    """
    الوكيل الخامس والأخير في خط أنابيب البحث.

    يأخذ تقرير وكيل الكاتب والمصادر الأصلية،
    يقارن الادعاءات الرئيسية في التقرير بما ورد فعلاً في المصادر،
    ويُرجع FactCheckResult يحتوي على درجة ثقة وقوائم الادعاءات.
    """

    def _build_prompt(self, report: str, sources: list[Source]) -> str:
        """
        بناء الطلب الذي سنرسله إلى النموذج.
        نُدرج التقرير كاملاً والمصادر مرقّمة، ونطلب تدقيقاً منظّماً.
        """
        # --- تجميع المصادر مرقّمة ---
        sources_text = ""
        for i, source in enumerate(sources, start=1):
            content_snippet = source.content or source.summary or "(no content available)"
            # نقتطع المحتوى الطويل تجنباً لتجاوز حدود الـcontext
            if len(content_snippet) > 800:
                content_snippet = content_snippet[:800] + "..."
            sources_text += (
                f"[{i}] {source.title} — {source.url}\n"
                f"Content: {content_snippet}\n\n"
            )

        return (
            "You are a fact-checking expert. Your task is to verify the claims made in a research report "
            "against the original sources provided.\n\n"
            "Steps:\n"
            "1. Identify the main factual claims in the report.\n"
            "2. Check each claim against the sources below.\n"
            "3. Classify each claim as VERIFIED (supported by sources) or QUESTIONABLE (not supported or contradicted).\n"
            "4. Give a confidence score (0-100) reflecting the overall reliability of the report "
            "(100 = fully supported, 0 = mostly unsupported).\n\n"
            "Use this EXACT format in your response (do not add anything before CONFIDENCE):\n\n"
            "CONFIDENCE: <number 0-100>\n\n"
            "VERIFIED CLAIMS:\n"
            "1. <first verified claim>\n"
            "2. <second verified claim>\n"
            "(Write 'None found.' if there are no verified claims.)\n\n"
            "QUESTIONABLE CLAIMS:\n"
            "1. <first questionable claim>\n"
            "(Write 'None found.' if there are no questionable claims.)\n\n"
            "NOTES:\n"
            "<one short paragraph about the overall quality and reliability of the report>\n\n"
            "---\n\n"
            f"REPORT TO VERIFY:\n{report}\n\n"
            f"ORIGINAL SOURCES:\n{sources_text}"
        )

    def _parse_response(
        self, raw: str
    ) -> tuple[int, list[str], list[str], str]:
        """
        تحليل رد النموذج واستخراج الأقسام الأربعة.
        يتعامل مع تنسيقات مختلفة ويُرجع قيماً افتراضية عند الفشل.
        """
        confidence = 50
        verified: list[str] = []
        questionable: list[str] = []
        notes = ""

        upper = raw.upper()
        conf_idx = upper.find("CONFIDENCE:")
        ver_idx = upper.find("VERIFIED CLAIMS:")
        que_idx = upper.find("QUESTIONABLE CLAIMS:")
        notes_idx = upper.find("NOTES:")

        # --- استخراج درجة الثقة ---
        if conf_idx != -1:
            # نأخذ النص بعد CONFIDENCE: حتى نهاية أول سطر
            end = raw.find("\n", conf_idx)
            conf_line = raw[conf_idx + len("CONFIDENCE:"):end if end != -1 else conf_idx + 20]
            # نبحث عن أي رقم في السطر
            numbers = re.findall(r"\d+", conf_line)
            if numbers:
                parsed = int(numbers[0])
                confidence = max(0, min(100, parsed))

        # --- دالة مساعدة لاستخراج قائمة مرقّمة من نص ---
        def extract_list(start_idx: int, end_idx: int) -> list[str]:
            if start_idx == -1:
                return []
            # تحديد حدود الكتلة
            block_start = start_idx + len("VERIFIED CLAIMS:")  # سيُعدَّل لاحقاً
            block = raw[block_start:end_idx if end_idx != -1 else len(raw)].strip()
            if "none found" in block.lower():
                return []
            items = []
            for line in block.splitlines():
                line = line.strip()
                if line and line[0].isdigit() and len(line) > 2:
                    rest = line[2:].strip() if line[1] in ".)" else line
                    if rest:
                        items.append(rest)
            return items

        # --- استخراج VERIFIED CLAIMS ---
        if ver_idx != -1:
            ver_block_start = ver_idx + len("VERIFIED CLAIMS:")
            ver_end = que_idx if que_idx != -1 else (notes_idx if notes_idx != -1 else len(raw))
            block = raw[ver_block_start:ver_end].strip()
            if "none found" not in block.lower():
                for line in block.splitlines():
                    line = line.strip()
                    if line and line[0].isdigit() and len(line) > 2:
                        rest = line[2:].strip() if line[1] in ".)" else line
                        if rest:
                            verified.append(rest)

        # --- استخراج QUESTIONABLE CLAIMS ---
        if que_idx != -1:
            que_block_start = que_idx + len("QUESTIONABLE CLAIMS:")
            que_end = notes_idx if notes_idx != -1 else len(raw)
            block = raw[que_block_start:que_end].strip()
            if "none found" not in block.lower():
                for line in block.splitlines():
                    line = line.strip()
                    if line and line[0].isdigit() and len(line) > 2:
                        rest = line[2:].strip() if line[1] in ".)" else line
                        if rest:
                            questionable.append(rest)

        # --- استخراج NOTES ---
        if notes_idx != -1:
            notes_block = raw[notes_idx + len("NOTES:"):].strip()
            notes = notes_block[:600]  # حدّ أقصى معقول

        # --- fallback إذا كان التنسيق غير صالح كلياً ---
        if not notes and conf_idx == -1:
            notes = raw.strip()[:500]

        return confidence, verified, questionable, notes

    async def check(
        self,
        report: str,
        sources: list[Source],
    ) -> FactCheckResult:
        """
        النقطة الرئيسية للدخول. تأخذ التقرير والمصادر وتُرجع FactCheckResult.

        الخطوات:
        1. بناء الطلب الذي يجمع التقرير والمصادر.
        2. إرسال الطلب إلى OpenRouter (نموذج fact_checker).
        3. تحليل الرد واستخراج الأقسام الأربعة.
        4. إرجاع FactCheckResult.
        """
        # --- بناء الطلب ---
        prompt = self._build_prompt(report, sources)

        # --- إرسال الطلب إلى OpenRouter ---
        raw_text = await ModelRouter.chat(
            agent_type="fact_checker",
            messages=[{"role": "user", "content": prompt}],
        )

        # --- تحليل الرد ---
        confidence, verified, questionable, notes = self._parse_response(raw_text)

        return FactCheckResult(
            confidence_score=confidence,
            verified_claims=verified,
            questionable_claims=questionable,
            notes=notes,
        )

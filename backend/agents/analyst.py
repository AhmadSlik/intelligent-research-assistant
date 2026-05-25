from pydantic import BaseModel

from agents.reader import ReaderResult
from core.model_router import ModelRouter


# --- نماذج البيانات ---

class AnalystResult(BaseModel):
    """النتيجة التي يُرجعها وكيل المحلل."""
    summary: str               # ملخص موحّد لجميع المصادر
    contradictions: list[str]  # قائمة التناقضات أو الاختلافات بين المصادر


# --- وكيل المحلل ---

class AnalystAgent:
    """
    الوكيل الثالث في خط أنابيب البحث.

    يقبل قائمة من ReaderResult (نتائج وكيل القارئ)،
    يقارن النقاط الرئيسية بين المصادر المختلفة،
    ويُرجع AnalystResult يحتوي على ملخص وقائمة التناقضات.
    """

    def _build_prompt(self, reader_results: list[ReaderResult]) -> str:
        """
        بناء الطلب الذي سنرسله إلى النموذج.
        نُدرج النقاط الرئيسية من كل مصدر، ونطلب ملخصاً وقائمة تناقضات.
        """
        # --- تجميع النقاط من كل مصدر في نص واحد ---
        sources_text = ""
        for i, result in enumerate(reader_results, start=1):
            sources_text += f"Source {i} ({result.source_url}):\n"
            for point in result.key_points:
                sources_text += f"  - {point}\n"
            sources_text += "\n"

        return (
            "You are a research analyst. Below are key points extracted from multiple sources.\n"
            "Your tasks:\n"
            "1. Write a short summary paragraph (3-5 sentences) that synthesizes the main ideas.\n"
            "2. List any contradictions or disagreements you find between the sources.\n\n"
            "Use this exact format in your response:\n"
            "SUMMARY:\n"
            "<your summary paragraph here>\n\n"
            "CONTRADICTIONS:\n"
            "1. <first contradiction>\n"
            "2. <second contradiction>\n"
            "(Write 'None found.' if there are no contradictions.)\n\n"
            f"Sources:\n{sources_text}"
        )

    def _parse_response(self, raw: str) -> tuple[str, list[str]]:
        """
        تحليل رد النموذج واستخراج الملخص وقائمة التناقضات.
        نبحث عن القسمين SUMMARY: و CONTRADICTIONS:.
        """
        summary = ""
        contradictions = []

        # --- تقسيم الرد إلى قسمين ---
        # نبحث عن الكلمتين المفتاحيتين بصرف النظر عن الأحرف الكبيرة والصغيرة
        upper = raw.upper()
        summary_idx = upper.find("SUMMARY:")
        contra_idx = upper.find("CONTRADICTIONS:")

        if summary_idx != -1 and contra_idx != -1:
            # استخراج نص الملخص بين القسمين
            summary_block = raw[summary_idx + len("SUMMARY:"):contra_idx].strip()
            summary = summary_block

            # استخراج نص التناقضات بعد CONTRADICTIONS:
            contra_block = raw[contra_idx + len("CONTRADICTIONS:"):].strip()

            # إذا لم توجد تناقضات
            if "none found" in contra_block.lower():
                contradictions = []
            else:
                # تحليل القائمة المرقّمة
                for line in contra_block.splitlines():
                    line = line.strip()
                    if line and line[0].isdigit() and len(line) > 2:
                        rest = line[2:].strip() if line[1] in ".)" else line
                        if rest:
                            contradictions.append(rest)
        else:
            # --- احتياط: إذا لم يلتزم النموذج بالتنسيق ---
            summary = raw.strip()

        return summary, contradictions

    async def analyse(self, reader_results: list[ReaderResult]) -> AnalystResult:
        """
        النقطة الرئيسية للدخول. تقبل نتائج وكيل القارئ وتُرجع AnalystResult.

        الخطوات:
        1. بناء الطلب الذي يجمع كل النقاط من كل المصادر.
        2. إرسال الطلب إلى OpenRouter.
        3. تحليل الرد واستخراج الملخص والتناقضات.
        4. إرجاع AnalystResult.
        """
        # --- بناء الطلب ---
        prompt = self._build_prompt(reader_results)

        # --- إرسال الطلب إلى OpenRouter ---
        raw_text = await ModelRouter.chat(
            agent_type="analyst",
            messages=[{"role": "user", "content": prompt}],
        )

        # --- تحليل الرد ---
        summary, contradictions = self._parse_response(raw_text)

        return AnalystResult(summary=summary, contradictions=contradictions)

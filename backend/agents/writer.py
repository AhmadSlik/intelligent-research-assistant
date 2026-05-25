from pydantic import BaseModel

from agents.analyst import AnalystResult
from agents.researcher import Source
from core.model_router import ModelRouter


# --- نماذج البيانات ---

class WriterResult(BaseModel):
    """النتيجة التي يُرجعها وكيل الكاتب."""
    report: str  # التقرير النهائي الكامل مع الاستشهادات


# --- وكيل الكاتب ---

class WriterAgent:
    """
    الوكيل الرابع والأخير في خط أنابيب البحث.

    يقبل الموضوع، نتيجة وكيل المحلل، وقائمة المصادر الأصلية،
    يطلب من OpenRouter كتابة تقرير بحثي منظّم مع استشهادات [1] [2] ...،
    ويُرجع WriterResult يحتوي على نص التقرير كاملاً.
    """

    def _build_prompt(
        self,
        topic: str,
        analyst_result: AnalystResult,
        sources: list[Source],
    ) -> str:
        """
        بناء الطلب الذي سنرسله إلى النموذج.
        نُدرج الموضوع، الملخص التحليلي، التناقضات، وقائمة المصادر مع أرقامها.
        """
        # --- تجميع المصادر مرقّمة ---
        sources_list = ""
        for i, source in enumerate(sources, start=1):
            sources_list += f"[{i}] {source.title} — {source.url}\n"

        # --- تجميع التناقضات ---
        if analyst_result.contradictions:
            contradictions_text = "\n".join(
                f"- {c}" for c in analyst_result.contradictions
            )
        else:
            contradictions_text = "No contradictions were found between the sources."

        return (
            f"You are an academic research writer. Write a well-structured research report on the topic: \"{topic}\".\n\n"
            "Use the following information as your basis:\n\n"
            f"ANALYST SUMMARY:\n{analyst_result.summary}\n\n"
            f"CONTRADICTIONS NOTED:\n{contradictions_text}\n\n"
            f"SOURCES:\n{sources_list}\n"
            "Instructions:\n"
            "- Structure the report with: Introduction, Main Findings, Contradictions & Debates, Conclusion.\n"
            "- Use inline citations like [1], [2], [3] when referencing the sources.\n"
            "- Write in clear, formal English.\n"
            "- The report should be 300-500 words.\n"
            "- End with a References section listing the sources.\n"
        )

    async def write(
        self,
        topic: str,
        analyst_result: AnalystResult,
        sources: list[Source],
    ) -> WriterResult:
        """
        النقطة الرئيسية للدخول. تقبل الموضوع ونتيجة المحلل والمصادر وتُرجع WriterResult.

        الخطوات:
        1. بناء الطلب الذي يجمع كل المعلومات.
        2. إرسال الطلب إلى OpenRouter.
        3. استلام التقرير النهائي كما هو من النموذج.
        4. إرجاع WriterResult.
        """
        # --- بناء الطلب ---
        prompt = self._build_prompt(topic, analyst_result, sources)

        # --- إرسال الطلب إلى OpenRouter ---
        report = await ModelRouter.chat(
            agent_type="writer",
            messages=[{"role": "user", "content": prompt}],
        )

        return WriterResult(report=report)

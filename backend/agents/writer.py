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
            f"You are an academic research writer. Write a rigorous, well-structured academic report on the topic: \"{topic}\".\n\n"
            "Use the following material as your basis:\n\n"
            f"ANALYST SUMMARY (numbered citable claims):\n{analyst_result.summary}\n\n"
            f"CONTRADICTIONS NOTED:\n{contradictions_text}\n\n"
            f"SOURCES:\n{sources_list}\n"
            "INSTRUCTIONS — follow exactly:\n\n"
            "1. STRUCTURE: Use exactly these six sections in this order, with Markdown ## headers:\n"
            "   ## Abstract\n"
            "   ## Introduction\n"
            "   ## Main Findings\n"
            "   ## Contradictions & Debates\n"
            "   ## Conclusion\n"
            "   ## References\n\n"
            "2. SECTION GUIDELINES:\n"
            "   - Abstract (80-120 words): Summarise the topic, research scope, key findings, and conclusion. No inline citations here.\n"
            "   - Introduction (60-90 words): Frame the topic and its significance.\n"
            "   - Main Findings (150-220 words): Present key findings. After every factual claim drawn from a source, place an inline citation [n] where n matches the source number listed above.\n"
            "   - Contradictions & Debates (50-100 words): Present the contradictions listed above in a neutral, academic tone. If no contradictions exist, write exactly: \"The reviewed sources are largely consistent on this topic.\"\n"
            "   - Conclusion (40-70 words): A measured synthesis. Introduce no new claims.\n"
            "   - References: A numbered list matching the citation numbers used in the report — format: [1] Title — URL\n\n"
            "3. CITATION RULES:\n"
            "   - Every factual claim must be followed by [n] matching its source number.\n"
            "   - Two supporting sources may be cited as [1, 2].\n"
            "   - Do not invent citation numbers beyond the sources provided.\n\n"
            "4. TONE: Formal academic English. Third person only. No first or second person (I, we, you). No rhetorical questions.\n\n"
            "5. TOTAL LENGTH: 400-600 words (Abstract through Conclusion, not counting the References list).\n"
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

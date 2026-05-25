from pydantic import BaseModel

from core.model_router import ModelRouter


# --- نماذج البيانات ---

class ReaderResult(BaseModel):
    """النتيجة التي يُرجعها وكيل القارئ لكل مصدر."""
    key_points: list[str]  # قائمة النقاط الرئيسية المستخرجة (3 نقاط عادةً)
    source_url: str        # رابط المصدر الأصلي


# --- وكيل القارئ ---

class ReaderAgent:
    """
    الوكيل الثاني في خط أنابيب البحث.

    يقبل نص المقال ورابطه، يرسلهما إلى OpenRouter،
    ويستخرج 3 نقاط رئيسية من المحتوى.
    يُرجع ReaderResult يحتوي على النقاط والرابط.
    """

    def _build_prompt(self, text: str) -> str:
        """
        بناء الرسالة التي سنرسلها إلى النموذج.
        نطلب منه استخراج 3 نقاط رئيسية بالضبط، مرقّمة.
        """
        return (
            "Read the following article text carefully.\n"
            "Extract exactly 3 key points from it.\n"
            "Format your response as a numbered list:\n"
            "1. First key point\n"
            "2. Second key point\n"
            "3. Third key point\n\n"
            "Do not add any introduction or conclusion — only the 3 numbered points.\n\n"
            f"Article text:\n{text}"
        )

    def _parse_response(self, raw: str) -> list[str]:
        """
        تحليل رد النموذج واستخراج النقاط الثلاث.
        نبحث عن أسطر تبدأ بـ 1. أو 2. أو 3.
        إذا لم يُرجع النموذج 3 نقاط، نُكمّل القائمة بعبارات افتراضية.
        """
        points = []
        for line in raw.strip().splitlines():
            line = line.strip()
            # نقبل أي سطر يبدأ برقم متبوع بنقطة أو قوس
            if line and line[0].isdigit() and len(line) > 2:
                # إزالة البادئة مثل "1. " أو "1) "
                rest = line[2:].strip() if line[1] in ".)" else line
                if rest:
                    points.append(rest)

        # --- التأكد من وجود 3 نقاط على الأقل ---
        while len(points) < 3:
            points.append("No additional key point extracted.")

        # نُرجع أول 3 نقاط فقط في حال أرجع النموذج أكثر
        return points[:3]

    async def read(self, text: str, url: str) -> ReaderResult:
        """
        النقطة الرئيسية للدخول. تقبل نص المقال ورابطه وتُرجع ReaderResult.

        الخطوات:
        1. بناء الطلب (prompt) المناسب.
        2. إرسال الطلب إلى OpenRouter.
        3. تحليل الرد واستخراج النقاط الثلاث.
        4. إرجاع ReaderResult.
        """
        # --- بناء الطلب ---
        prompt = self._build_prompt(text)

        # --- إرسال الطلب إلى OpenRouter ---
        raw_text = await ModelRouter.chat(
            agent_type="reader",
            messages=[{"role": "user", "content": prompt}],
        )

        # --- تحليل الرد ---
        key_points = self._parse_response(raw_text)

        return ReaderResult(key_points=key_points, source_url=url)

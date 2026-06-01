import logging

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "IntelligentResearchAssistant/0.1 (educational; accahmadff1@gmail.com)"
OPENSEARCH_URL = "https://{lang}.wikipedia.org/w/api.php"
TIMEOUT = 10.0
MAX_CONTENT_CHARS = 8000


class WikipediaUnavailable(Exception):
    """Raised when Wikipedia search cannot complete (network or import error)."""


class WikipediaScraper:

    def __init__(self):
        try:
            import wikipediaapi  # noqa: F401
            from langdetect import DetectorFactory
            DetectorFactory.seed = 0
            self._available = True
        except ImportError as e:
            logger.warning("WikipediaScraper deps missing: %s", e)
            self._available = False

    def _detect_lang(self, topic: str) -> str:
        if len(topic.strip()) < 3:
            return "en"
        try:
            from langdetect import detect
            code = detect(topic)
            return "ar" if code == "ar" else "en"
        except Exception:
            return "en"

    async def search(self, topic: str, lang: str = "auto", max_results: int = 3) -> list[dict]:
        if not self._available:
            raise WikipediaUnavailable("wikipedia-api or langdetect not installed")

        if lang == "auto":
            lang = self._detect_lang(topic)
        if lang not in ("ar", "en"):
            lang = "en"

        from utils.arabic import normalize_for_search, clean_arabic_text
        search_query = normalize_for_search(topic) if lang == "ar" else topic

        params = {
            "action": "opensearch",
            "search": search_query,
            "limit": max_results,
            "namespace": 0,
            "format": "json",
        }
        url = OPENSEARCH_URL.format(lang=lang)

        try:
            async with httpx.AsyncClient(
                timeout=TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            raise WikipediaUnavailable(f"OpenSearch request failed: {e}") from e

        # data = [query_string, [titles], [descriptions], [urls]]
        titles = data[1] if len(data) > 1 else []
        page_urls = data[3] if len(data) > 3 else []

        if not titles:
            return []

        import wikipediaapi
        wiki = wikipediaapi.Wikipedia(user_agent=USER_AGENT, language=lang)

        results = []
        for title, page_url in zip(titles, page_urls):
            try:
                page = wiki.page(title)
                if not page.exists():
                    continue
                summary = clean_arabic_text((page.summary or "").strip())
                content = clean_arabic_text((page.text or "").strip())
                if len(content) > MAX_CONTENT_CHARS:
                    content = content[:MAX_CONTENT_CHARS] + "..."
                results.append({
                    "title": page.title,
                    "url": page_url,
                    "summary": summary[:500] if summary else "(no summary)",
                    "content": content or summary,
                    "lang": lang,
                })
            except Exception as e:
                logger.warning("Failed to fetch Wikipedia page %r: %s", title, e)

        return results

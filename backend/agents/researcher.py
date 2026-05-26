import logging

from pydantic import BaseModel

from core.model_router import ModelRouter

logger = logging.getLogger(__name__)


# --- Pydantic Models ---

class Source(BaseModel):
    """Represents a single research source."""
    title: str
    url: str
    summary: str
    content: str | None = None
    lang: str | None = None


class ResearchResult(BaseModel):
    """The full result returned by the Researcher agent."""
    topic: str
    sources: list[Source]


# --- Hardcoded source templates ---
# Each entry uses {topic} and {topic_slug} as placeholders.
# {topic} = the original topic string (e.g. "artificial intelligence")
# {topic_slug} = topic with spaces replaced by underscores (e.g. "artificial_intelligence")

_SOURCE_TEMPLATES = [
    {
        "title": "Introduction to {topic} - Wikipedia",
        "url": "https://en.wikipedia.org/wiki/{topic_slug}",
        "summary": (
            "A comprehensive overview of {topic} covering its history, "
            "definition, and key concepts."
        ),
    },
    {
        "title": "{topic} Explained - Britannica",
        "url": "https://www.britannica.com/topic/{topic_slug}",
        "summary": (
            "An in-depth article on {topic} from Encyclopaedia Britannica, "
            "covering major developments and current understanding."
        ),
    },
    {
        "title": "Latest Research on {topic} - arXiv",
        "url": "https://arxiv.org/search/?query={topic_slug}&searchtype=all",
        "summary": (
            "Recent academic papers and findings related to {topic} "
            "from the arXiv preprint server."
        ),
    },
]


# --- Researcher Agent ---

class ResearcherAgent:
    """
    The first agent in the research pipeline.

    Accepts a topic, builds a list of relevant sources,
    and uses httpx to attempt fetching each URL.
    Returns a ResearchResult with source titles, URLs, and summaries.
    """

    model = ModelRouter.get_model("researcher")

    def _build_sources(self, topic: str) -> list[Source]:
        """Fill in the topic placeholders and return a list of Source objects."""
        topic_slug = topic.strip().replace(" ", "_")

        sources = []
        for template in _SOURCE_TEMPLATES:
            source = Source(
                title=template["title"].format(topic=topic, topic_slug=topic_slug),
                url=template["url"].format(topic=topic, topic_slug=topic_slug),
                summary=template["summary"].format(topic=topic, topic_slug=topic_slug),
            )
            sources.append(source)

        return sources

    async def research(self, topic: str) -> ResearchResult:
        try:
            from agents.web_scraper import WikipediaScraper, WikipediaUnavailable
            from rag.source_cache import get_cached_sources, set_cached_sources
        except Exception as e:
            logger.warning("Wikipedia path unavailable, using templates: %s", e)
            return ResearchResult(topic=topic, sources=self._build_sources(topic))

        scraper = WikipediaScraper()
        lang = scraper._detect_lang(topic) if scraper._available else "en"

        cached = get_cached_sources(topic, lang)
        if cached:
            logger.info("Cache HIT topic=%r lang=%s", topic, lang)
            return ResearchResult(topic=topic, sources=[Source(**s) for s in cached])

        try:
            raw = await scraper.search(topic, lang=lang, max_results=3)
        except WikipediaUnavailable as e:
            logger.warning("Wikipedia unavailable, falling back to templates: %s", e)
            return ResearchResult(topic=topic, sources=self._build_sources(topic))

        if not raw:
            logger.info("No Wikipedia results for %r — using templates", topic)
            return ResearchResult(topic=topic, sources=self._build_sources(topic))

        sources = [Source(**item) for item in raw]
        set_cached_sources(topic, lang, [s.model_dump() for s in sources])
        return ResearchResult(topic=topic, sources=sources)

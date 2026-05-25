import httpx
from pydantic import BaseModel

from core.model_router import ModelRouter


# --- Pydantic Models ---

class Source(BaseModel):
    """Represents a single research source."""
    title: str
    url: str
    summary: str


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
        """
        Main entry point. Accepts a research topic and returns a ResearchResult.

        Steps:
        1. Build the list of sources from templates.
        2. Use httpx to attempt a GET request to each URL.
           (If a URL is unreachable, we skip it silently — the source is still returned.)
        3. Return the ResearchResult.
        """
        sources = self._build_sources(topic)

        # Use an async HTTP client to fetch each URL.
        # timeout=5.0 means we wait at most 5 seconds per request.
        async with httpx.AsyncClient() as client:
            for source in sources:
                try:
                    await client.get(source.url, timeout=5.0)
                except Exception:
                    # URL might be unreachable in dev/offline environments — that's okay.
                    # We still include it in the results.
                    pass

        return ResearchResult(topic=topic, sources=sources)

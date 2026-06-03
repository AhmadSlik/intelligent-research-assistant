import logging
import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from openai import APIStatusError, AsyncOpenAI, RateLimitError

load_dotenv()

logger = logging.getLogger("research_assistant.model_router")

MODELS = {
    "researcher":   "meta-llama/llama-3.2-3b-instruct:free",
    "reader":       "google/gemma-4-31b-it:free",
    "analyst":      "deepseek/deepseek-v4-flash:free",
    "writer":       "qwen/qwen3-next-80b-a3b-instruct:free",
    "fact_checker": "meta-llama/llama-3.3-70b-instruct:free",
}

FALLBACK_MODELS = {agent: "openrouter/auto" for agent in MODELS}

_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)


class ModelRouter:

    @staticmethod
    def get_model(agent_type: str) -> str:
        return MODELS[agent_type]

    @staticmethod
    def get_with_fallback(agent_type: str) -> list[str]:
        return [MODELS[agent_type], FALLBACK_MODELS[agent_type]]

    @staticmethod
    def list_all() -> dict:
        return {
            "models": MODELS,
            "fallbacks": FALLBACK_MODELS,
            "chain": {a: ModelRouter.get_with_fallback(a) for a in MODELS},
        }

    @staticmethod
    async def stream_chat(
        agent_type: str,
        messages: list[dict],
    ) -> AsyncGenerator[str, None]:
        primary, fallback = ModelRouter.get_with_fallback(agent_type)
        logger.info("Agent %s streaming with model %s", agent_type, primary)
        try:
            stream = await _client.chat.completions.create(
                model=primary, messages=messages, stream=True,
            )
            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
        except (RateLimitError, APIStatusError) as e:
            logger.warning(
                "Rate limited on %s (error: %s), falling back to %s",
                primary, type(e).__name__, fallback,
            )
            stream = await _client.chat.completions.create(
                model=fallback, messages=messages, stream=True,
            )
            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta

    @staticmethod
    async def chat(agent_type: str, messages: list[dict]) -> str:
        primary, fallback = ModelRouter.get_with_fallback(agent_type)
        logger.info("Agent %s using model %s", agent_type, primary)
        try:
            response = await _client.chat.completions.create(
                model=primary,
                messages=messages,
            )
            return response.choices[0].message.content or ""
        except (RateLimitError, APIStatusError) as e:
            logger.warning(
                "Rate limited on %s (error: %s), falling back to %s",
                primary, type(e).__name__, fallback,
            )
            response = await _client.chat.completions.create(
                model=fallback,
                messages=messages,
            )
            return response.choices[0].message.content or ""

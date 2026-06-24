"""Shared OpenAI-compatible client construction, plus small one-off LLM helpers."""
import json

from openai import AsyncOpenAI

from app.config import get_settings

settings = get_settings()


def get_openai_client() -> AsyncOpenAI:
    client_kwargs = {"api_key": settings.openai_api_key}
    if settings.ai_base_url:
        client_kwargs["base_url"] = settings.ai_base_url
    return AsyncOpenAI(**client_kwargs)


async def generate_tags(title: str, content: str) -> list[str]:
    """Suggest 3-6 short tags for a note. Returns [] on any failure."""
    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.ai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Suggest 3-6 short, lowercase, relevant tags (1-2 words each) for the given note. "
                        'Respond with ONLY JSON: {"tags": ["tag1", "tag2"]}'
                    ),
                },
                {"role": "user", "content": f"Title: {title}\n\nContent: {content[:2000]}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        data = json.loads(response.choices[0].message.content)
        tags = data.get("tags", [])
        return [str(t).strip() for t in tags if str(t).strip()]
    except Exception:
        return []

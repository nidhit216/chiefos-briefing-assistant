import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import ai_client


def make_fake_client(content: str | None = None, raise_exc: Exception | None = None):
    client = MagicMock()
    if raise_exc is not None:
        client.chat.completions.create = AsyncMock(side_effect=raise_exc)
    else:
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content=content))]
        client.chat.completions.create = AsyncMock(return_value=response)
    return client


async def test_generate_tags_returns_parsed_tags(monkeypatch):
    fake = make_fake_client(json.dumps({"tags": ["roadmap", "planning"]}))
    monkeypatch.setattr(ai_client, "get_openai_client", lambda: fake)

    tags = await ai_client.generate_tags("Q3 roadmap", "Plan the roadmap for Q3.")

    assert tags == ["roadmap", "planning"]


async def test_generate_tags_strips_whitespace_and_drops_empty_entries(monkeypatch):
    fake = make_fake_client(json.dumps({"tags": ["  roadmap  ", "", "   ", "planning"]}))
    monkeypatch.setattr(ai_client, "get_openai_client", lambda: fake)

    tags = await ai_client.generate_tags("title", "content")

    assert tags == ["roadmap", "planning"]


async def test_generate_tags_coerces_non_string_entries(monkeypatch):
    fake = make_fake_client(json.dumps({"tags": [1, "two", 3.5]}))
    monkeypatch.setattr(ai_client, "get_openai_client", lambda: fake)

    tags = await ai_client.generate_tags("title", "content")

    assert tags == ["1", "two", "3.5"]


async def test_generate_tags_returns_empty_list_on_malformed_json(monkeypatch):
    fake = make_fake_client("not valid json {{{")
    monkeypatch.setattr(ai_client, "get_openai_client", lambda: fake)

    tags = await ai_client.generate_tags("title", "content")

    assert tags == []


async def test_generate_tags_returns_empty_list_when_tags_key_missing(monkeypatch):
    fake = make_fake_client(json.dumps({"unexpected": "shape"}))
    monkeypatch.setattr(ai_client, "get_openai_client", lambda: fake)

    tags = await ai_client.generate_tags("title", "content")

    assert tags == []


async def test_generate_tags_returns_empty_list_when_api_call_raises(monkeypatch):
    fake = make_fake_client(raise_exc=RuntimeError("upstream is down"))
    monkeypatch.setattr(ai_client, "get_openai_client", lambda: fake)

    tags = await ai_client.generate_tags("title", "content")

    assert tags == []


async def test_generate_tags_truncates_very_long_content(monkeypatch):
    fake = make_fake_client(json.dumps({"tags": ["x"]}))
    monkeypatch.setattr(ai_client, "get_openai_client", lambda: fake)

    await ai_client.generate_tags("title", "x" * 10_000)

    sent_messages = fake.chat.completions.create.call_args.kwargs["messages"]
    user_message = sent_messages[1]["content"]
    assert len(user_message) < 2100  # bounded even though content was 10k chars


def test_get_openai_client_includes_base_url_when_configured(monkeypatch):
    monkeypatch.setattr(ai_client.settings, "ai_base_url", "https://api.groq.com/openai/v1")
    monkeypatch.setattr(ai_client.settings, "openai_api_key", "test-key")
    captured = {}

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(ai_client, "AsyncOpenAI", FakeAsyncOpenAI)

    ai_client.get_openai_client()

    assert captured == {"api_key": "test-key", "base_url": "https://api.groq.com/openai/v1"}


def test_get_openai_client_omits_base_url_when_not_configured(monkeypatch):
    monkeypatch.setattr(ai_client.settings, "ai_base_url", None)
    monkeypatch.setattr(ai_client.settings, "openai_api_key", "test-key")
    captured = {}

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(ai_client, "AsyncOpenAI", FakeAsyncOpenAI)

    ai_client.get_openai_client()

    assert captured == {"api_key": "test-key"}

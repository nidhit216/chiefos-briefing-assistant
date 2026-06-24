import json
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.database import async_session
from app.models.daily_brief import DailyBrief
from app.models.memory import Memory
from app.routers import chat as chat_router


def fake_openai_client(reply="Hello from the assistant"):
    client = MagicMock()
    response = MagicMock()
    # tool_calls must be explicitly None — MagicMock auto-creates a (truthy) attribute
    # otherwise, which would make the chat loop think the model requested a tool call.
    response.choices = [MagicMock(message=MagicMock(content=reply, tool_calls=None))]
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


def patch_chat_deps(monkeypatch, context="No relevant context found.", reply="Hello from the assistant"):
    fake_client = fake_openai_client(reply)
    monkeypatch.setattr(chat_router, "get_relevant_context", AsyncMock(return_value=context))
    monkeypatch.setattr(chat_router, "get_openai_client", lambda: fake_client)
    return fake_client


def fake_openai_client_with_tool_call(tool_content, final_reply="Got it."):
    """First response requests `save_memory`; second (post tool-result) response is the final reply."""
    tool_call = MagicMock(id="call_1")
    tool_call.function.name = "save_memory"
    tool_call.function.arguments = json.dumps({"content": tool_content})

    tool_call_response = MagicMock()
    tool_call_response.choices = [MagicMock(message=MagicMock(tool_calls=[tool_call]))]

    final_response = MagicMock()
    final_response.choices = [MagicMock(message=MagicMock(content=final_reply, tool_calls=None))]

    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=[tool_call_response, final_response])
    return client


def patch_chat_deps_with_tool_call(monkeypatch, tool_content, final_reply="Got it.", context="No relevant context found."):
    fake_client = fake_openai_client_with_tool_call(tool_content, final_reply)
    monkeypatch.setattr(chat_router, "get_relevant_context", AsyncMock(return_value=context))
    monkeypatch.setattr(chat_router, "get_openai_client", lambda: fake_client)
    return fake_client


async def test_chat_creates_new_session_when_none_provided(client, monkeypatch):
    patch_chat_deps(monkeypatch, context="No relevant context found.", reply="Hi there")

    res = await client.post("/chat/", json={"message": "What's on my plate today?"})

    assert res.status_code == 200
    data = res.json()
    assert data["reply"] == "Hi there"
    assert data["sources_used"] == 0
    uuid.UUID(data["session_id"])  # does not raise


async def test_chat_persists_user_and_assistant_messages(client, test_user, monkeypatch):
    patch_chat_deps(monkeypatch, reply="Sure, here's a summary")

    res = await client.post("/chat/", json={"message": "Summarize my day"})
    session_id = res.json()["session_id"]

    history_res = await client.get("/chat/history", params={"session_id": session_id})
    history = history_res.json()
    assert [h["role"] for h in history] == ["user", "assistant"]
    assert history[0]["content"] == "Summarize my day"
    assert history[1]["content"] == "Sure, here's a summary"


async def test_chat_reuses_provided_session_id_and_includes_prior_history(client, monkeypatch):
    fake_client = patch_chat_deps(monkeypatch, reply="first reply")
    first = await client.post("/chat/", json={"message": "first message"})
    session_id = first.json()["session_id"]

    fake_client2 = patch_chat_deps(monkeypatch, reply="second reply")
    second = await client.post(
        "/chat/", json={"message": "second message", "session_id": session_id}
    )

    assert second.status_code == 200
    assert second.json()["session_id"] == session_id

    sent_messages = fake_client2.chat.completions.create.call_args.kwargs["messages"]
    contents = [m["content"] for m in sent_messages]
    assert "first message" in contents
    assert "first reply" in contents
    assert "second message" in contents


async def test_chat_sources_used_counts_context_chunks(client, monkeypatch):
    context = "chunk one\n\n---\n\nchunk two\n\n---\n\nchunk three"
    patch_chat_deps(monkeypatch, context=context)

    res = await client.post("/chat/", json={"message": "anything"})

    assert res.json()["sources_used"] == 3


async def test_chat_injects_todays_brief_into_prompt(client, test_user, monkeypatch):
    async with async_session() as session:
        session.add(
            DailyBrief(
                id=uuid.uuid4(),
                user_id=test_user.id,
                brief_date=date.today(),
                content='{"priorities": ["Ship the launch"]}',
            )
        )
        await session.commit()

    fake_client = patch_chat_deps(monkeypatch)
    await client.post("/chat/", json={"message": "what should I focus on"})

    sent_messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
    system_message = sent_messages[0]["content"]
    assert "Ship the launch" in system_message


async def test_chat_missing_message_field_returns_422(client):
    res = await client.post("/chat/", json={})
    assert res.status_code == 422


async def test_chat_history_for_unknown_session_returns_empty_list(client):
    res = await client.get("/chat/history", params={"session_id": str(uuid.uuid4())})
    assert res.status_code == 200
    assert res.json() == []


async def test_chat_save_memory_tool_call_persists_memory_and_returns_final_reply(
    client, test_user, monkeypatch
):
    patch_chat_deps_with_tool_call(
        monkeypatch, tool_content="Prefers async standups on Mondays.", final_reply="Noted!"
    )

    res = await client.post(
        "/chat/", json={"message": "Remember that I prefer async standups on Mondays"}
    )

    assert res.status_code == 200
    assert res.json()["reply"] == "Noted!"

    async with async_session() as session:
        from sqlalchemy import select

        result = await session.execute(select(Memory).where(Memory.user_id == test_user.id))
        memories = result.scalars().all()
    assert [m.content for m in memories] == ["Prefers async standups on Mondays."]


async def test_chat_injects_existing_memories_into_system_prompt(client, test_user, monkeypatch):
    async with async_session() as session:
        session.add(Memory(user_id=test_user.id, content="Lives in Tokyo."))
        await session.commit()

    fake_client = patch_chat_deps(monkeypatch)
    await client.post("/chat/", json={"message": "What timezone am I in?"})

    sent_messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
    system_message = sent_messages[0]["content"]
    assert "Lives in Tokyo." in system_message


async def test_chat_history_without_session_id_summarizes_distinct_sessions(client, monkeypatch):
    patch_chat_deps(monkeypatch, reply="reply A")
    session_a = (await client.post("/chat/", json={"message": "message A"})).json()["session_id"]

    patch_chat_deps(monkeypatch, reply="reply B")
    session_b = (await client.post("/chat/", json={"message": "message B"})).json()["session_id"]

    res = await client.get("/chat/history")

    assert res.status_code == 200
    session_ids = {s["session_id"] for s in res.json()}
    assert {session_a, session_b}.issubset(session_ids)

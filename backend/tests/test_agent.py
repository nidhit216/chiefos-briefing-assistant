"""Tests for the agent brief generator's token-saving behavior: pre-fetched
baseline context (no tool round-trip needed), truncated search results, and a
bounded tool surface / loop length."""
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from app.database import async_session
from app.models.calendar_event import CalendarEvent
from app.models.email import Email
from app.models.note import Note
from app.services import agent


MINIMAL_BRIEF_JSON = {
    "executive_summary": "Good morning.",
    "attention_required": [],
    "recommendations": {},
    "focus_breakdown": [],
}


def fake_agent_client_with(brief_json):
    """No tool calls — the agent loop exits immediately with the final JSON brief."""
    client = MagicMock()
    response = MagicMock()
    response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(brief_json), tool_calls=None))
    ]
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


def fake_agent_client_always_calling_tools():
    """Every response requests a tool call and has no content — used to exercise
    the loop's iteration cap and the structured-output fallback it falls through to."""
    tool_call = MagicMock(id="call_1")
    tool_call.function.name = "search_emails"
    tool_call.function.arguments = json.dumps({"query": "anything"})
    tool_call_response = MagicMock(
        choices=[MagicMock(message=MagicMock(tool_calls=[tool_call], content=None))]
    )
    fallback_response = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps(MINIMAL_BRIEF_JSON)))]
    )

    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=[tool_call_response, tool_call_response, tool_call_response, fallback_response]
    )
    return client


def test_agent_tools_expose_only_search_functions():
    """get_upcoming_events / get_recent_emails / get_all_notes were removed in favor
    of pre-fetched baseline context — only dynamic search tools should remain."""
    tool_names = {t["function"]["name"] for t in agent.AGENT_TOOLS}
    assert tool_names == {"search_emails", "search_calendar", "search_notes"}


async def test_generate_brief_with_agent_injects_baseline_context_without_tool_calls(test_user, monkeypatch):
    async with async_session() as session:
        session.add(CalendarEvent(
            user_id=test_user.id,
            google_event_id=f"evt-{uuid.uuid4().hex}",
            title="Board meeting",
            start_time=datetime.now(timezone.utc) + timedelta(hours=2),
            end_time=datetime.now(timezone.utc) + timedelta(hours=3),
            attendees="ceo@example.com",
        ))
        session.add(Email(
            user_id=test_user.id,
            gmail_message_id=f"msg-{uuid.uuid4().hex}",
            sender="boss@example.com",
            subject="Re: Q3 plan",
            snippet="Let's lock the roadmap",
            received_at=datetime.now(timezone.utc),
        ))
        session.add(Note(user_id=test_user.id, title="Idea", content="Ship the new pricing page"))
        await session.commit()

    fake_client = fake_agent_client_with(MINIMAL_BRIEF_JSON)
    monkeypatch.setattr(agent, "get_openai_client", lambda: fake_client)

    async with async_session() as session:
        await agent.generate_brief_with_agent(test_user, session)

    sent_messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
    system_message = sent_messages[0]["content"]
    assert "Board meeting" in system_message
    assert "Q3 plan" in system_message
    assert "Ship the new pricing page" in system_message
    # Baseline data came from the pre-fetch, not a tool round-trip.
    assert fake_client.chat.completions.create.await_count == 1


async def test_execute_tool_truncates_search_result_content(test_user, monkeypatch):
    long_content = "x" * 1000
    monkeypatch.setattr(
        agent,
        "semantic_search",
        AsyncMock(return_value=[{"content": long_content, "source_type": "email"}]),
    )

    async with async_session() as session:
        result_json = await agent._execute_tool("search_emails", {"query": "anything"}, test_user, session)

    result = json.loads(result_json)
    assert len(result[0]["content"]) == agent.SEARCH_CONTENT_CHAR_CAP


async def test_agent_loop_stops_after_max_iterations_and_falls_back_to_structured_output(test_user, monkeypatch):
    fake_client = fake_agent_client_always_calling_tools()
    monkeypatch.setattr(agent, "get_openai_client", lambda: fake_client)
    monkeypatch.setattr(agent, "semantic_search", AsyncMock(return_value=[]))

    async with async_session() as session:
        brief = await agent.generate_brief_with_agent(test_user, session)

    # 3 loop iterations (each returning a tool call) + 1 structured-output fallback call.
    assert fake_client.chat.completions.create.await_count == 4
    assert json.loads(brief.content)["executive_summary"] == "Good morning."

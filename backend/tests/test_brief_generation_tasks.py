"""Confirms generate_brief / generate_brief_with_agent persist BriefTask rows, not just the DailyBrief blob."""
import json
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select

from app.database import async_session
from app.models.brief_task import BriefTask
from app.services import planner, agent


BRIEF_JSON = {
    "executive_summary": "Good morning. Today is about the launch.",
    "attention_required": ["File the report"],
    "recommendations": {"morning": "Ship the launch", "afternoon": "Review feedback", "evening": "Wrap up"},
}

AGENT_BRIEF_JSON = {
    "executive_summary": "Good morning. Today is about the launch.",
    "attention_required": ["Invoice from Acme is overdue"],
    "recommendations": {"morning": "Ship the launch", "afternoon": "Review feedback", "evening": "Wrap up"},
}


def fake_simple_client():
    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=json.dumps(BRIEF_JSON)))]
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


def fake_agent_client_with(brief_json):
    """No tool calls — the agent loop exits immediately with the final JSON brief."""
    client = MagicMock()
    response = MagicMock()
    response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(brief_json), tool_calls=None))
    ]
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


async def test_generate_brief_persists_brief_tasks(test_user, monkeypatch):
    monkeypatch.setattr(planner, "get_openai_client", fake_simple_client)

    async with async_session() as session:
        await planner.generate_brief(test_user, session)

    async with async_session() as session:
        result = await session.execute(select(BriefTask).where(BriefTask.user_id == test_user.id))
        tasks = result.scalars().all()

    by_category = {t.category: t.task for t in tasks}
    assert by_category["attention_required"] == "File the report"


async def test_generate_brief_with_agent_persists_brief_tasks(test_user, monkeypatch):
    monkeypatch.setattr(agent, "get_openai_client", lambda: fake_agent_client_with(AGENT_BRIEF_JSON))

    async with async_session() as session:
        await agent.generate_brief_with_agent(test_user, session)

    async with async_session() as session:
        result = await session.execute(select(BriefTask).where(BriefTask.user_id == test_user.id))
        tasks = result.scalars().all()

    by_category = {t.category: t.task for t in tasks}
    assert by_category["attention_required"] == "Invoice from Acme is overdue"


async def test_generate_brief_with_agent_persists_executive_summary_and_recommendations(test_user, monkeypatch):
    monkeypatch.setattr(agent, "get_openai_client", lambda: fake_agent_client_with(AGENT_BRIEF_JSON))

    async with async_session() as session:
        brief = await agent.generate_brief_with_agent(test_user, session)

    saved = json.loads(brief.content)
    assert saved["executive_summary"] == AGENT_BRIEF_JSON["executive_summary"]
    assert saved["recommendations"] == AGENT_BRIEF_JSON["recommendations"]

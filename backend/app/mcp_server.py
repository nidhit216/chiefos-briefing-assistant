"""MCP Server — exposes ChiefOS data as tools for external AI agents (Claude, Cursor, etc.)."""
import json
import asyncio
from datetime import date, datetime, timezone

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.user import User
from app.models.email import Email
from app.models.calendar_event import CalendarEvent
from app.models.note import Note
from app.models.daily_brief import DailyBrief
from app.services.rag import semantic_search

server = Server("chiefos")


async def _get_user_by_email(email: str) -> User | None:
    """Get user by email address."""
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_todays_brief",
            description="Get today's AI-generated daily briefing for a user. Returns an executive summary, items needing attention, and a recommended schedule.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_email": {"type": "string", "description": "The user's email address"},
                },
                "required": ["user_email"],
            },
        ),
        Tool(
            name="search_emails",
            description="Semantic search across a user's emails. Returns relevant emails ranked by similarity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_email": {"type": "string", "description": "The user's email address"},
                    "query": {"type": "string", "description": "What to search for"},
                    "limit": {"type": "integer", "description": "Max results (default 5)"},
                },
                "required": ["user_email", "query"],
            },
        ),
        Tool(
            name="search_notes",
            description="Semantic search across a user's personal notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_email": {"type": "string", "description": "The user's email address"},
                    "query": {"type": "string", "description": "What to search for"},
                    "limit": {"type": "integer", "description": "Max results (default 5)"},
                },
                "required": ["user_email", "query"],
            },
        ),
        Tool(
            name="get_upcoming_events",
            description="Get upcoming calendar events for a user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_email": {"type": "string", "description": "The user's email address"},
                    "limit": {"type": "integer", "description": "Max events (default 10)"},
                },
                "required": ["user_email"],
            },
        ),
        Tool(
            name="get_notes",
            description="Get all personal notes for a user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_email": {"type": "string", "description": "The user's email address"},
                },
                "required": ["user_email"],
            },
        ),
        Tool(
            name="get_recent_emails",
            description="Get the most recent emails for a user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_email": {"type": "string", "description": "The user's email address"},
                    "limit": {"type": "integer", "description": "Max emails (default 20)"},
                },
                "required": ["user_email"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    user_email = arguments.get("user_email", "")
    user = await _get_user_by_email(user_email)
    if not user:
        return [TextContent(type="text", text=f"Error: No user found with email '{user_email}'")]

    async with async_session() as db:
        if name == "get_todays_brief":
            result = await db.execute(
                select(DailyBrief).where(
                    DailyBrief.user_id == user.id,
                    DailyBrief.brief_date == date.today(),
                ).order_by(DailyBrief.created_at.desc()).limit(1)
            )
            brief = result.scalar_one_or_none()
            if brief:
                return [TextContent(type="text", text=brief.content)]
            return [TextContent(type="text", text="No brief generated for today yet.")]

        elif name == "search_emails":
            results = await semantic_search(
                arguments["query"], user.id, db,
                source_type="email", limit=arguments.get("limit", 5)
            )
            return [TextContent(type="text", text=json.dumps(results, indent=2))]

        elif name == "search_notes":
            results = await semantic_search(
                arguments["query"], user.id, db,
                source_type="note", limit=arguments.get("limit", 5)
            )
            return [TextContent(type="text", text=json.dumps(results, indent=2))]

        elif name == "get_upcoming_events":
            limit = arguments.get("limit", 10)
            result = await db.execute(
                select(CalendarEvent)
                .where(CalendarEvent.user_id == user.id)
                .where(CalendarEvent.start_time >= datetime.now(timezone.utc))
                .order_by(CalendarEvent.start_time.asc())
                .limit(limit)
            )
            events = result.scalars().all()
            data = [
                {"title": e.title, "start": str(e.start_time), "end": str(e.end_time), "attendees": e.attendees}
                for e in events
            ]
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        elif name == "get_notes":
            result = await db.execute(
                select(Note).where(Note.user_id == user.id).order_by(Note.updated_at.desc())
            )
            notes = result.scalars().all()
            data = [
                {"title": n.title, "content": n.content, "tags": n.tags, "updated_at": str(n.updated_at)}
                for n in notes
            ]
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        elif name == "get_recent_emails":
            limit = arguments.get("limit", 20)
            result = await db.execute(
                select(Email).where(Email.user_id == user.id).order_by(Email.received_at.desc()).limit(limit)
            )
            emails = result.scalars().all()
            data = [
                {"sender": e.sender, "subject": e.subject, "snippet": e.snippet, "received_at": str(e.received_at)}
                for e in emails
            ]
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def run_mcp_server():
    """Run the MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(run_mcp_server())

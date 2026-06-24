"""MCP integrations management — register/list/test external MCP servers."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.mcp_integrations import mcp_client

router = APIRouter()


class MCPServerConfig(BaseModel):
    name: str
    command: str
    args: list[str] = []
    env: dict[str, str] = {}


class MCPServerInfo(BaseModel):
    name: str
    command: str
    tools: list[dict] = []


@router.post("/register")
async def register_mcp_server(
    config: MCPServerConfig,
    user: User = Depends(get_current_user),
):
    """Register an external MCP server (Jira, Slack, Notion, etc.)."""
    mcp_client.register_server(config.name, config.command, config.args, config.env)
    return {"status": "registered", "name": config.name}


@router.get("/servers", response_model=list[str])
async def list_registered_servers(
    user: User = Depends(get_current_user),
):
    """List all registered external MCP servers."""
    return list(mcp_client.connections.keys())


@router.get("/servers/{name}/tools")
async def list_server_tools(
    name: str,
    user: User = Depends(get_current_user),
):
    """List available tools from a registered MCP server."""
    if name not in mcp_client.connections:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not registered")
    tools = await mcp_client.list_tools(name)
    return tools


@router.post("/servers/{name}/call")
async def call_server_tool(
    name: str,
    tool_name: str,
    arguments: dict = {},
    user: User = Depends(get_current_user),
):
    """Call a tool on a registered external MCP server."""
    if name not in mcp_client.connections:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not registered")
    result = await mcp_client.call_tool(name, tool_name, arguments)
    return {"result": result}

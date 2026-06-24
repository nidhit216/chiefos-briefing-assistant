import pytest
from unittest.mock import AsyncMock

from app.services.mcp_integrations import mcp_client


@pytest.fixture(autouse=True)
def _isolate_mcp_client_state():
    """mcp_client is a process-wide singleton — snapshot/restore its registry per test."""
    original = dict(mcp_client.connections)
    yield
    mcp_client.connections.clear()
    mcp_client.connections.update(original)


async def test_register_server_adds_it_to_the_registry(client):
    res = await client.post(
        "/mcp/register",
        json={"name": "jira", "command": "npx", "args": ["jira-mcp"], "env": {"TOKEN": "abc"}},
    )

    assert res.status_code == 200
    assert res.json() == {"status": "registered", "name": "jira"}
    assert "jira" in mcp_client.connections


async def test_register_server_with_minimal_payload_defaults_args_and_env(client):
    res = await client.post("/mcp/register", json={"name": "slack", "command": "slack-mcp"})

    assert res.status_code == 200
    assert mcp_client.connections["slack"] == {"command": "slack-mcp", "args": [], "env": {}}


async def test_list_registered_servers_returns_registered_names(client):
    await client.post("/mcp/register", json={"name": "jira", "command": "jira-mcp"})
    await client.post("/mcp/register", json={"name": "notion", "command": "notion-mcp"})

    res = await client.get("/mcp/servers")

    assert res.status_code == 200
    assert set(res.json()) == {"jira", "notion"}


async def test_list_tools_for_unregistered_server_returns_404(client):
    res = await client.get("/mcp/servers/not-registered/tools")
    assert res.status_code == 404


async def test_call_tool_for_unregistered_server_returns_404(client):
    res = await client.post(
        "/mcp/servers/not-registered/call",
        params={"tool_name": "anything"},
        json={},
    )
    assert res.status_code == 404


async def test_list_tools_for_registered_server_delegates_to_mcp_client(client, monkeypatch):
    await client.post("/mcp/register", json={"name": "jira", "command": "jira-mcp"})
    monkeypatch.setattr(
        mcp_client, "list_tools", AsyncMock(return_value=[{"name": "list_issues", "description": "List issues"}])
    )

    res = await client.get("/mcp/servers/jira/tools")

    assert res.status_code == 200
    assert res.json() == [{"name": "list_issues", "description": "List issues"}]


async def test_call_tool_for_registered_server_returns_wrapped_result(client, monkeypatch):
    await client.post("/mcp/register", json={"name": "jira", "command": "jira-mcp"})
    monkeypatch.setattr(mcp_client, "call_tool", AsyncMock(return_value="3 open issues"))

    res = await client.post(
        "/mcp/servers/jira/call",
        params={"tool_name": "list_issues"},
        json={"project": "ENG"},
    )

    assert res.status_code == 200
    assert res.json() == {"result": "3 open issues"}

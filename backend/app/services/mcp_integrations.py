"""External MCP client — connects to external MCP servers (Jira, Slack, Notion, etc.) to pull additional context."""
import json
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from app.config import get_settings

settings = get_settings()


class ExternalMCPClient:
    """Client that connects to external MCP servers to fetch data for briefs."""

    def __init__(self):
        self.connections: dict[str, dict] = {}

    def register_server(self, name: str, command: str, args: list[str] | None = None, env: dict | None = None):
        """Register an external MCP server to connect to."""
        self.connections[name] = {
            "command": command,
            "args": args or [],
            "env": env or {},
        }

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        """Call a tool on an external MCP server."""
        if server_name not in self.connections:
            return json.dumps({"error": f"Server '{server_name}' not registered"})

        conn = self.connections[server_name]
        server_params = StdioServerParameters(
            command=conn["command"],
            args=conn["args"],
            env=conn["env"],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                # Extract text content
                texts = [c.text for c in result.content if hasattr(c, "text")]
                return "\n".join(texts) if texts else ""

    async def list_tools(self, server_name: str) -> list[dict]:
        """List available tools from an external MCP server."""
        if server_name not in self.connections:
            return []

        conn = self.connections[server_name]
        server_params = StdioServerParameters(
            command=conn["command"],
            args=conn["args"],
            env=conn["env"],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [
                    {"name": t.name, "description": t.description}
                    for t in tools.tools
                ]

    async def gather_external_context(self) -> str:
        """Gather context from all registered external MCP servers for brief generation."""
        context_parts = []

        for name, conn in self.connections.items():
            try:
                tools = await self.list_tools(name)
                # Try common patterns for each integration type
                for tool in tools:
                    if any(keyword in tool["name"].lower() for keyword in ["list", "get", "fetch", "assigned"]):
                        try:
                            result = await self.call_tool(name, tool["name"], {})
                            if result:
                                context_parts.append(f"[{name} - {tool['name']}]\n{result[:2000]}")
                        except Exception:
                            continue
            except Exception:
                continue

        return "\n\n---\n\n".join(context_parts) if context_parts else ""


# Singleton instance
mcp_client = ExternalMCPClient()

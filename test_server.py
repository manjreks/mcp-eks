import asyncio
import os

# server.py reads these settings when it is imported: the Cognito values for
# the Step 9c version, or MCP_API_TOKEN for the Step 9a version. Dummy values
# are fine, because the in-memory client below talks to the server object
# directly and skips HTTP authentication, so Cognito is never contacted.
os.environ.setdefault("COGNITO_REGION", "us-east-1")
os.environ.setdefault("COGNITO_USER_POOL_ID", "us-east-1_TEST")
os.environ.setdefault("COGNITO_CLIENT_IDS", "test-client")
os.environ.setdefault("MCP_API_TOKEN", "test-token")

from mcp import Client  # noqa: E402
from server import mcp  # noqa: E402


async def _check_tools():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        assert {t.name for t in tools.tools} == {"add", "greet"}

        result = await client.call_tool("add", {"a": 2, "b": 3})
        assert result.content[0].text == "5"

        result = await client.call_tool("greet", {"name": "CI"})
        assert "Hello, CI!" in result.content[0].text


def test_tools():
    asyncio.run(_check_tools())
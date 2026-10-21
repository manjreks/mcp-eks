import asyncio, os, sys
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
 
TOKEN_URL = (f"https://{os.environ['COGNITO_DOMAIN']}.auth."
             f"{os.environ['AWS_REGION']}.amazoncognito.com/oauth2/token")
 
async def get_token() -> str:
    async with httpx2.AsyncClient() as http:
        r = await http.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials", "scope": "mcp-api/tools"},
            auth=(os.environ["COGNITO_CLIENT_ID"],
                  os.environ["COGNITO_CLIENT_SECRET"]),
        )
        r.raise_for_status()
        return r.json()["access_token"]
 
async def main(url: str):
    token = await get_token()
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx2.Timeout(30.0, read=300.0),
    ) as http:
        async with Client(streamable_http_client(url, http_client=http)) as client:
            tools = await client.list_tools()
            print("Tools:", [t.name for t in tools.tools])
            r = await client.call_tool("add", {"a": 2, "b": 3})
            print("add(2,3) =", r.content[0].text)
 
if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
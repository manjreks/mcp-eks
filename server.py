import asyncio, os
import jwt
from jwt import PyJWKClient
from pydantic import AnyHttpUrl
from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from starlette.requests import Request
from starlette.responses import JSONResponse
 
PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8000")
RESOURCE = f"{PUBLIC_URL}/mcp"
 
REGION = os.environ["COGNITO_REGION"]
POOL_ID = os.environ["COGNITO_USER_POOL_ID"]
ALLOWED_CLIENT_IDS = set(os.environ["COGNITO_CLIENT_IDS"].split(","))
REQUIRED_SCOPE = os.environ.get("REQUIRED_SCOPE", "mcp-api/tools")
 
ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{POOL_ID}"
jwks = PyJWKClient(f"{ISSUER}/.well-known/jwks.json", cache_keys=True)
 
class CognitoTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            # Fetching signing keys is blocking I/O (cached after first call)
            key = await asyncio.to_thread(
                lambda: jwks.get_signing_key_from_jwt(token).key)
            claims = jwt.decode(
                token, key,
                algorithms=["RS256"],
                issuer=ISSUER,
                options={"verify_aud": False,   # Cognito access tokens have no "aud"
                         "require": ["exp", "iss", "token_use", "client_id"]},
            )
        except jwt.PyJWTError:
            return None
 
        if claims["token_use"] != "access":     # reject ID tokens
            return None
        if claims["client_id"] not in ALLOWED_CLIENT_IDS:
            return None
 
        return AccessToken(
            token=token,
            client_id=claims["client_id"],
            subject=claims.get("sub"),
            scopes=claims.get("scope", "").split(),
            expires_at=claims["exp"],
            resource=RESOURCE,  # Cognito has no resource claim; the checks above bind it
        )
 
mcp = MCPServer(
    "demo-server",
    version="1.0.0",
    token_verifier=CognitoTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(ISSUER),
        resource_server_url=AnyHttpUrl(RESOURCE),
        required_scopes=[REQUIRED_SCOPE],
        validate_token_resource=True,
    ),
)
 
 
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
 
@mcp.tool()
def greet(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}! Greetings from EKS."
 
# Plain HTTP endpoint for Kubernetes health probes
@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})
 
if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",   # MCP endpoint is served at /mcp
        host="0.0.0.0",                # listen on all interfaces inside the container
        port=8000,
        stateless_http=True,           # no sticky sessions, so multiple replicas work
        json_response=True,            # plain JSON responses
    )

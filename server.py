
import hashlib
from contextvars import ContextVar

from mcp.server.fastmcp import FastMCP

# Store the challenge for each incoming request
current_challenge = ContextVar("current_challenge", default=None)

EMAIL = "24f3004475@ds.study.iitm.ac.in".strip().lower()


from mcp.server.transport_security import TransportSecuritySettings

mcp = FastMCP(
    "Exam Challenge Server",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        allowed_hosts=[
            "live-mcp-server-i7s9.onrender.com"
        ],
        allowed_origins=[
            "https://live-mcp-server-i7s9.onrender.com"
        ]
    )
)



class ChallengeHeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        challenge = headers.get(
            b"x-exam-challenge", b""
        ).decode("ascii")

        token = current_challenge.set(challenge or None)

        try:
            await self.app(scope, receive, send)
        finally:
            current_challenge.reset(token)


@mcp.tool()
def solve_challenge() -> str:
    """Calculate the answer for the current exam challenge."""

    challenge = current_challenge.get()

    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    text_to_hash = f"{challenge}:{EMAIL}"

    result = hashlib.sha256(
        text_to_hash.encode("utf-8")
    ).hexdigest()

    return result[:16]



from starlette.responses import JSONResponse

mcp_app = mcp.streamable_http_app()


async def health(request):
    return JSONResponse({"status": "ok"})


from starlette.routing import Route

mcp_app.routes.append(Route("/health", health, methods=["GET", "HEAD"]))

app = ChallengeHeaderMiddleware(mcp_app)


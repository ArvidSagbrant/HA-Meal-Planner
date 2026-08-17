"""ASGI middleware used at the Home Assistant Ingress boundary."""

from starlette.types import ASGIApp, Receive, Scope, Send


class NormalizeIngressPathMiddleware:
    """Collapse duplicate leading slashes before FastAPI route matching.

    Home Assistant Ingress can combine its entry path and the requested path
    into values such as ``//api/meals``. Starlette intentionally treats that as
    distinct from ``/api/meals``, so normalize only the leading separators and
    leave the rest of the URL untouched.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in {"http", "websocket"}:
            path = scope.get("path", "")
            normalized_path = f"/{path.lstrip('/')}"
            if normalized_path != path:
                scope = dict(scope)
                scope["path"] = normalized_path
                if isinstance(scope.get("raw_path"), bytes):
                    scope["raw_path"] = normalized_path.encode("utf-8")
        await self.app(scope, receive, send)

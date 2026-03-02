"""Request-level middleware: i18n via Accept-Language."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from cfd.i18n.translator import set_language


class I18nMiddleware(BaseHTTPMiddleware):
    """Set language from Accept-Language header per request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = getattr(request.app.state, "settings", None)
        default_lang = getattr(settings, "default_language", "ua") if settings else "ua"
        lang_header = request.headers.get("accept-language", "")
        if lang_header.lower().startswith("en"):
            set_language("en")
        else:
            set_language(default_lang)
        return await call_next(request)

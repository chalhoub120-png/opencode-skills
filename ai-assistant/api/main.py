"""FastAPI application entry point.

The chat path in `llm.router` is the single brain shared by every client: the
chatbox-ai UI proxies to it, so task routing, model fallback and
authentication exist in exactly one place.

The enterprise endpoints (voice, agents, knowledge, memory, admin) are
mounted on the same app so a single process serves the whole product.
"""

from __future__ import annotations

import importlib
import logging
import os

from llm.router import app

logger = logging.getLogger(__name__)


def _mount(module_name: str, attribute: str) -> bool:
    """Mount an optional router.

    The voice, knowledge and admin routers pull in optional dependencies
    (faster-whisper, Qdrant, PostgreSQL). A missing optional dependency must
    never take the chat path down, so a failed mount is logged and skipped.
    """
    try:
        module = importlib.import_module(module_name)
        app.include_router(getattr(module, attribute))
        return True
    except Exception as exc:  # noqa: BLE001 - optional routers must not break boot
        logger.warning("Optional router %s not mounted: %s", module_name, exc)
        return False


_mount("api.voice", "router")
_mount("api.enterprise", "router")
_mount("api.admin", "router")
_mount("api.notifications", "router")

# The dashboard is a static single-page app served by the same process.
_DASHBOARD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard"
)
if os.path.isdir(_DASHBOARD):
    from fastapi.staticfiles import StaticFiles

    app.mount(
        "/dashboard",
        StaticFiles(directory=_DASHBOARD, html=True),
        name="dashboard",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

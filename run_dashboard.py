"""Production entrypoint for Buffett BOT dashboard."""

from __future__ import annotations

import os

from waitress import serve

from web_dashboard import app


if __name__ == "__main__":
    host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    port = int(os.getenv("DASHBOARD_PORT", "8080"))
    serve(app, host=host, port=port)

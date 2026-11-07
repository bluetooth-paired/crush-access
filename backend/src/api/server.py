"""独立部署入口：python -m api.server 或 uvicorn api.server:app"""
from __future__ import annotations

import os

import uvicorn

from api.app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info"),
    )

from __future__ import annotations

import argparse

import uvicorn

from .config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NiuQI2D FastAPI service.")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    host = args.host or settings.host
    port = args.port or settings.port
    uvicorn.run("fastapi_app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()

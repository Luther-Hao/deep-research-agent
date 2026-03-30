"""
Deep Research Agent — FastAPI server entry point.

Start:
    python main.py
    # or
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Then open http://localhost:8000 for the web UI.
API docs: http://localhost:8000/docs
"""

import logging
import os

import uvicorn

from src.app.api import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[logging.StreamHandler()],
)

app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)

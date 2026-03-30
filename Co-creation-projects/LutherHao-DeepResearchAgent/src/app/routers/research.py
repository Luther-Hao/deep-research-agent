import json
import logging
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agents.agent import run_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


class ResearchRequest(BaseModel):
    query: str
    max_plan_iterations: int = 1
    max_step_num: int = 3
    enable_background_investigation: bool = True


@router.post("/stream")
async def research_stream(req: ResearchRequest):
    """SSE endpoint — streams agent events as newline-delimited JSON."""

    async def event_generator():
        try:
            async for event in run_stream(
                user_input=req.query,
                max_plan_iterations=req.max_plan_iterations,
                max_step_num=req.max_step_num,
                enable_background_investigation=req.enable_background_investigation,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"research_stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

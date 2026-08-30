from fastapi import APIRouter, Depends, Response

from app.safety.rate_limits import block_limited_user, read_limited_user, report_limited_user
from app.safety.schemas import AppealCreate, BlockCreate, ReportCreate
from app.safety.service import (
    create_appeal,
    create_block,
    create_report,
    list_blocks,
    list_moderation_decisions,
    remove_block,
)

router = APIRouter(prefix="/safety", tags=["safety"])


@router.get("/blocks")
def get_blocks(user_id: str = Depends(read_limited_user)) -> list[dict[str, object]]:
    return list_blocks(user_id)


@router.post("/blocks", status_code=201)
def post_block(payload: BlockCreate, user_id: str = Depends(block_limited_user)) -> dict[str, object]:
    return create_block(user_id, payload.user_id)


@router.delete("/blocks/{blocked_user_id}", status_code=204)
def delete_block(blocked_user_id: str, user_id: str = Depends(block_limited_user)) -> Response:
    remove_block(user_id, blocked_user_id)
    return Response(status_code=204)


@router.post("/reports", status_code=201)
def post_report(payload: ReportCreate, user_id: str = Depends(report_limited_user)) -> dict[str, object]:
    return create_report(user_id, payload)


@router.get("/moderation-decisions")
def get_moderation_decisions(user_id: str = Depends(read_limited_user)) -> list[dict[str, object]]:
    return list_moderation_decisions(user_id)


@router.post("/appeals", status_code=201)
def post_appeal(payload: AppealCreate, user_id: str = Depends(report_limited_user)) -> dict[str, object]:
    return create_appeal(user_id, payload.report_id, payload.statement)

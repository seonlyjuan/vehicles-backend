from fastapi import APIRouter, Depends, Query

from app.moderation.rate_limits import moderator_limited_user
from app.moderation.schemas import AppealDecision, DealerDecision, ReportDecision
from app.moderation.appeals import decide_appeal, list_open_appeals
from app.moderation.dealers import decide_dealer, list_pending_dealers
from app.moderation.service import (
    decide_report,
    list_reports,
)

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.get("/reports")
def get_reports(
    status: str | None = Query(default="open", pattern=r"^(open|reviewing|resolved|rejected)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    _: str = Depends(moderator_limited_user),
) -> dict[str, object]:
    return list_reports(status, page, per_page)


@router.patch("/reports/{report_id}")
def patch_report(
    report_id: str,
    payload: ReportDecision,
    moderator_id: str = Depends(moderator_limited_user),
) -> dict[str, object]:
    return decide_report(report_id, moderator_id, payload)


@router.get("/dealers")
def get_pending_dealers(_: str = Depends(moderator_limited_user)) -> list[dict[str, object]]:
    return list_pending_dealers()


@router.patch("/dealers/{user_id}")
def patch_dealer(
    user_id: str,
    payload: DealerDecision,
    moderator_id: str = Depends(moderator_limited_user),
) -> dict[str, object]:
    return decide_dealer(user_id, moderator_id, payload)


@router.get("/appeals")
def get_appeals(_: str = Depends(moderator_limited_user)) -> list[dict[str, object]]:
    return list_open_appeals()


@router.patch("/appeals/{appeal_id}")
def patch_appeal(
    appeal_id: str,
    payload: AppealDecision,
    moderator_id: str = Depends(moderator_limited_user),
) -> dict[str, object]:
    return decide_appeal(appeal_id, moderator_id, payload)

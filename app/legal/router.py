from fastapi import APIRouter, Depends

from app.legal.rate_limits import read_limited_user
from app.legal.service import get_current_terms

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/terms/current")
def get_current_terms_document(_: str = Depends(read_limited_user)) -> dict[str, object]:
    document = get_current_terms()
    return {
        "version": document["version"],
        "display_version": document["display_version"],
        "title": document["title"],
        "public_path": document["public_path"],
        "status": document["status"],
        "effective_from": document.get("effective_from"),
    }

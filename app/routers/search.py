from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.models import User
from app.schemas.search import GlobalSearchResponse
from app.services.insights import global_search

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/", response_model=GlobalSearchResponse)
async def search_all(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await global_search(db, current_user.id, q)


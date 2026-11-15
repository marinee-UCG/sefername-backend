from fastapi import APIRouter,Depends

from app.models.user import User
from app.schemas.news import NewsItem

from app.core.deps import get_current_user

from app.services.news import get_headlines

router=APIRouter(prefix="/news",tags=["news"])


@router.get("",response_model=list[NewsItem])
def get_news(
    current_user:User=Depends(get_current_user)
):
    return get_headlines()
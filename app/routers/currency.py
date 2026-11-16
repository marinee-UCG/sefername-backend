from fastapi import APIRouter,Depends,HTTPException,status

from app.models.user import User
from app.schemas.currency import CurrencyRate,CurrencyRateOut

from app.core.deps import get_current_user

from app.services.currency import fetch_rates_xml,parse_rates,get_rates

router=APIRouter(prefix="/currency",tags=["currency"])

@router.get("",response_model=CurrencyRateOut)
def get_currency(current_user:User=Depends(get_current_user)):
    rates=get_rates()
    if rates is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,detail="Rates are not available right now.")
    return rates


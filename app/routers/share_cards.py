from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.contract import Contract
from app.models.voyage import Voyage
from app.routers.contracts import get_user_contract_or_404
from app.schemas.share_card import HomewardCardOut,EospCardOut,CospCardOut
from app.services.share_cards import homeward_card,eosp_card,cosp_card
from app.routers.voyages import get_user_voyage_or_404


router=APIRouter(prefix="/share-cards",tags=["share-cards"])


@router.get("/contracts/{contract_id}/homeward",response_model=HomewardCardOut)
def get_homeward_card(
    contract:Contract=Depends(get_user_contract_or_404),
    db:Session=Depends(get_db),
):
    if contract.end_date is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This contract is still active. Its card is ready after sign-off.",
        )
    query=select(Voyage).where(Voyage.contract_id==contract.id).options(
        selectinload(Voyage.from_port),
        selectinload(Voyage.to_port),
    )
    voyages=db.scalars(query).all()
    return homeward_card(contract,voyages)

@router.get("/voyages/{voyage_id}/eosp",response_model=EospCardOut)
def get_eosp_card(
    voyage:Voyage=Depends(get_user_voyage_or_404),
    db:Session=Depends(get_db)
):
    if voyage.eosp_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This voyage is still active. Card will be ready after EOSP"
        )
    query=select(Voyage).where(Voyage.contract_id==voyage.contract_id).options(
        selectinload(Voyage.from_port),
        selectinload(Voyage.to_port),
    )
    voyages=db.scalars(query).all()
    return eosp_card(voyage,voyages)


@router.get("/voyages/{voyage_id}/cosp", response_model=CospCardOut)
def get_cosp_card(
    voyage: Voyage = Depends(get_user_voyage_or_404),
    db: Session = Depends(get_db),
):
    # Allowed while under way too: the card never shows the route or the destination
    query = select(Voyage).where(Voyage.contract_id == voyage.contract_id)
    return cosp_card(voyage, db.scalars(query).all())

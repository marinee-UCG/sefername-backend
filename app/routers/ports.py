from fastapi import APIRouter,Depends,Query

from sqlalchemy import select,or_,case,union
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.port import Port
from app.schemas.port import PortOut
from app.models.voyage import Voyage

router=APIRouter(prefix="/ports",tags=["ports"])

@router.get("",response_model=list[PortOut])
def search_ports(
    q:str=Query(min_length=2,max_length=50),
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    from_ports=select(Voyage.from_port_id).where(Voyage.user_id==current_user.id)
    to_ports=select(Voyage.to_port_id).where(Voyage.user_id==current_user.id)
    my_ports=union(from_ports,to_ports)

    match_rank=case(
        (Port.locode.ilike(q),0),
        (Port.id.in_(my_ports),1),
        (Port.name.ilike(f"{q}%"),2),
        else_=3
    )
    query=(
        select(Port)
        .where(or_(
            Port.name.ilike(f"%{q}%"),
            Port.locode.ilike(f"{q}%")
            
        ))
        .order_by(match_rank,Port.name)
        .limit(15)
    )
    return db.scalars(query).all()
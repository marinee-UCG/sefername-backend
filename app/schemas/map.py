from pydantic import BaseModel

from app.schemas.port import PortOut
from app.schemas.voyage import VoyageOut


class MapVoyage(VoyageOut):

    coordinates:list[tuple[float,float]]=[]

class MapPosition(BaseModel):

    lat:float
    lon:float
    approximate:bool=True

class MapTotals(BaseModel):

    voyages:int
    distance_nm:float
    ports:int

class MapOut(BaseModel):

    voyages:list[MapVoyage]
    ports:list[PortOut]
    position:MapPosition | None
    totals:MapTotals

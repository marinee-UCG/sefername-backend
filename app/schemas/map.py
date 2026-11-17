from pydantic import AwareDatetime,BaseModel

from app.schemas.port import PortOut
from app.schemas.voyage import VoyageOut


class MapNoon(BaseModel):
    lat:float
    lon:float
    recorded_at:AwareDatetime
    distance_nm:float | None
    wind_bft:int | None
    wind_dir_deg:int | None
    wave_m:float | None


class MapCrossing(BaseModel):
    key:str
    name:str
    lat:float
    lon:float


class MapVoyage(VoyageOut):

    coordinates:list[tuple[float,float]]=[]
    # The voyage's noon positions with their weather, oldest first (only the user sees these)
    noons:list[MapNoon]=[]
    crossings:list[MapCrossing]=[]

class MapPosition(BaseModel):

    lat:float
    lon:float
    progress:int
    eta:AwareDatetime
    approximate:bool=True
   

class MapTotals(BaseModel):

    voyages:int
    distance_nm:float
    ports:int

class MapArea(BaseModel):
    name:str
    # lon_min, lon_max, lat_min, lat_max
    box:list[float]
    nm:int
    days:float
    voyages:int


class MapOut(BaseModel):

    voyages:list[MapVoyage]
    ports:list[PortOut]
    position:MapPosition | None
    totals:MapTotals
    # Every sea area, most specific first, with the user's days and miles there
    areas:list[MapArea]=[]

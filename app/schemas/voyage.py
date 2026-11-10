from pydantic import BaseModel,ConfigDict,AwareDatetime

from app.schemas.port import PortOut


class VoyageCreate(BaseModel):
    contract_id:int
    from_port_id:int
    to_port_id:int
    cosp_at:AwareDatetime
    eosp_at:AwareDatetime|None=None

class VoyageEosp(BaseModel):
    eosp_at:AwareDatetime

class VoyageUpdate(BaseModel):
    # Corrections only: the contract stays, and an active voyage still ends with EOSP
    from_port_id:int|None=None
    to_port_id:int|None=None
    cosp_at:AwareDatetime|None=None
    eosp_at:AwareDatetime|None=None

class VoyageOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)

    id:int
    contract_id:int
    vessel_name:str
    from_port:PortOut
    to_port: PortOut
    cosp_at:AwareDatetime
    eosp_at:AwareDatetime | None = None
    is_active:bool
    distance_nm:float |None = None

  
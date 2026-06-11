from pydantic import BaseModel

class SaveLocalRequest(BaseModel):
    trabajador_id: int
    huella_template: str

class OfflineAttendanceRequest(BaseModel):
    trabajador_id: int

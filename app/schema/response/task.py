from pydantic import BaseModel
from datetime import datetime

class JobInfo(BaseModel):
    job_id: str
    job_type: str
    message: dict
    date_queues: datetime
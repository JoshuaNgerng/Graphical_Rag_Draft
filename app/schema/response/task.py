from pydantic import BaseModel

class TaskInfo(BaseModel):
    task_id: str
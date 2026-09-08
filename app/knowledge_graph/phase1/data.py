from pydantic import BaseModel
from app.models.entity_relationship import GraphObservationNormalize
from app.models.documents import ChunkData

class Phase1Summary(BaseModel):
    chunk: ChunkData
    observations: GraphObservationNormalize

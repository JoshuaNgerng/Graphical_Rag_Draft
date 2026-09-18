from pydantic import BaseModel, ConfigDict, Field

class Node(BaseModel):
    id: str

class Document(Node):
    pass

class ChunkData(BaseModel):
    text: str
    chunk_index: int
    page_start: int = 0
    page_end: int = 0
    section: str | None = None

    model_config = ConfigDict(from_attributes=True)

class Chunk(ChunkData):
    chunk_id: str
    document_id: str = Field(serialization_alias="doc_id")
    embedding: list[float] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
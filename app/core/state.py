
from wrapt import lru_cache

from app.core.config import Config
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from app.neo4j_graphrag.RelationshipExtractorOllama import RelationshipExtractorOllama

class State:
    def __init__(self, config: Config) -> None:
        # Startup Neo4j Driver
        self.driver = GraphDatabase.driver(
            config.DRIVER_URL,
            auth=("neo4j", config.DRIVER_PASSWORD)
        )

        self.database_name = config.DRIVER_DATABASE

        # Startup Ollama Extractor
        self.extractor = RelationshipExtractorOllama(config)

        # Startup Embedding model
        self.model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)

    def transfer(self, state):
        for key, value in self.__dict__.items():
            setattr(state, key, value)

@lru_cache
def get_state(config: Config):
        return State(config)
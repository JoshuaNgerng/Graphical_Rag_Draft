
from functools import lru_cache

from app.core.config import Config, get_config
from neo4j import GraphDatabase
from ollama.Embedding import Embedding
from app.neo4j_graphrag.RelationshipExtractorOllama import RelationshipExtractorOllama

class State:
    def __init__(self, config: Config) -> None:
        # Startup Neo4j Driver
        self.driver = GraphDatabase.driver(
            config.DRIVER_URL,
            auth=("neo4j", config.DRIVER_PASSWORD)
        )

        self.database_name = config.DRIVER_DATABASE

        self.embedding = Embedding(config)

        # Startup Ollama Extractor
        self.extractor = RelationshipExtractorOllama(config)

    def transfer(self, state):
        for key, value in self.__dict__.items():
            setattr(state, key, value)

@lru_cache
def get_state():
    return State(get_config())
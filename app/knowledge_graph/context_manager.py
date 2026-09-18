from app.core.config import Config
from app.llm_service.ollama.embedding import Embedding
from app.neo4j.driver import Neo4jDriver
from app.postgres.session import Postgres
from app.knowledge_graph.phase1.extraction import RelationExtractor
from app.knowledge_graph.phase2.entity_resolver import EntityResolver
from app.knowledge_graph.phase2.retrival import RetrievalCandidates
from app.knowledge_graph.phase2.entity_repo import EntityRepo
from app.knowledge_graph.phase3.relationship_resolver import RelationshipResolver
from app.knowledge_graph.phase3.relationship_validator import RelationshipValidator

class DataProcessingContext:
    def __init__(self, config: Config) -> None:
        self.embedding = Embedding(config)
        self.driver = Neo4jDriver(config)
        self.extractor = RelationExtractor(config)
        self.entity_resolver = EntityResolver(config)
        self.retrieval = RetrievalCandidates(self.driver, self.embedding)
        self.entity_repo = EntityRepo(self.driver, self.embedding)
        self.relationship_resolver = RelationshipResolver(config)
        self.relationship_validator = RelationshipValidator(config)
        self.db = Postgres().init(config)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.embedding.close()
        self.driver.close()
        self.extractor.close()
        self.entity_resolver.close()
        self.relationship_resolver.close()
        self.relationship_validator.close()
        self.db.close()

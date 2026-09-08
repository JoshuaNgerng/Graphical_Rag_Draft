from app.knowledge_graph.phase2.entity_resolver import Decision
from app.models.entity_relationship import EntityNode
from app.neo4j.driver import Neo4jDriver
from app.ollama.embedding import Embedding


class EntityRepo:
    def __init__(self, driver: Neo4jDriver, embed: Embedding) -> None:
        self.driver = driver
        self.embed = embed

    def resolve_entity_decision(
            self, candidates: list[EntityNode], decision: Decision
        ):
        match decision.decision:
            case "MERGE": 
                return self.merge_entity(decision, candidates)
            case "CREATE":
                return self.create_new_entity(decision)
            case "UNKNOWN":
                return None # skip for now
            case _:
                raise RuntimeError("Unknown decision")

    def save_new_entity_bulk(self, changed_entity: list[EntityNode]):
        self.driver.save_entities(entities=changed_entity)

    def merge_entity(self, decision: Decision, candidates: list[EntityNode]):
        id_ = decision.entity_id
        if not id_:
            return # error
        found_candidate = None
        for c in candidates:
            if c.id == id_:
                found_candidate = c
        if not found_candidate:
            return # error
        if decision.add_alias:
            check_unique = set(found_candidate.alias)
            check_unique.update(decision.add_alias)
            found_candidate.alias = list(check_unique)
        found_candidate.embedding = list(self.embed.encode(found_candidate.repr_self_text()))
        return found_candidate
        
    def create_new_entity(self, decision: Decision):
        res = EntityNode(
            id=f"{decision.entity_type}:{decision.canonical_name.strip().lower()}",
            name=decision.canonical_name,
            type=decision.entity_type,
            description=decision.description,
            alias=decision.add_alias,
            embedding=[]
        )
        res.embedding = list(self.embed.encode(res.repr_self_text()))
        return res
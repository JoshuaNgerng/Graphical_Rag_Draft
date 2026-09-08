import re
import unicodedata
from uuid import uuid4
from typing import TYPE_CHECKING
from pydantic import (
    AliasChoices, BaseModel, ConfigDict, 
    Field, field_validator, model_validator
)
from app.models.documents import Chunk, Node

if TYPE_CHECKING:
    from app.models.observations import (
        RelationshipObservation, ClaimNode
    )

# base model

class Entity(BaseModel):
    name: str
    type: str = Field(
        validation_alias=AliasChoices(
            "entity_type", "canonical_type"
        )
    )
    description: str

class Relationship(BaseModel):
    type: str = Field(validation_alias="relationship_type")
    # relationship_type = relationship.type.strip().upper()

    @field_validator('type', mode='after')
    @classmethod
    def normalize_type(cls, val):
        val = normalize_name(val)
        return val.upper()

class RelationshipType(BaseModel):
    description: str
    source_type: str | None = Field(default=None)
    target_type: str | None = Field(default=None)
    embedding: list[float] = Field(default_factory=list)

class EntityNormalize(Entity):
    normalize_name: str = ''

    @model_validator(mode="after")
    def generate_normalize_name(self):
        if self.normalize_name == '':
            self.normalize_name = normalize_name(self.name) 
        return self

class EntityNode(Node, EntityNormalize):
    alias: list[str]
    embedding: list[float]

    def repr_self_text(self):
        return (
f"""
ID: {self.id}
Name: {self.name}
Type: {self.type}
Description: {self.description}
Aliases: {", ".join(self.alias)}
"""
        )

class RelationshipNode(Node, Relationship):
    source_id: str
    target_id: str

class RelationshipTypeNode(Node, RelationshipType):
    pass

# llm facing

def resolve_relationship_claims(
        chunk_info: Chunk | str,
        relationships: list[RelationshipObservation],
        entity_ids_mapping: dict[str, str]
) -> tuple[list[RelationshipNode], list[ClaimNode]]:
    chunk_id = (
        chunk_info.chunk_id 
        if isinstance(chunk_info, Chunk) 
        else chunk_info
    )
    relationships_res : list[RelationshipNode]= []
    claims_res : list[ClaimNode] = []
    visted_relationships : set[tuple[str, str, str]] = set()
    for r in relationships:
        source_id = entity_ids_mapping.get(r.source, None)
        target_id = entity_ids_mapping.get(r.target, None)
        if source_id is None or target_id is None: continue
        key = (r.type, source_id, target_id)
        relationship_id = f"{source_id}:{r.type}:{target_id}"
        if key not in visted_relationships:
            visted_relationships.add(key)
            relationships_res.append(
                RelationshipNode(
                    id=relationship_id,
                    type=r.type,
                    source_id=source_id,
                    target_id=target_id
                )
            )
        claims_res.append(
            ClaimNode(
                id=f'{chunk_id}:{str(uuid4())}',
                chunk_id=chunk_id,
                subject_id=source_id,
                object_id=target_id,
                relationship_id=relationship_id,
                predicate=r.type,
                confidence=r.confidence,
                evidence_text=r.evidence_text
            )
        )
    return relationships_res, claims_res 

'''
import hashlib

raw = f"{source_id}:{relationship_type}:{target_id}"
relationship_id = hashlib.sha256(raw.encode()).hexdigest()
for fixed len ids
'''

def normalize_name(name: str) -> str:
    """
    Normalize an entity name for matching/deduplication.

    Operations:
    - Unicode normalization
    - Convert to lowercase
    - Normalize quotes/dashes
    - Remove punctuation
    - Collapse whitespace
    - Strip leading/trailing whitespace

    Does NOT:
    - Remove legal entity suffixes (Inc, Ltd, Corp, etc.)
    - Perform fuzzy matching
    - Resolve aliases
    - Decide whether two entities are actually the same
    """

    if not name:
        return ""

    # 1. Convert to string and strip whitespace
    name = str(name).strip()

    # 2. Unicode normalization
    # NFKC handles things like full-width characters.
    name = unicodedata.normalize("NFKC", name)

    # 3. Normalize common Unicode punctuation
    replacements = {
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2212": "-",   # minus sign
        "\u00a0": " ",   # non-breaking space
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    # 4. Lowercase
    name = name.lower()

    # 5. Remove punctuation
    # Keep alphanumeric characters and whitespace.
    name = re.sub(r"[^\w\s]", " ", name)

    # 6. Collapse repeated whitespace
    name = re.sub(r"\s+", " ", name)

    # 7. Final trim + Default Title
    return name.strip().title()
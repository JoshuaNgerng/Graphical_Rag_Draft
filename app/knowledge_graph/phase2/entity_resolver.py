import re

from pydantic import BaseModel, Field, field_validator

from app.core.config import Config
from app.models.entity_relationship import EntityNode
from app.models.observations import (
    EntityContext, EntityNormalizeObservation
)
from app.llm_service.gemini.client import Gemini_LLM
from app.models.decisions import Decision as D

class Decision(D):
    # Only populated for MERGE
    entity_id: str | None = None

    # Used for CREATE
    canonical_name: str
    entity_type: str
    description: str

    # Used primarily for MERGE
    add_alias: list[str] = Field(default_factory=list)

    @field_validator('entity_type', mode="after")
    @classmethod
    def normalize_type(cls, v: str):
        buffer = v.upper().strip()
        return re.sub(r"\s+", "_", buffer)


class EntityResolver(Gemini_LLM):

    def __init__(self, config: Config) -> None:
        super().__init__(config)

        self.context=self.__build_context()

    def decide_entity(
            self, entity: EntityNormalizeObservation, context: str,
            candidates: list[tuple[EntityNode, list[EntityContext]]]
        ):
        prompt = self.__complie_prompt(entity, context, candidates)
        return self.process(prompt, self.context, Decision)

    def __complie_prompt(
            self, entity: EntityNormalizeObservation, context: str, 
            candidates: list[tuple[EntityNode, list[EntityContext]]]
        ):
        buffer = (
    f"""
NEW ENTITY
Name: {entity.name}
Type: {entity.type}
Description: {entity.description}

SOURCE CONTEXT
{context}

EXISTING CANDIDATES

"""
        )
        if candidates:
            buffer += '\n'.join(
                self.__complie_candidate(c) for c in candidates
            )
        else:
            buffer += "No existing candidates were retrieved for this entity.\n"
        return buffer

    def __complie_entity_context(self, entity_context: list[EntityContext]):
        return "\n".join(
            c.evidence_text
            for c in entity_context
        )

    def __complie_candidate(self, candidate: tuple[EntityNode, list[EntityContext]]):
        entity, entity_context = candidate
        context = self.__complie_entity_context(entity_context)

        return f"""
--- CANDIDATE ---
{entity.repr_self_text()}

Existing evidence:
{context}
--- END CANDIDATE ---
"""

    def __build_context(self):
        return '''
You are an entity resolution system for a knowledge graph.

Your task is to determine whether a newly observed entity refers to one
of the existing candidate entities.

You must choose exactly one of:

MERGE
    The observed entity refers to an existing candidate entity.

CREATE
    The observed entity represents a new entity that does not correspond
    to any candidate.

UNKNOWN
    The available evidence is insufficient to safely determine whether
    the entity matches an existing candidate or represents a new entity.

ENTITY RESOLUTION RULES

1. Compare the new entity against candidates using:
   - entity name
   - normalized name
   - aliases
   - entity type
   - description
   - surrounding context
   - relationships or facts expressed in the context

2. Do not merge entities solely because their names are similar.

3. Names that are identical or similar can still refer to different entities.

4. Entity type is important evidence. A strong type conflict should normally
   prevent a MERGE unless the context clearly explains the difference.

5. Prefer contextual evidence over superficial name similarity.

6. Use the candidate's existing context to determine whether the candidate
   represents the same real-world entity.

7. Do not invent facts about candidates or the observed entity.

8. If multiple candidates remain plausible and the available evidence does
   not distinguish them, return UNKNOWN.

9. Do not choose a candidate merely because it is the highest-ranked candidate.

10. CREATE should only be selected when the evidence supports that the
    observed entity does not correspond to any provided candidate.

11. UNKNOWN should be preferred over an unsafe MERGE.

12. If no existing candidates were retrieved, this means that the candidate
retrieval stage did not identify any likely existing entities.

When no candidates are provided:

- Do not invent an existing candidate.
- Do not assign an entity_id.
- CREATE if the source evidence sufficiently establishes a distinct entity.
- UNKNOWN if the evidence is insufficient to establish a new entity.

DECISION OUTPUT

For MERGE:
- decision must be MERGE
- entity_id must contain the selected candidate ID
- canonical_name should be the candidate's canonical name
- entity_type should be the candidate's type
- description should preserve or improve the candidate description
- add_alias should contain the observed name if it is a useful new alias

For CREATE:
- decision must be CREATE
- entity_id must be null
- canonical_name should be the canonical name for the new entity
- entity_type should be the appropriate entity type
- description should describe only information supported by the supplied evidence
- add_alias may contain useful alternative names

For UNKNOWN:
- decision must be UNKNOWN
- entity_id must be null
- explain what evidence is missing or ambiguous
- do not arbitrarily select a candidate

CONFIDENCE

Confidence represents confidence in the decision, not confidence in the
quality of the input.

A high confidence MERGE means there is strong evidence that the observed
entity and candidate refer to the same entity.

A high confidence CREATE means there is strong evidence that none of the
provided candidates represents the observed entity.

A high confidence UNKNOWN means there is strong evidence that the available
evidence is insufficient to safely resolve the entity.

Return only the requested structured decision.
'''
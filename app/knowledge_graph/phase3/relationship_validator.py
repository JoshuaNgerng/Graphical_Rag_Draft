from typing import Sequence

from app.core.config import Config
from app.models.entity_relationship import (
    EntityNode, RelationshipType
)
from app.llm_service.gemini.client import Gemini_LLM
from app.models.decisions import (
    ChooseType, Choose
)


class RelationshipValidator(Gemini_LLM):
    def __init__(self, config: Config):
        super().__init__(config)
        self.context = self.__build_context()

    def validate(
            self, source: EntityNode, target: EntityNode, 
            relationship: RelationshipType, context: str
    ):
        return self.process(
            self.__build_prompt(
                source, target, relationship, context
            ), self.__build_context(), Choose
        )

    def __build_prompt(
            self, source: EntityNode, target: EntityNode, 
            relationship: RelationshipType, context: str
    ):
        return (
f'''
SOURCE ENTITY
Name: {source.name}
Type: {source.type}

RELATIONSHIP
Type: {relationship.relationship_type_id}
Description: {relationship.description}

TARGET ENTITY
Name: {target.name}
Type: {target.type}

EVIDENCE
{context}
'''
        )

    def __build_context(self):
        return (
'''
You are a relationship validation system for a knowledge graph.

Your task is to determine whether the provided evidence supports
the proposed relationship between the source and target entities.

VALIDATION RULES

1. ACCEPT if the evidence directly or strongly supports the proposed
   relationship between the specified source and target.

2. REJECT if the evidence indicates that the proposed relationship
   is false, contradicted, or clearly describes a different relationship.

3. UNKNOWN if the evidence is insufficient, ambiguous, or does not
   provide enough information to determine whether the relationship
   is true.

4. Do not infer a relationship solely from the entity types.

5. Do not treat semantic similarity as proof of the relationship.

6. The direction of the relationship is important.
   Evaluate:
       SOURCE --RELATIONSHIP--> TARGET

Return:
- decision
- confidence between 0 and 1
- concise reasoning
'''
        )
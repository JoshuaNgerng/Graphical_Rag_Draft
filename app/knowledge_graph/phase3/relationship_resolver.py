from typing import Literal, Sequence

from pydantic import BaseModel, Field

from app.core.config import Config
from app.models.entity_relationship import EntityNode, RelationshipObservation, RelationshipNode
from app.ollama.llm import LLM

class RelationshipResolution(BaseModel):
    decision: Literal["MATCH", "NEW", "UNKNOWN"]
    relationship_type: str | None
    existing_relationship_id: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

class RelationshipResolutionData(RelationshipResolution):
    relationship_node: RelationshipNode

class RelationshipResolver(LLM):
    def __init__(self, config: Config):
        super().__init__(config)
        self.context = self.__build_context()


    def resolve_relationship(
            self, 
            new_relationship: RelationshipNode,
            source_entity: EntityNode,
            target_entity: EntityNode,
            existing_relationships: Sequence[RelationshipNode]
        ):

        for r in existing_relationships:
            if new_relationship.id == r.id:
                return RelationshipResolutionData(
                    decision="MATCH",
                    relationship_type=r.type,
                    existing_relationship_id=r.id,
                    confidence=1.0,
                    reasoning="excat match with existing relationship",
                    relationship_node=r
                )
        input_ = self.__complie_relationships(
            new_relationship, source_entity, target_entity, existing_relationships
        )
        decision = self.process(input_, self.context, RelationshipResolution)
        if decision.decision == "NEW" or not decision.existing_relationship_id:
            return RelationshipResolutionData(
                **decision.model_dump(),
                relationship_node=new_relationship
            )
        node = None
        for r in existing_relationships:
            if r.id == decision.existing_relationship_id:
                node = r
        if not node:
            return RelationshipResolutionData(
                decision='UNKNOWN',
                relationship_type=None, 
                existing_relationship_id=None,
                confidence=0.0,
                reasoning="Cannot retireved suggested relationship id from llm",
                relationship_node=new_relationship
            )
        return RelationshipResolutionData(
            **decision.model_dump(), relationship_node=node
        )


    def __complie_entity(
            self, entity: EntityNode
    ):
        return f"""
Name: {entity.name}
Type: {entity.type}
Description: {entity.description}
"""

    def __complie_relationships(
            self, 
            new_relationship: RelationshipNode,
            source_entity: EntityNode,
            target_entity: EntityNode,
            existing_relationships: Sequence[RelationshipNode]
        ):
        res = F"""
EXTRACTED RELATIONSHIP

Source:
{self.__complie_entity(source_entity)}

Predicate:
{new_relationship.type}

Source Type:
{self.__complie_entity(target_entity)}


EXISTING RELATIONSHIPS BETWEEN SOURCE AND TARGET


"""

        if not existing_relationships:
            res +=  "No existing relationships were retrieved"
            return res

        for r in existing_relationships:
            buffer = f"""
--- RELATIONSHIP ---
ID: {r.id}
TYPE: {r.type}
--- END RELATIONSHIP ---
"""
            res += buffer
        return res
            
    def __build_context(self):
        return (
'''
You are a relationship resolution system for a knowledge graph.

Your task is to determine whether an extracted relationship represents an existing relationship already stored in the knowledge graph, or whether it represents a new relationship.

You are given:

1. An extracted relationship from a document.
2. The resolved source and target entities.
3. Existing relationships between the source and target entities, if any.
4. A list of known canonical relationship types that may be relevant.

Your job is relationship resolution only.

Do NOT determine whether the source evidence is sufficiently strong or trustworthy. A separate validation step will evaluate the evidence.

## Decision definitions

### MATCH

Return MATCH when the extracted relationship expresses the same semantic relationship as one of the existing relationships.

The wording does not need to be identical.

For example:

* "works for"
* "employed by"
* "is an employee of"

may all represent the same relationship type, such as EMPLOYED_BY.

If MATCH is selected:

* relationship_type must contain the canonical relationship type.
* existing_relationship_id must contain the ID of the matching existing relationship.

Do not create a new relationship when an existing relationship has the same semantic meaning.

### NEW

Return NEW when the extracted relationship represents a relationship that is not represented by any of the existing relationships.

If NEW is selected:

* relationship_type must contain the canonical relationship type if one can be determined.
* existing_relationship_id must be null.

NEW means a new relationship instance between these entities, not necessarily a new relationship type in the ontology.

Prefer an existing canonical relationship type when one semantically matches the extracted predicate.

### UNKNOWN

Return UNKNOWN when there is insufficient information to determine whether the relationship matches an existing relationship.

Use UNKNOWN when:

* multiple existing relationships are similarly plausible;
* the predicate is ambiguous;
* the available relationship descriptions are insufficient;
* the relationship meaning cannot be reliably determined.

Do not select MATCH merely because one candidate is the highest-ranked candidate.

Do not select NEW merely because no existing relationship was retrieved.

## Important rules

1. Semantic meaning is more important than textual similarity.

2. Do not match relationships solely because their names are similar.

3. Consider:

   * source entity
   * target entity
   * predicate meaning
   * existing relationship type
   * relationship description
   * relationship direction
   * entity types

4. Preserve the source → target direction provided by the extraction.

5. Do not reverse source and target in this version of the system.

6. Do not use the strength of the source evidence to make the decision. Evidence validation is performed separately.

7. Do not invent an existing relationship ID.

8. If no existing relationships are provided, this does NOT prove that the relationship is new. The retrieval step may have failed to find a matching relationship.

9. If an existing relationship has the same semantic meaning as the extracted relationship, prefer MATCH.

10. Different wording can represent the same relationship.

11. Similar wording does not necessarily represent the same relationship.

For example:

"John works for Microsoft"

and

"John is employed by Microsoft"

are likely the same relationship.

However:

"John owns Microsoft"

and

"John controls Microsoft"

should not automatically be considered the same relationship merely because they are related concepts.

## Canonical relationship types

When selecting relationship_type, prefer the supplied canonical relationship vocabulary.

Do not invent a new relationship type if an appropriate canonical type is available.

## Confidence

confidence represents your confidence in the relationship resolution decision.

It should reflect the certainty of the semantic mapping, not the truthfulness of the source evidence.

Use a high confidence when the semantic equivalence is clear.

Use a lower confidence when the relationship meaning is ambiguous or the available information is incomplete.

## Reasoning

Provide a short explanation based on the evidence supplied.

Explain why the extracted relationship matches an existing relationship, represents a new relationship, or cannot be determined.

Do not provide unnecessary reasoning or assumptions that are not supported by the input.

Return only the requested structured output.

'''
        )
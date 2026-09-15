from typing import Sequence

from app.core.config import Config
from app.models.entity_relationship import (
    EntityNode, RelationshipNode, RelationshipCandidate
)
from app.llm_service.gemini.client import Gemini_LLM
from app.knowledge_graph.models.decisions import (
    Decision as D, DecisionType
)

class RelationshipResolution(D):
    relationship_type: str | None = None
    existing_relationship_id: str | None = None
    new_description: str | None = None

class RelationshipResolutionData(RelationshipResolution):
    relationship_candidate: RelationshipCandidate 

class RelationshipResolver(Gemini_LLM):
    def __init__(self, config: Config):
        super().__init__(config)
        self.context = self.__build_context()

    def resolve_relationship(
            self, 
            new_relationship: RelationshipNode,
            source_entity: EntityNode,
            target_entity: EntityNode,
            existing_relationships: Sequence[RelationshipCandidate]
        ):

        for r in existing_relationships:
            if new_relationship.id == r.relationship_id:
                return RelationshipResolutionData(
                    decision=DecisionType.MERGE,
                    relationship_type=r.relationship_type_id,
                    existing_relationship_id=r.relationship_id,
                    confidence=1.0,
                    reasoning="excat match with existing relationship",
                    relationship_candidate=r
                )
        input_ = self.__complie_relationships(
            new_relationship, source_entity, target_entity, 
            existing_relationships
        )
        decision = self.process(input_, self.context, RelationshipResolution)
        if (
            decision.decision == DecisionType.CREATE or 
            not decision.existing_relationship_id
        ):
            return RelationshipResolutionData(
                **decision.model_dump(),
                relationship_candidate=self._create_new_relationship_candidate(
                    new_relationship, source_entity, target_entity, 
                    decision.new_description or ''
                )
            )
        node = None
        for r in existing_relationships:
            if r.relationship_id == decision.existing_relationship_id:
                node = r
        if not node:
            return RelationshipResolutionData(
                decision=DecisionType.UNKNOWN,
                relationship_type=None, 
                existing_relationship_id=None,
                confidence=0.0,
                reasoning="Cannot retireved suggested relationship id from llm",
                relationship_candidate=self._create_new_relationship_candidate(
                    new_relationship, source_entity, target_entity, 
                    decision.new_description or ''
                )
            )
        return RelationshipResolutionData(
            **decision.model_dump(), relationship_candidate=node
        )

    def _create_new_relationship_candidate(
            self, new_relationship: RelationshipNode,
            source_entity: EntityNode,
            target_entity: EntityNode,
            new_description: str
        ):
        type_ = new_relationship.relationship_type_id
        id_ = f'{source_entity.id}:{type_}:{target_entity.id}'
        return RelationshipCandidate(
            relationship_id=id_,
            relationship_type_id=type_,
            description=new_description,
            source_type=source_entity.type,
            source_id=source_entity.id,
            target_id=target_entity.id,
            target_type=target_entity.type
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
            existing_relationships: Sequence[RelationshipCandidate]
        ):
        res = (
f"""
EXTRACTED RELATIONSHIP

Source:
{self.__complie_entity(source_entity)}

Predicate:
{new_relationship.relationship_type_id}

Source Type:
{self.__complie_entity(target_entity)}

EXISTING RELATIONSHIPS BETWEEN SOURCE AND TARGET
"""
        )

        if not existing_relationships:
            res +=  "No existing relationships were retrieved"
            return res

        for r in existing_relationships:
            buffer = (
f"""
--- RELATIONSHIP ---
ID: {r.relationship_id}
TYPE: {r.relationship_type_id}
DESCRIPTION: {r.description}
--- END RELATIONSHIP ---
"""
            )
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

### MERGE

Return MERGE when the extracted relationship expresses the same semantic relationship as one of the existing relationships.

The wording does not need to be identical.

For example:

* "works for"
* "employed by"
* "is an employee of"

may all represent the same relationship type, such as EMPLOYED_BY.

If MERGE is selected:

* relationship_type must contain the canonical relationship type.
* existing_relationship_id must contain the ID of the matching existing relationship.
* new_description leave as null

Do not create a new relationship when an existing relationship has the same semantic meaning.

### CREATE

Return CREATE when the extracted relationship represents a relationship that is not represented by any of the existing relationships.

If CREATE is selected:

* relationship_type must contain the canonical relationship type if one can be determined.
* existing_relationship_id must be null.
* new_description must be given a concise description for the new relationship

CREATE means a new relationship instance between these entities, not necessarily a new relationship type in the ontology.

Prefer an existing canonical relationship type when one semantically matches the extracted predicate.

### UNKNOWN

* leave the fields relationship_type, existing_relationship_id and new_description as null

Return UNKNOWN when there is insufficient information to determine whether the relationship matches an existing relationship.

Use UNKNOWN when:

* multiple existing relationships are similarly plausible;
* the predicate is ambiguous;
* the available relationship descriptions are insufficient;
* the relationship meaning cannot be reliably determined.

Do not select MERGE merely because one candidate is the highest-ranked candidate.

Do not select CREATE merely because no existing relationship was retrieved.

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

9. If an existing relationship has the same semantic meaning as the extracted relationship, prefer MERGE.

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

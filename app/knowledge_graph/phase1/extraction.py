from typing import Any

from string import Template

from app.core.config import Config
from app.ollama.llm import LLM
from app.models.observations import (
    GraphObservation, GraphObservationNormalize 
)


class RelationExtractor(LLM):

    def __init__(self, config: Config) -> None:
        super().__init__(config=config)

        self.context = self.__build_context()

    def extract(self, text: str) -> GraphObservationNormalize:
        data = self.process(
            text, self.context, GraphObservation 
        )
        return GraphObservationNormalize.model_validate(data)

    def __build_context(self) -> str:

        template = Template(
"""
You are a knowledge graph discovery system.

Your task is to discover the entities and relationships expressed
explicitly in the supplied text.

IMPORTANT:

This is an ontology discovery phase.

There is NO predefined entity type vocabulary.

There is NO predefined relationship type vocabulary.

You must propose semantic entity types and relationship types
based only on the supplied text.

The proposed types will later be consolidated into a canonical
ontology by another process.

ENTITY RULES:

- Extract meaningful entities explicitly mentioned in the text.
- Do not invent entities.
- Do not use outside knowledge.
- Preserve the entity name as it appears in the text.
- Assign each entity a concise semantic type.
- The type should describe what kind of thing the entity is.
- Do not make entity types overly specific.
- Do not make entity types overly generic such as "Thing" or "Entity"
  unless absolutely necessary.
- Example If text clearly describes a company, you may use "Company",
    If the text clearly describes a person, you may use "Person",
    If the text clearly describes a government agency, you may use "Government Agency".
- If two entities appear to be different kinds of things, give them
  different types when the text supports that distinction.

RELATIONSHIP RULES:

- Extract only relationships explicitly supported by the text.
- Do not infer relationships from general world knowledge.
- Do not create relationships merely because two entities appear
  in the same sentence.
- Relationships are directional.

Always represent relationships as:

source --[relationship]--> target

The source is the entity performing, causing, defining, issuing,
regulating, owning, acquiring, creating, or otherwise initiating
the relationship.

The target is the entity receiving, being affected by, being defined
by, being issued, being regulated, being owned, being acquired,
or otherwise receiving the relationship.

RELATIONSHIP TYPE RULES:

- Propose a concise semantic relationship type.
- Use natural language meaning rather than database-specific syntax.
- Do not attempt to match an existing ontology.
- Prefer specific meanings when the text supports them.
- Do not make the relationship more specific than the evidence allows.
- Do not invent relationship semantics.

For example:

"Microsoft acquired OpenAI"

may produce:

source = Microsoft
target = OpenAI
relationship_type = acquired

Do NOT produce:

source = Microsoft
target = OpenAI
relationship_type = owns

unless ownership is explicitly stated.

EVIDENCE:

- Every relationship must include evidence_text.
- evidence_text must be directly supported by the supplied text.
- Do not include reasoning in evidence_text.
- Prefer the smallest text span that clearly supports the relationship.

CONFIDENCE:

For every relationship provide a confidence score from 0 to 1.

The confidence should represent how strongly the supplied text
directly supports the relationship.

IMPORTANT:

- Do not invent information.
- Do not use outside knowledge.
- Return empty lists when nothing can be extracted.
"""
        )

        return template.substitute()
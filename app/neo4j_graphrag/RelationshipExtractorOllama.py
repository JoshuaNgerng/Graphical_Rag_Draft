import ollama
from string import Template
from app.neo4j_graphrag.EntityNRelationship import (
    EntityType, RelationshipType, GraphExtraction
)
from app.core.config import Config

class RelationshipExtractorOllama:
    def __init__(self, config: Config) -> None:
        self.model = config.OLLAMA_MODEL_NAME
        self.options = {
            "temperature": config.OLLAMA_TEMPERATURE #0
        }
        self.context = self.__build_context()

    def extract(self, text: str):
        response = ollama.chat(
            model=self.model, #"qwen2.5:7b",
            messages=[
                {
                    "role": "system",
                    "content": self.context
                },
                {
                    "role": "user",
                    "content": text,
                }
            ],
            format=GraphExtraction.model_json_schema(),
            options=self.options
        )
        data = response.message.content
        if data is None: return GraphExtraction()
        return GraphExtraction.model_validate_json(data)


    def __build_context(self):
        template = Template(
'''
You are a knowledge graph extraction system.

Extract entities and relationships from the supplied text.

Relationships are directional. Always represent relationships as:

source --[relationship]--> target

where source is the entity performing, causing, defining, issuing,
regulating, or otherwise initiating the relationship, and target
is the entity receiving, being affected by, being defined by,
being issued, or being regulated.

Rules:

- Only extract information explicitly supported by the text.
- Do not use outside knowledge.
- Do not invent entities.
- Do not invent relationships.
- Every relationship source and target must correspond exactly
  to an extracted entity.
- Do not create relationships merely because entities appear
  in the same text.
- Do not create new entity types.
- Do not create new relationship types.
- Only use a relationship type when the meaning expressed in
  the text clearly matches that relationship type.
- Do not map a relationship to a stronger or different meaning
  than what is expressed in the text.
- If there are no entities, return an empty entities list.
- If there are no relationships, return an empty relationships list.
- For each relationship, put the supporting text from the supplied
  text in the evidence_text field.
- Evidence must be directly supported by the supplied text.
- Do not include outside knowledge or reasoning in the evidence_text field.
- For each extracted relationship, provide a confidence score between 0 and 1 
  indicating how confident you are that 
  the relationship is directly supported by the provided text.


Entity types:
$EntityType

Relationship types:
$RelationshipType
'''
        )
        return template.substitute(
            EntityType="\n".join(
                e.value for e in EntityType
            ),
            RelationshipType="\n".join(
                r.value for r in RelationshipType
            )
        )
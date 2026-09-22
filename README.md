# Schema-Independent Knowledge Graph Construction

> An experimental pipeline for exploring how domain knowledge graphs can be constructed from unstructured documents **without requiring a complete expert-defined schema beforehand**.

## Overview

Domain-specific knowledge graphs often depend on carefully designed schemas describing:

* entity types
* relationship types
* constraints
* domain-specific concepts
* rules for connecting entities

This schema-first approach can produce highly structured and useful knowledge graphs, but designing the schema itself can require substantial domain expertise and engineering effort.

This project explores a different question:

> **Can we start with relatively little predefined domain knowledge, extract candidate entities and relationships from documents, and use the resulting knowledge to help discover, validate, and progressively develop a domain-specific schema?**

The goal is **not** to eliminate domain experts.

Instead, the goal is to investigate whether automated extraction, entity resolution, relationship discovery, and LLM-assisted validation can reduce the effort required to move from unstructured documents toward a useful domain knowledge graph.

---

## Motivation

Many knowledge graph systems are designed around a predefined ontology or schema.

For example, a domain may first define:

```text
Person
Organization
ResearchProject
Disease
Drug
Gene

Person ── WORKS_FOR ──> Organization
Person ── WORKS_ON ──> ResearchProject
Drug ── TREATS ──> Disease
Drug ── TARGETS ──> Gene
```

The resulting extraction process can then be constrained to these known concepts and relationships.

This project investigates the reverse direction:

```text
                 Unstructured Documents
                          │
                          ▼
                 Generic Extraction
                          │
                          ▼
                 Candidate Entities
                 + Relationships
                          │
                          ▼
                  Entity Resolution
                          │
                          ▼
              Relationship Resolution
                          │
                          ▼
                   Evidence Validation
                          │
                          ▼
                ┌────────────────────┐
                │ Candidate Knowledge │
                │      Graph         │
                └─────────┬──────────┘
                          │
                          ▼
                  Schema Discovery
                          │
                          ▼
               Expert Review / Refinement
                          │
                          ▼
                Domain Knowledge Graph
```

The intended outcome is therefore not simply an automatically generated graph, but a process that can help a domain expert **discover what a useful schema might look like**.

---

## Current Research Question

The current project is exploring:

> **How can a knowledge graph construction pipeline extract useful structured knowledge from documents before a detailed domain schema has been established, and how can the extracted knowledge subsequently assist in developing or extending that schema?**

Some related questions are:

1. How well can an LLM extract entities and relationships without a predefined domain ontology?
2. How can extracted entities be resolved against an evolving knowledge graph?
3. How can semantically similar relationship predicates be canonicalized?
4. How can evidence be used to validate extracted relationships?
5. Can frequently occurring entity types and relationship patterns reveal useful candidate schema components?
6. How much human effort is required to transform automatically discovered patterns into a usable domain schema?
7. Can an existing knowledge graph be extended with previously unknown entity or relationship types without requiring the entire schema to be redesigned?

---

# Current Architecture

The current implementation is an experimental document-processing pipeline.

```text
Document
   │
   ▼
Chunking
   │
   ▼
Generic Entity + Relationship Extraction
   │
   ▼
Entity Resolution
   │
   ▼
Relationship Candidate Retrieval
   │
   ▼
Relationship Resolution
   │
   ▼
Relationship Validation
   │
   ▼
Knowledge Graph
```

PostgreSQL is currently used as a durable processing/checkpoint store, while Neo4j is used as the knowledge graph.

---

## 1. Document Chunking

Documents are divided into chunks before LLM processing.

Each chunk retains provenance information such as:

* document ID
* chunk ID
* chunk index
* page range
* source text

This allows extracted knowledge to be traced back to the original evidence.

---

## 2. Generic Entity and Relationship Extraction

The initial extraction stage intentionally avoids requiring a complete domain-specific schema.

The LLM is asked to identify candidate:

```text
Entity
Relationship
```

rather than being given a fixed list of all valid domain relationships.

For example, a document might produce:

```text
Entity:
    John Smith
    NASA
    Artemis Program

Relationship:
    John Smith
        works for
    NASA

Relationship:
    John Smith
        participates in
    Artemis Program
```

The extracted predicates can then be normalized and resolved against the evolving graph.

---

## 3. Entity Resolution

Extracted entity mentions are not immediately assumed to represent new entities.

Candidate entities can be retrieved using multiple signals, including:

* exact matching
* lexical matching
* vector similarity
* contextual evidence
* entity type

The candidates are then presented to an LLM for a resolution decision.

Current decisions include:

```text
MERGE
CREATE
UNKNOWN
```

For example:

```text
Extracted:
    "NASA"

Candidates:
    NASA
    NASA Federal Credit Union
    NASA Research Center

LLM decision:
    MERGE → existing NASA entity
```

If there is insufficient evidence to determine the identity, the system can retain an `UNKNOWN` decision rather than forcing a merge.

---

## 4. Relationship Resolution

Relationship predicates extracted from documents can have many surface forms.

For example:

```text
works for
employed by
employee of
works at
```

may refer to closely related concepts.

The current system separates:

### Predicate normalization

Simple syntactic normalization:

```text
"works for"
        ↓
WORKS_FOR
```

from:

### Relationship canonicalization

Semantic resolution:

```text
WORKS_FOR
EMPLOYEE_OF
EMPLOYED_BY
        ↓
EMPLOYED_BY
```

Relationship types are represented separately from relationship instances.

```text
(:RelationshipType {
    id,
    description,
    source_type,
    target_type,
    embedding
})
```

while graph relationships contain the resolved type:

```text
(:Entity)-[:RELATES {
    id,
    type
}]->(:Entity)
```

This allows relationship-type definitions to evolve independently from individual relationship instances.

---

## 5. Relationship Validation

After candidate relationship resolution, the system validates whether the source document actually supports the proposed relationship.

For example:

```text
Source:
    John Smith

Relationship:
    EMPLOYED_BY

Target:
    NASA

Evidence:
    "John Smith joined NASA in 2018."
```

The validation stage can return:

```text
ACCEPT
REJECT
UNKNOWN
```

This distinction is important because semantic similarity alone does not prove that a relationship exists.

The document evidence remains attached to the resulting claim.

---

# Provenance

A central design goal is that graph knowledge should remain traceable to its source evidence.

The conceptual graph currently looks like:

```text
Document
   │
   └── CONTAINS → Chunk
                    │
                    └── SUPPORTS → Claim
                                    │
                                    ├── SUBJECT → Entity
                                    │
                                    └── OBJECT → Entity

Entity ── RELATES ──> Entity

Claim
   │
   └── relationship_id → canonical relationship
```

A relationship can therefore be supported by multiple claims:

```text
Document A
    │
    └── Chunk A
          └── Claim A ──┐
                         │
Document B              ▼
    │               Relationship
    └── Chunk B         │
          └── Claim B ──┘
```

This allows the system to distinguish:

> **The graph currently contains this relationship**

from:

> **These particular pieces of evidence support the relationship.**

---

# Checkpoint and Recovery System

LLM-based pipelines can fail for reasons outside the application itself:

* API quota exhaustion
* rate limits
* model availability
* network failures
* local model resource limitations
* worker crashes
* unexpected external-service errors

The processing pipeline therefore uses PostgreSQL as a durable checkpoint store.

Each processing stage saves its state after successful completion.

```text
Phase 1
   │
   ├── success
   ▼
PostgreSQL checkpoint
   │
   ▼
Phase 2
   │
   ├── success
   ▼
PostgreSQL checkpoint
   │
   ▼
Phase 3
   │
   ├── success
   ▼
PostgreSQL checkpoint
```

If processing fails during a later stage, the job can be resumed using the stored state rather than restarting the entire document.

For example:

```text
Phase 1    ✓
Phase 2    ✓
Phase 3    ✗
```

On recovery:

```text
Phase 1    SKIP
Phase 2    SKIP
Phase 3    RETRY
```

This is particularly important for experiments involving external LLM APIs, where repeated processing can consume significant resources.

---

# Current Technology Stack

The project currently uses:

* **Python**
* **Pydantic**
* **SQLAlchemy**
* **PostgreSQL**
* **Neo4j**
* **LLMs**
* **Vector embeddings**
* **FastAPI** for API experimentation

Ollama is used for vector embedding
LLM tested both Ollama and Gemini 

---

# API

The project currently includes basic entity listing/search functionality.

Conceptually:

```http
GET /entities
```

The endpoint supports filtering by entity type and pagination, with optional search functionality.

Example:

```http
GET /entities?entity_type=Organization&page=1&page_size=25
```

The entity listing API is intended for graph exploration and administration.

Entity-resolution candidate retrieval is treated as a separate operation because it serves a different purpose:

```text
Entity listing
    → "Show me entities in the graph."

Entity candidate retrieval
    → "Which existing entity might this extracted mention refer to?"
```

---

# Current Status

This project is currently **experimental and under active development**.

### Implemented / in progress

* [x] PDF/document chunking
* [x] Generic entity extraction
* [x] Generic relationship extraction
* [x] PostgreSQL processing/checkpoint storage
* [x] Pipeline recovery after processing failure
* [x] Neo4j entity persistence
* [x] Relationship type representation
* [x] Entity candidate retrieval
* [x] LLM-assisted entity resolution
* [x] Relationship candidate retrieval
* [x] Relationship validation design
* [x] Basic entity API
* [ ] Comprehensive evaluation
* [ ] Schema discovery from extracted graph
* [ ] Expert-assisted schema refinement
* [ ] Benchmark datasets
* [ ] Quantitative comparison with schema-first pipelines
* [ ] Large-scale performance testing

### Current testing

* There are still bugs when saving and recovering from Postgres that is being fix now

---

# Current Limitations

The current implementation should not yet be considered a production-ready knowledge graph construction system.

In particular:

### Limited evaluation

The pipeline has not yet undergone systematic evaluation on a sufficiently large benchmark.

### LLM resource constraints

Experiments are currently limited by available LLM resources, including hosted API quotas and local inference CPU capacity.

### Schema discovery is not yet complete

The current system can extract generic knowledge, but the next major research stage is determining how extracted graph patterns can be transformed into useful candidate schemas.

### Human evaluation is still required

The project does not assume that an automatically discovered schema is correct.

Instead, one of the research questions is whether automation can reduce the amount of expert effort required to construct and maintain a domain schema.

---

# Research Direction

The long-term goal is to explore a workflow such as:

```text
                Documents
                    │
                    ▼
          Schema-independent
              extraction
                    │
                    ▼
             Raw knowledge
                    │
          ┌─────────┴─────────┐
          │                   │
          ▼                   ▼
    Entity patterns      Relationship patterns
          │                   │
          └─────────┬─────────┘
                    ▼
              Pattern mining
                    │
                    ▼
             Candidate schema
                    │
                    ▼
             Expert review
                    │
                    ▼
           Refined domain schema
                    │
                    ▼
           Schema-aware extraction
                    │
                    ▼
          Domain Knowledge Graph
```

This suggests a potentially iterative process:

```text
Extract
   ↓
Discover
   ↓
Review
   ↓
Schema
   ↓
Re-extract
   ↓
Refine
   ↓
Schema
   ↓
...
```

Rather than treating schema design as a one-time prerequisite, the schema becomes an evolving artifact informed by the data.

---

# Future Experiments

Several experiments are planned.

## 1. Schema Discovery

Given a collection of extracted entities and relationships:

```text
PERSON
ORGANIZATION
PROJECT
LOCATION
...

WORKS_FOR
PARTICIPATES_IN
LOCATED_IN
FUNDED_BY
...
```

investigate whether recurring patterns can be clustered into candidate:

* entity types
* relationship types
* source/target constraints
* relationship descriptions
* aliases
* type hierarchies

---

## 2. Human Effort

Compare:

```text
Manual schema design
```

against:

```text
Automatically generated candidate schema
        +
Expert refinement
```

Potential measurements include:

* time required
* number of expert corrections
* number of accepted/rejected schema elements
* extraction quality before and after schema refinement

---

## 3. Schema-free vs Schema-guided Extraction

Compare extraction under:

```text
No domain schema
```

versus:

```text
Partially developed schema
```

versus:

```text
Fully defined schema
```

This could help determine where schema guidance provides the greatest benefit.

---

## 4. Incremental Knowledge Base Extension

Given an existing knowledge graph:

```text
Existing schema
      +
New document collection
      ↓
Previously unknown concepts
      ↓
Candidate schema extensions
      ↓
Expert approval
      ↓
Updated knowledge graph
```

This explores whether the system can assist with **schema evolution**, rather than only initial KG construction.

---

# Research Context

This project is related to several areas of existing research:

* Knowledge graph construction
* Ontology learning
* Schema induction
* Open information extraction
* Entity resolution / entity linking
* Relation extraction
* Knowledge fusion
* Human-in-the-loop AI
* LLM-assisted knowledge graph construction

Recent surveys describe KG construction as a combination of knowledge acquisition, refinement, and evolution, while more recent LLM-focused work explicitly distinguishes schema-based and schema-free approaches.

Human-in-the-loop schema induction is also an established research direction: prior work has explored using LLMs to generate candidate schema elements followed by human editing and refinement.

This project is particularly interested in the space between:

```text
Fully manual domain modeling
```

and

```text
Fully automatic schema generation
```

with the goal of investigating whether LLMs and graph-based methods can make **expert schema development more efficient and iterative**.

---

# Disclaimer

This repository represents an experimental research project rather than a finished framework.

The current implementation is primarily intended to explore:

> **How much of the knowledge-graph construction and schema-development process can be automated or assisted when the domain schema is initially incomplete or unknown?**

Results should therefore be interpreted as experimental until systematic evaluation has been completed.

---

# License

TODO

# Contact / Discussion

Feedback, criticism, research suggestions, and implementation ideas are welcome.

In particular, feedback from people working in:

* knowledge graphs
* ontology engineering
* information extraction
* NLP
* entity resolution
* LLM-based information extraction
* domain-specific knowledge management

would be valuable.

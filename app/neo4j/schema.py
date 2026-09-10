from neo4j import Driver

class Neo4jSchema:
    @staticmethod
    def ensure(driver: Driver):
        driver.execute_query("""
            CREATE CONSTRAINT document_id_unique IF NOT EXISTS
            FOR (d:Document)
            REQUIRE d.id IS UNIQUE
        """)

        driver.execute_query("""
            CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
            FOR (c:Chunk)
            REQUIRE c.id IS UNIQUE
        """)

        driver.execute_query("""
            CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
            FOR (e:Entity)
            REQUIRE e.id IS UNIQUE
        """)

        driver.execute_query("""
            CREATE CONSTRAINT claim_id_unique IF NOT EXISTS
            FOR (c:Claim)
            REQUIRE c.id IS UNIQUE
        """)

        driver.execute_query("""
            CREATE CONSTRAINT relationship_type_id_unique IF NOT EXISTS
            FOR (rt:RelationshipType)
            REQUIRE rt.id IS UNIQUE
        """)

        driver.execute_query("""
            CREATE CONSTRAINT relationship_id_unique IF NOT EXISTS
            FOR ()-[r:RELATES]-()
            REQUIRE r.id IS UNIQUE
        """)

        driver.execute_query("""
            CREATE VECTOR INDEX chunk_embedding_index IF NOT EXISTS
            FOR (c:Chunk)
            ON c.embedding
            OPTIONS {
                indexConfig: {
                    `vector.dimensions`: 768,
                    `vector.similarity_function`: 'cosine'
                }
            }
        """)

        driver.execute_query(
            """
            CREATE INDEX entity_normalized_name IF NOT EXISTS
            FOR (e:Entity)
            ON (e.normalize_name)
            """
        )

        driver.execute_query(
            """
            CREATE FULLTEXT INDEX entity_name_fulltext IF NOT EXISTS
            FOR (e:Entity)
            ON EACH [e.name, e.alias]
            """
        )

        driver.execute_query("""
            CREATE VECTOR INDEX entity_embedding_index IF NOT EXISTS
            FOR (e:Entity)
            ON e.embedding
            OPTIONS {
                indexConfig: {
                    `vector.dimensions`: 768,
                    `vector.similarity_function`: 'cosine'
                }
            }
        """)

        driver.execute_query("""
            CREATE VECTOR INDEX relationship_type_embedding_index IF NOT EXISTS
            FOR (rt:RelationshipType)
            ON rt.embedding
            OPTIONS {
                indexConfig: {
                    `vector.dimensions`: 768,
                    `vector.similarity_function`: 'cosine'
                }
            }
        """)

        driver.execute_query("""
            CREATE INDEX claim_relationship_id IF NOT EXISTS
            FOR (c:Claim)
            ON (c.relationship_id)
        """)

        records, _, _ = driver.execute_query("""
            SHOW VECTOR INDEXES
            YIELD name, state, populationPercent
            WHERE name = 'chunk_embedding_index'
            RETURN name, state, populationPercent
        """)

        if len(records) == 0:
            raise RuntimeError(
                "Vector index was not created"
            )

        if not records:
            raise RuntimeError(
                "Vector index was not created"
            )

        record = records[0]

        if record["state"] != "ONLINE":
            raise RuntimeError(
                f"Vector index is not ready: "
                f"{record['state']}"
            )
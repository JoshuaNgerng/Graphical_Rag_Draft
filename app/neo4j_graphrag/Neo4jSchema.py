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
            CREATE VECTOR INDEX chunk_embedding_index IF NOT EXISTS
            FOR (c:Chunk)
            ON c.embedding
            OPTIONS {
                indexConfig: {
                    `vector.dimensions`: 1024,
                    `vector.similarity_function`: 'cosine'
                }
            }
        """)

        records, _, _ = driver.execute_query("""
            SHOW VECTOR INDEXES
            YIELD name, state, populationPercent
            WHERE name = 'chunk_embedding_index'
            RETURN name, state, populationPercent
        """)

        if len(records) == 0:
            raise RuntimeError("Vector index was not created")

        record = records[0]
        # print(
        #     f"Vector index: {record['state']} "
        #     f"({record['populationPercent']}%)"
        # )
        print(f"debug {record}")
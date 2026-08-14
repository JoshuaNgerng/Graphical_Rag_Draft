from neo4j import Driver

class Neo4jQuery: 

    def __init__(self, driver: Driver) -> None:
        self.driver = driver

    def query(self, prompt: str):
        pass
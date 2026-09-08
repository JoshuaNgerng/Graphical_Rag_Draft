from typing import Sequence

from ollama import Client

from app.core.config import Config, get_config 

class Embedding:

    def __init__(
        self,
        config: Config
    ) -> None:

        self.client = Client(config.OLLAMA_URL)
        self.model = config.OLLAMA_EMBEDDING_MODEL

    def encode(self, text: str) -> Sequence[float]:

        response = self.client.embed(
            model=self.model,
            input=text,
        )

        return response.embeddings[0]

    @property
    def dimension(self) -> int: # use for testing for Neo4j schema setup
        response = self.client.embed(
            model=self.model,
            input="dimension check",
        )
        return len(response.embeddings[0])

if __name__ == '__main__':
    model = Embedding(get_config())
    print(model.model)
    print(model.dimension)
# ingest.py

import asyncio
from pathlib import Path

from neo4j_graphrag.experimental.components.data_loader import PdfLoader


async def main():
    loader = PdfLoader()

    document = await loader.run(
        filepath=Path("../eu_air_policy.pdf")
    )

    # check = dir(document)
    # print([c for c in check if not c.startswith('_')])
    print(document.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
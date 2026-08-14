from dataclasses import dataclass
import json
from typing import cast

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid
import re
import unicodedata
import pymupdf as fitz
from pymupdf import Document

@dataclass
class QueryPoint:
    score: float
    text: str
    document_id: str

@dataclass
class ChunkData:
    text: str
    chunk_index: int
    page_start: int = 0
    page_end: int = 0
    section: str | None = None


class VectorDB:

    def __init__(self) -> None:
        self.collection_name = "documents"
        self.qdrant = QdrantClient(url="http://localhost:6333")
        self.model = SentenceTransformer("BAAI/bge-m3")

    def index_document(
        self,
        pdf_path: str,
        document_id: str,
        filename: str,
        additional_metadata: dict = {}
    ):
        with fitz.open(pdf_path) as doc:
            doc = fitz.open(pdf_path)

            points = []
            for chunk in self._chunk_doc(doc):
                vector = self.model.encode(
                    chunk.text,
                    normalize_embeddings=True,
                ).tolist()

                points.append(
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "document_id": document_id,
                            "chunk_index": chunk.chunk_index,
                            "text": chunk.text,
                            "page_start": chunk.page_start,
                            "page_end": chunk.page_end,
                            "source": filename,
                            **(additional_metadata),
                        },
                    )
                )

            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=points,
            )


    def retrieve(self, query: str, top_k=5):
        query_vector = self.model.encode(
            query,
            normalize_embeddings=True,
        ).tolist()

        results = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
        )

        return [
            QueryPoint(
                score=point.score,
                text=(
                    point.payload["text"] 
                    if point.payload else ""
                ),
                document_id=(
                    point.payload["document_id"] 
                    if point.payload else ""
                )
            )
            for point in results.points
        ]

    def _chunk_text(self, text: str, chunk_size=500, overlap=50):
        words = text.split()

        chunks : list[str] = []

        start = 0
        while start < len(words):
            end = start + chunk_size

            chunks.append(
                " ".join(words[start:end])
            )

            start += chunk_size - overlap

        return chunks

    def _normalize_text(self, text):
        """
        Normalize text for comparison, matching, and
        header/footer detection.

        Does not modify the original text stored in Qdrant.
        """

        if not text:
            return ""

        # Normalize Unicode compatibility characters
        text = unicodedata.normalize("NFKC", text)

        # Quotes
        quote_map = {
            "\u2018": "'",   # left single quote
            "\u2019": "'",   # right single quote
            "\u201a": "'",   # single low-9 quote
            "\u201b": "'",   # single high-reversed-9 quote
            "\u201c": '"',   # left double quote
            "\u201d": '"',   # right double quote
            "\u201e": '"',   # double low-9 quote
            "\u201f": '"',   # double high-reversed-9 quote
        }

        for old, new in quote_map.items():
            text = text.replace(old, new)

        # Dashes / minus signs
        dash_map = {
            "\u2010": "-",   # hyphen
            "\u2011": "-",   # non-breaking hyphen
            "\u2012": "-",   # figure dash
            "\u2013": "-",   # en dash
            "\u2014": "-",   # em dash
            "\u2212": "-",   # minus sign
        }

        for old, new in dash_map.items():
            text = text.replace(old, new)

        # Non-breaking spaces
        text = text.replace("\u00a0", " ")

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip().lower()

    def _chunk_doc(self, doc: Document):
        chunk_index = 1
        leftover_chunk: ChunkData | None = None
        for page_num in range(1, len(doc) + 1):
            page = doc.load_page(page_num - 1)
            blocks = page.get_text("blocks")
            if page_num == 1:
                blocks = self._remove_header_footer(blocks, page.rect.height, header_ratio=0.2)
            else:
                blocks = self._remove_header_footer(blocks, page.rect.height)
            for block in blocks:
                x0, y0, x1, y1, text, block_no, block_type = block
                text = self._normalize_text(text)
                res =  ChunkData(text, chunk_index, page_start=page_num, page_end=page_num)
                if leftover_chunk:
                    text = leftover_chunk.text + ' ' +  text
                    res.text = text
                    res.page_start = leftover_chunk.page_start
                    leftover_chunk = None
                if self._incomplete_chunk(res):
                    leftover_chunk = res
                    continue
                yield res
                chunk_index += 1

    def _remove_header_footer(self, blocks, page_height, header_ratio = 0.1, footer_ratio = 0.85):
        cleaned = []

        for block in blocks:
            x0, y0, x1, y1, text, block_no, block_type = block
            if y1 <= page_height * header_ratio:
                continue

            if y0 >= page_height * footer_ratio:
                continue

            cleaned.append(block)

        return cleaned

    def _incomplete_chunk(self, chunk: ChunkData):
        text = chunk.text
        # print(f'|{text}| {text[-1] == '.'}')
        return False if text[-1] == '.' else True

'''
can make a chunking method that detecting headings and group metadata section for every chunk

'''

if __name__ == "__main__":
    db = VectorDB()
    test = []
    with fitz.open("eu_air_policy.pdf") as doc:
        for chunk in db._chunk_doc(doc):
            test.append({
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end
            })
            if chunk.page_start == 3:
                break
    with open('check2.json', 'w') as f:
        json.dump(test, f, indent=4)
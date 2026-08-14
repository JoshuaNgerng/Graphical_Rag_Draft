from dataclasses import dataclass
import json
from typing import cast

import re
import unicodedata
from fitz import b
from numpy import block
import pymupdf as fitz
from pymupdf import Document, Page

@dataclass
class ChunkData:
    text: str
    chunk_index: int
    page_start: int = 0
    page_end: int = 0
    section: str | None = None

@dataclass
class PDFBlockInfo:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    block_no: int
    block_type: int

class PDFParser:
    @staticmethod
    def chunk_doc(doc: Document):
        self = PDFParser
        chunk_index = 1
        leftover_chunk: ChunkData | None = None
        for page_num in range(1, len(doc) + 1):
            page = doc.load_page(page_num - 1)
            blocks = self.__get_block_info_from_page(page)
            if page_num == 1:
                blocks = self._remove_header_footer(blocks, page.rect.height, header_ratio=0.2)
            else:
                blocks = self._remove_header_footer(blocks, page.rect.height)
            for block in blocks:
                text = self._normalize_text(block.text)
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

    @staticmethod
    def _remove_header_footer(
            blocks: list[PDFBlockInfo], page_height,
            header_ratio = 0.1, footer_ratio = 0.85
    ):
        y1_lim = page_height * header_ratio
        y0_lim = page_height * footer_ratio
        return [
            b
            for b in blocks
            if (
                b.y1 > y1_lim and b.y0 < y0_lim
            )
        ]

    @staticmethod
    def _incomplete_chunk(chunk: ChunkData):
        text = chunk.text
        # print(f'|{text}| {text[-1] == '.'}')
        return False if text[-1] == '.' else True

    @staticmethod
    def _normalize_text(text: str | None):
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

    @staticmethod
    def __get_block_info_from_page(page: Page) -> list[PDFBlockInfo]:
        blocks = cast(tuple, page.get_text("blocks"))
        return [
            PDFBlockInfo(
                x0=x0, y0=y0, x1=x1, y1=y1,
                text=text, block_no=block_no, block_type=block_type
            )
            for x0, y0, x1, y1, text, block_no, block_type in blocks
        ]


'''
can make a chunking method that detecting headings and group metadata section for every chunk

'''

if __name__ == "__main__":
    test = []
    with fitz.open("eu_air_policy.pdf") as doc:
        for chunk in PDFParser.chunk_doc(doc):
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
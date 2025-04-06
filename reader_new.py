from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Union
from uuid import UUID

from loguru import logger
from mobi.mobi_header import uuid
from numpy import character
from api_module.schemas.base import SummaryInputSchema
from base_reader import HTMLtoLines, get_ebook_cls, Epub, FictionBook, Azw3, Mobi
from utils import Chunker, get_chunker
from pydantic import BaseModel
from api_module.schemas import SummaryOutputSchema


class State_attrs(Enum):
    summary = "SUM"
    characters = "SUM"
    places = "SUM"
    prompt = "PROMPT"
    image = "IMAGE"
    audio = "AUDIO"


class ChunkState(BaseModel):
    chunk_id: str
    summary: bool = False
    characters: bool = False
    places: bool = False
    prompt: bool = False
    image: bool = False
    audio: bool = False

    def is_done(self) -> bool:
        return all(
            [
                self.summary,
                self.characters,
                self.places,
                self.prompt,
                self.image,
                self.audio,
            ]
        )

    def to_do(self) -> List[State_attrs]:
        tasks = {
            "summary": "SUM",
            "characters": "SUM",
            "places": "SUM",
            "prompt": "PROMPT",
            "image": "IMAGE",
            "audio": "AUDIO",
        }

        return [getattr(State_attrs, key) for key, value in tasks.items() if not value]

    def check(self):
        pass


class ChapterState(BaseModel):
    chapter_id: int
    chunks: List[ChunkState]

    def is_done(self):
        return all(self.chunks)


class BookState(BaseModel):
    book_id: uuid.UUID
    chapters: List[ChapterState]

    def is_done(self):
        return all(self.chapters)


@dataclass
class Chunk:
    chunk_id: str
    chapter_id: int
    chunk: str
    summary: str = ""
    scene_title = ""
    prompt: str = ""
    characters: Dict[str, str] = field(default_factory=dict)
    places: Dict[str, str] = field(default_factory=dict)
    image_url: str = ""

    def __post_init__(self):
        logger.trace(f"Chunk : {self.chunk_id} set")

    def get_chunk(self) -> str:
        return self.chunk

    def set_sum(self, summary: str, characters: Dict[str, str], places: Dict[str, str]):
        self.summary = summary
        self.characters = characters
        self.places = places

    def set_prompt(self, scene_title: str, prompt: str):
        self.scene_title = scene_title
        self.prompt = prompt

    def get_sum(self):
        return SummaryInputSchema(
            past_context=self.summary,
            character_list=self.characters,
            places_list=self.places,
            current_chapter="",
        )


@dataclass
class Chapter:
    """Stores a chapter"""

    id: int
    chunker: Chunker
    title: str
    str_data: str
    html_data: str
    chunks: List[Chunk] = field(init=False)

    def __post_init__(self) -> None:
        self.set_chunks()
        logger.trace(f"Chapter : {self.id} set")

    def set_chunks(self) -> None:
        self.chunks = [
            Chunk(
                chunk_id=f"{self.id}%{idx}",
                chapter_id=self.id,
                chunk=chunk,
            )
            for idx, chunk in enumerate(self.chunker.chunk(self.str_data))
        ]

    def get_chunks_str(self) -> List[str]:
        return [i.get_chunk() for i in self.chunks]

    def get_chunks(self) -> List[Chunk]:
        return self.chunks

    def get_title(self) -> str:
        return self.title

    def get_str_data(self) -> str:
        return self.str_data

    def get_html_data(self) -> str:
        return self.html_data


@dataclass
class Book:
    """Stores a book"""

    path: str
    user_id: uuid.UUID = uuid.uuid4()
    book_id: uuid.UUID = field(default_factory=uuid.uuid4)
    file: Optional[Union[Epub, Mobi, Azw3]] = field(init=False)
    metadata: Optional[Dict[str, str]] = field(init=False, default=None)
    toc: list = field(init=False)
    chapters: list[Chapter] = field(
        default_factory=list,
        init=False,
        metadata={
            "description": "list of Chapters(class)",
        },
    )

    def __post_init__(self):
        self.chunker = get_chunker(max_len=7500)
        logger.trace("got chunker")
        file_class = get_ebook_cls(self.path)
        logger.trace("got book_file")
        if not file_class:
            raise Exception("get_book_cls returned None")
        self.file = file_class
        file_toc = self.file.contents
        if file_toc:
            self.toc = file_toc
        logger.trace("got toc")
        self.parser = HTMLtoLines()
        self.chapters = [
            self.set_chapters(idx, name) for idx, name in enumerate(self.toc)
        ]
        logger.info(f"Total Chunks {len(self.get_chunks())}")

    def set_chapters(self, id, chapter_name: str) -> Chapter:
        html_data: str = self.file.get_raw_text(chapter_name)
        self.parser.feed(html_data)
        str_data = "\n".join(self.parser.get_lines())
        self.parser.close()
        return Chapter(
            id=id,
            title=chapter_name,
            str_data=str_data,
            html_data=html_data,
            chunker=self.chunker,
        )

    def get_toc(self) -> list:
        return self.toc

    def get_file(self):
        return self.file

    def get_str_chapters(self) -> dict:
        return {i.get_title(): i.get_str_data() for i in self.chapters}

    def get_html_chapters(self) -> dict:
        return {i.get_title(): i.get_html_data() for i in self.chapters}

    def get_chunks(self) -> List[Chunk]:
        return [chunk for chapter in self.chapters for chunk in chapter.chunks]

    def get_chapters(self) -> List[Chapter]:
        return self.chapters

    def is_sum_done(self) -> bool:
        return all(i.summary != "" for i in self.get_chunks())

    def is_prompt_done(self) -> bool:
        return all(i.prompt != "" for i in self.get_chunks())


def main() -> None:
    file = Book("./test_books/PP.epub", user_id=uuid.uuid4())

    print(file.is_sum_done())


if __name__ == "__main__":
    main()

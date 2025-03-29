from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict
from uuid import UUID

from mobi.mobi_header import uuid
from base_reader import HTMLtoLines, get_ebook_cls, Epub, FictionBook, Azw3, Mobi
from utils import Chunker, get_chunker
from pydantic import BaseModel


class State_attrs(Enum):
    summary = "summary"
    characters = "characters"
    places = "places"
    prompt = "prompt"
    image = "prompt"
    audio = "audio"


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
        "summary": self.summary,
        "characters": self.characters,
        "places": self.places,
        "image": self.image,
        "audio": self.audio,
    }

    return [getattr(State_attrs, key) for key, value in tasks.items() if not value]


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
    _chunk_id: str
    _chapter_id: int
    _chunk: str
    _summary: Optional[str] = None
    _prompt: Optional[str] = None

    def get_chunk(self) -> str:
        return self._chunk


@dataclass
class Chapter:
    """Stores a chapter"""

    _id: int
    _chunker: Chunker
    _title: str
    _str_data: str
    _html_data: str
    _chunks: List[Chunk] = field(init=False)

    def __post_init__(self) -> None:
        self.set_chunks()

    def set_chunks(self) -> None:
        self._chunks = [
            Chunk(
                _chunk_id=f"{self._id}%{idx}",
                _chapter_id=self._id,
                _chunk=chunk,
            )
            for idx, chunk in enumerate(self._chunker.chunk(self._str_data))
        ]

    def get_chunks_str(self) -> List[str]:
        return [i.get_chunk() for i in self._chunks]

    def get_chunks(self) -> List[Chunk]:
        return self._chunks

    def get_title(self) -> str:
        return self._title

    def get_str_data(self) -> str:
        return self._str_data

    def get_html_data(self) -> str:
        return self._html_data


@dataclass
class Book:
    """Stores a book"""

    _path: str
    _user_id: uuid.UUID
    _book_id: uuid.UUID = field(default_factory=uuid.UUID)
    _file: Epub | Mobi | Azw3 | FictionBook = field(init=False)
    _metadata: Optional[Dict[str, str]] = field(init=False, default=None)
    _toc: list = field(init=False)
    _chapters: list[Chapter] = field(
        default_factory=list,
        init=False,
        metadata={
            "description": "list of Chapters(class)",
        },
    )

    def __post_init__(self):
        self._chunker = get_chunker(max_len=7000)
        file = get_ebook_cls(self._path)
        if not file:
            raise Exception("get_book_cls returned None")
        self._file = file
        self._toc = self._file.contents
        self._parser = HTMLtoLines()
        self._chapters = [
            self._set_chapters(idx, name) for idx, name in enumerate(self._toc)
        ]

    def _set_chapters(self, id, chapter_name: str) -> Chapter:
        html_data: str = self._file.get_raw_text(chapter_name)
        self._parser.feed(html_data)
        str_data = "\n".join(self._parser.get_lines())
        self._parser.close()
        return Chapter(
            _id=id,
            _title=chapter_name,
            _str_data=str_data,
            _html_data=html_data,
            _chunker=self._chunker,
        )

    def toc(self) -> list:
        return self._toc

    def file(self):
        return self._file

    def get_str_chapters(self) -> dict:
        return {i.get_title(): i.get_str_data() for i in self._chapters}

    def get_html_chapters(self) -> dict:
        return {i.get_title(): i.get_html_data() for i in self._chapters}

    def get_chunks(self) -> List[List[Chunk]]:
        return [i.get_chunks() for i in self._chapters]


def main() -> None:
    import time

    start = time.time()
    file = Book("./test_books/PP.epub", _user_id=uuid.uuid4())
    end = time.time()
    print(end - start)
    chunks = len(file.get_chunks())
    print(chunks)


if __name__ == "__main__":
    main()

from ebooklib import epub
import ebooklib

from dataclasses import dataclass, field
import fitz
from typing import Optional, Dict

import os
from zipfile import ZipFile


@dataclass()
class Chapters:
    """Stores a chapter"""

    _title: str
    _paras: str
    _len_by_words: int = field(metadata={"description": "Length of chapters by word"})
    _page_count: int = field(init=False)
    _split: int = field(
        metadata={
            "description": "how many times will this chapter be spilt, incase of length issue",
        }
    )


@dataclass()
class Book:
    """Stores a book"""

    _metadata: Optional[Dict[str, str]] = field(init=False)
    _toc: list = field(init=False)

    _chapters: list[Chapters] = field(
        default_factory=list,
        init=False,
        metadata={
            "description": "list of Chapters(class)",
        },
    )


@dataclass()
class Reader:
    path: str
    _file: fitz.Document = field(init=False)

    def __post_init__(self):
        """
        Check the type of book and return a valid epub format

        """
        pass


def main() -> None:
    with ZipFile("./books/LP.epub", "b") as zip:
        print(zip.infolist())


if __name__ == "__main__":
    main()

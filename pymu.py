from typing import Dict, Optional, Tuple
import fitz
import mobi
import os
from dataclasses import dataclass, field
import sys
from loguru import logger


def printl(ls, space=1):
    line_breaks = "\n"
    for _ in range(space):
        line_breaks += "\n"

    for i in ls:
        print(i, end=line_breaks)


def printd(dir: dict, space: int = 1):
    scape = "\n"
    for _ in range(space):
        scape += "\n"
    for key, value in dir.items():
        print(f"{key} : {value}", end=scape)


def printt(tou: list):
    for i in tou:
        print("---------------------------" + i[0] + "---------------------------")
        print(i[1])


@dataclass
class ebook:
    path: str
    file: fitz.Document = field(init=False)
    page_count: int = field(init=False)
    toc: list = field(init=False)
    chapters: list = field(default_factory=list, init=False)

    def __post_init__(self):
        filext = os.path.splitext(self.path)[1].lower()

        if filext in {".azw3", ".epub", ".mobi", ".pdf"}:
            if filext == ".azw3":
                self.path = to_epub(self.path)
            try:
                self.file = fitz.open(self.path)
            except Exception as e:
                print(f"{self.path}: file is currupted : {e}")
        else:
            sys.exit("ERROR: Format not supported. (Supported: epub, mobi, azw3, pdf)")

        self.toc = self.file.get_toc()
        self.metadata = self.file.metadata
        self.page_count = self.file.page_count

        if (self.toc != 0) and self.toc is not None:
            for idx, (lvl, chp, start_page) in enumerate(self.toc):
                # Determine start and end pages for the current chapter
                start_index = start_page - 1  # Convert to 0-based indexing
                end_index = (
                    self.toc[idx + 1][2] - 1
                    if idx + 1 < len(self.toc)
                    else self.page_count - 1
                )

                # Collect text for the range of pages
                chapter_text = []
                for page_num in range(start_index, end_index + 1):  # Inclusive range
                    page = self.file.load_page(page_num)
                    chapter_text.append(page.get_text())  # Append text from each page

                # Join collected text and store it in the dictionary
                self.chapters.append((chp, "".join(chapter_text)))
        else:
            raise Exception("Table of contents are empty")

    def get_toc_list(self) -> list:
        return self.toc

    def get_metadata(self) -> Optional[Dict[str, str]]:
        return self.metadata

    def get_book(self) -> fitz.Document:
        return self.file

    def get_chapters(self) -> list:
        return self.chapters

    @staticmethod
    def to_epub(azw3: str) -> str:
        _, epub = mobi.extract(azw3)
        return epub


def main():
    book = ebook("./LP.azw3")
    ch = book.get_chapters()
    printt(ch)


if __name__ == "__main__":
    main()

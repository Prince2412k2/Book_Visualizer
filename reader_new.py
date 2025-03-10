from dataclasses import dataclass, field
from typing import Optional, Dict, Self
from new_read import HTMLtoLines, det_ebook_cls, Epub, FictionBook, Azw3, Mobi
from loguru import logger
import sys

logger.remove()
logger.add(sys.stdout)
logger.add("app.log", format="{time} | {level} | {message} | {extra} ", level="DEBUG")


@dataclass
class Chapters:
    """Stores a chapter"""

    _title: str
    _str_data: str
    _html_data: str

    def get_title(self):
        return self._title

    def get_str_data(self):
        return self._str_data

    def get_html_data(self):
        return self._html_data


@dataclass
class Book:
    """Stores a book"""

    _path: str
    _file: Epub | Mobi | Azw3 | FictionBook = field(init=False)
    _metadata: Optional[Dict[str, str]] = field(init=False, default=None)
    _toc: list = field(init=False)
    _chapters: list[Chapters] = field(
        default_factory=list,
        init=False,
        metadata={
            "description": "list of Chapters(class)",
        },
    )

    def __post_init__(self):
        self._file = det_ebook_cls(self._path)
        self._toc = self._file.contents
        self._chapters = [self._set_chapters(i) for i in self._toc]

    def _set_chapters(self, chapter_name: str):
        html_data: str = self._file.get_raw_text(chapter_name)
        parser = HTMLtoLines()
        parser.feed(html_data)
        str_data = "\n".join(parser.get_lines())
        parser.close()
        return Chapters(_title=chapter_name, _str_data=str_data, _html_data=html_data)

    def toc(self):
        return self._toc

    def file(self):
        return self._file

    def get_str_chapters(self) -> dict:
        return {i.get_title(): i.get_str_data() for i in self._chapters}

    def get_html_chapters(self) -> dict:
        return {i.get_title(): i.get_html_data() for i in self._chapters}


def main() -> None:
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.success("This is a success message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")


if __name__ == "__main__":
    main()

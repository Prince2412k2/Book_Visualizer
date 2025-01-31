from typing import Dict, Optional
import fitz
import mobi
import os
from dataclasses import dataclass, field
import sys
from ebooklib import epub
import ebooklib

## utils


@dataclass
class ebook:
    path: str
    _file: fitz.Document = field(init=False)
    _metadata: Optional[Dict[str, str]] = field(init=False)
    _page_count: int = field(init=False)
    _toc: list = field(init=False)
    _chapters: list = field(default_factory=list, init=False)

    def __post_init__(self):
        # Handle types of file
        filext = os.path.splitext(self.path)[1].lower()

        if filext in {".azw3", ".epub", ".mobi", ".pdf"}:
            if filext == ".azw3":
                self.path = self.to_epub(self.path)
                filext = ".epub"
            try:
                self._file = fitz.open(self.path)
            except Exception as e:
                print(f"{self.path}: file is currupted : {e}")
        else:
            sys.exit("ERROR: Format not supported. (Suppor0ted: epub, mobi, azw3, pdf)")

        # Generatres table of contents ,metadata, page_count
        self._toc = self._file.get_toc()
        self._metadata = self._file.metadata
        self._page_count = self._file.page_count

        #   separates chapters by pages outputs a list->[(chapter-name,content),]
        if self._toc:
            for idx, (lvl, chp, start_page) in enumerate(self._toc):
                # Determine start and end pages for the current chapter
                start_index = start_page - 1  # Convert to 0-based indexing
                end_index = (
                    self._toc[idx + 1][2] - 1
                    if idx + 1 < len(self._toc)
                    else self._page_count - 1
                )
                # Collect text for the range of pages
                chapter_text = []
                for page_num in range(start_index, end_index + 1):  # Inclusive range
                    page = self._file.load_page(page_num)
                    chapter_text.append(page.get_text())  # Append text from each page

                # Join collected text and store it in Tuple
                self._chapters.append((chp, "".join(chapter_text)))
        else:
            self._chapters = [
                (i, self._file.load_page(i).get_text()) for i in range(self._page_count)
            ]
            # chapters=[(i,obj.load_page(i).get_text()) for i in range(obj.page_count)]

    # Handle getters
    def get_toc_list(self) -> list:
        return self._toc

    def get_metadata(self) -> Optional[Dict[str, str]]:
        return self._metadata

    def get_book(self) -> fitz.Document:
        return self._file

    def get_chapters(self) -> list:
        return self._chapters

    def get_page_count(self) -> int:
        return self._page_count

    @staticmethod
    def to_epub(azw3: str) -> str:
        _, epub = mobi.extract(azw3)
        return epub


def main():
    book = ebook("./books/gen_LP.epub")
    a = {
        "meta": book.get_metadata(),
        "toc": book.get_toc_list(),
        #        "book": book.get_book(),
        "chapters": book.get_chapters(),
    }
    print(a["toc"])


def extract_images_from_epub(file_path):
    book = epub.read_epub(file_path)
    output_dir = "output/Images"

    # Create a directory to store extracted images
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Loop through all items in the EPUB file
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        name = item.get_name()
        # Sanitize the name to create a valid file path
        sanitized_name = name.replace("/", "_").replace("\\", "_")
        content = item.get_content()

        with open(os.path.join(output_dir, sanitized_name), "wb") as img_file:
            img_file.write(content)
            print(f"Extracted image: {sanitized_name}")


def test():
    book = extract_images_from_epub("./books/HP.epub")


if __name__ == "__main__":
    main()

from dataclasses import dataclass, field
import json
import os
from os.path import exists
from typing import List, Optional, Dict, Union
from PIL import Image as pil_img
from io import BytesIO
import uuid
import requests
import time

from logger_module import logger

# from .api_module import SummaryContentSchema
from base_reader import HTMLtoLines, get_ebook_cls, Epub, Azw3, Mobi
from utils import Chunker, get_chunker
from pydantic import BaseModel, ValidationError


def fetch_image_with_retries(
    url: str, retries: int = 3, delay: int = 2
) -> Optional[bytes]:
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.content
            else:
                raise Exception(f"Status code: {response.status_code}")
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed to fetch image: {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                raise Exception(f"All {retries} attempts failed for URL: {url}")


def save_image(path: str, img_bytes: bytes) -> None:
    try:
        buffer = BytesIO()
        image = pil_img.open(BytesIO(img_bytes))
        image.save(buffer, format="WEBP")
        webp_bytes = buffer.getvalue()

        with open(path, "wb") as f:
            f.write(webp_bytes)

        logger.info(f"Image saved at: {path}")
    except Exception as e:
        logger.error(f"Error saving image: {e}")


def fetch_and_save_image(url: str, path: str) -> None:
    try:
        img_bytes = fetch_image_with_retries(url)
        if img_bytes:
            save_image(path, img_bytes)
    except Exception as e:
        logger.error(f"Failed to fetch and save image from {url}: {e}")


def save_audio(content: bytes, path: str) -> None:
    try:
        with open(path, "wb") as f:
            f.write(content)
        logger.info(f"Audio saved at: {path}")
    except Exception as e:
        logger.error(f"Failed to save audio at {path}: {e}")


class BookArchivedState(BaseModel):
    name: str
    chunks: List[Optional[dict]]

    def __repr__(self):
        return f"Archive({self.chunks})"


def archive_reader(path) -> dict:
    with open(path, "r") as file:
        data = file.read()
    json_data = json.loads(data)
    return ChunkState.model_validate(json_data).model_dump(
        exclude={"prompt", "characters", "places"}
    )


def load_archived(user, name):
    book_path = f"./uploaded_books/{user}/{name}"
    state_path = book_path + "/book_state.json"
    if not os.path.exists(state_path):
        return False
    with open(state_path, "r") as file:
        data = file.read()
    json_data = json.loads(data)
    book_state = BookState.model_validate(json_data)
    chunks = book_state.chunks
    return BookArchivedState(
        name=name,
        chunks=[
            archive_reader(
                f"{book_path}{os.sep}{chunk.split('/')[0]}{os.sep}{chunk.split('/')[1]}/state.json"
            )
            for chunk in chunks
        ],
    )


class ChunkState(BaseModel):
    chunk_id: str
    chapter_id: str
    summary: str = ""
    characters: Dict[str, str] = field(default_factory=dict)
    places: Dict[str, str] = field(default_factory=dict)
    scene_title: str = ""
    prompt: str = ""
    image: str = ""
    audio: bool = False
    is_done: bool = False

    def __repr__(self) -> str:
        return f"ChunkState(sum=\n{self.summary}\n,image=\n{self.image}\n"


class BookState(BaseModel):
    name: str
    book_id: str
    chunks: List[str]
    is_done: bool = False


@dataclass
class Chunk:
    chapter_id: str
    chunk: str
    user_id: str = ""
    chunk_id: str = ""
    path: str = ""
    summary: str = ""
    scene_title = ""
    prompt: str = ""
    characters: Dict[str, str] = field(default_factory=dict)
    places: Dict[str, str] = field(default_factory=dict)
    image_url: str = ""
    image_id: str = ""
    audio: bool = False
    chunk_state: Optional[ChunkState] = None
    is_done: bool = False

    def __post_init__(self):
        self.path = f"{self.path}/{self.chunk_id}"
        if not os.path.exists(self.path):
            os.mkdir(self.path)

        self.init()
        logger.trace(f"Chunk : {self.chunk_id} set")

    def init(self):
        if not self.load_it():
            self.chunk_state = ChunkState(
                chunk_id=self.chunk_id,
                chapter_id=self.chapter_id,
                summary=self.summary,
                characters=self.characters,
                places=self.places,
                prompt=self.prompt,
                scene_title=self.scene_title,
                image=self.image_url,
            )
            self.dump_it()
        else:
            assert self.chunk_state
            self.summary = self.chunk_state.summary
            self.prompt = self.chunk_state.prompt
            self.image_url = self.chunk_state.image
            self.characters = self.chunk_state.characters
            self.places = self.chunk_state.places
            self.scene_title = self.chunk_state.scene_title
            self.audio = self.chunk_state.audio

    def get_chunk(self) -> str:
        return self.chunk

    def set_sum(self, summary: str, characters: Dict[str, str], places: Dict[str, str]):
        self.summary = summary
        self.characters = characters
        self.places = places

        assert self.chunk_state
        self.chunk_state.characters = self.characters
        self.chunk_state.places = self.places
        self.chunk_state.summary = self.summary
        self.dump_it()

    def set_prompt(self, scene_title: str, prompt: str):
        self.scene_title = scene_title
        self.prompt = prompt

        assert self.chunk_state
        self.chunk_state.prompt = self.prompt
        self.chunk_state.scene_title = self.scene_title
        self.dump_it()

    def set_img(self, url: str, task_id: str):
        self.image_url = url
        self.image_id = task_id
        # save_img(url=url, path=f)
        try:
            fetch_and_save_image(url=url, path=f"{self.path}/img.webp")
            assert self.chunk_state
            self.chunk_state.image = url
        except Exception as e:
            print("error saving image : ", e)
        self.dump_it()

    def set_audio(self, content: bytes):
        temp_path = f"{self.path}/audio.mp3"
        assert self.chunk_state
        self.audio = True
        self.chunk_state.audio = True
        save_audio(content=content, path=temp_path)
        self.dump_it()

    def get_sum(self):
        return SummaryContentSchema(
            past_context=self.summary,
            character_list=self.characters,
            places_list=self.places,
            current_chapter="",
        )

    def set_state(self):
        assert self.chunk_state
        if self.chunk_state.summary and self.chunk_state.prompt and self.image_url:
            self.chunk_state.is_done = True
            self.dump_it()

    def dump_it(self):
        assert self.chunk_state is not None
        json_state = self.chunk_state.model_dump_json(indent=4)

        with open(f"{self.path}/state.json", "w") as file:
            file.write(json_state)

    def load_it(self):
        state_path = f"{self.path}/state.json"
        if os.path.exists(state_path):
            with open(state_path, "r") as file:
                try:
                    self.chunk_state = ChunkState.model_validate_json(file.read())
                except ValidationError:
                    return False
                logger.info("Loading chunk from state")
                return True

    def __repr__(self) -> str:
        return f"{self.chapter_id}:{self.scene_title}"


@dataclass
class Chapter:
    """Stores a chapter"""

    chapter_id: str
    user_id: str
    chunker: Chunker
    title: str
    str_data: str
    html_data: str
    chapter_path: str
    chunks: List[Chunk] = field(init=False)

    def __post_init__(self) -> None:
        self.chapter_path = f"{self.chapter_path}/{self.chapter_id}"
        if not os.path.exists(self.chapter_path):
            os.mkdir(self.chapter_path)
        self.set_chunks()
        logger.trace(f"Chapter : {self.chapter_id} set")

    def set_chunks(self) -> None:
        self.chunks = [
            Chunk(
                chunk_id=f"{idx + 1}",
                chapter_id=self.chapter_id,
                user_id=self.user_id,
                chunk=chunk,
                path=self.chapter_path,
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

    def __repr__(self) -> str:
        return f"{self.chapter_id}"


@dataclass
class Book:
    """Stores a book"""

    path: str
    name: str = ""
    path_content: str = ""
    user_id: str = str(uuid.uuid4())
    book_id: str = field(default=str(uuid.uuid4()))
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
    book_state: Optional[BookState] = None

    def __post_init__(self):
        if not self.name:
            self.name = os.path.splitext(self.path)[0]
            self.name = self.name.split(os.sep)[-1]

        self.path_content = (
            self.path_content + f"./uploaded_books/{self.user_id}/{self.name}"
        )

        if not os.path.exists(self.path_content):
            os.makedirs(self.path_content)
        else:
            logger.info("Path is is there for given book")
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
            self.set_chapters(id=idx + 1, chapter_name=name)
            for idx, name in enumerate(self.toc)
        ]
        logger.info(f"Total Chunks {len(self.get_chunks())}")
        self.init_state()
        self.load_it()

    def init_state(self):
        dump_chunks = [f"{i.chapter_id}/{i.chunk_id}" for i in self.get_chunks()]
        self.book_state = BookState(
            name=self.name, book_id=self.book_id, chunks=dump_chunks
        )
        self.dump_it()

    def set_chapters(self, id, chapter_name: str) -> Chapter:
        assert self.file
        html_data: str = self.file.get_raw_text(chapter_name)
        self.parser.feed(html_data)
        str_data = "\n".join(self.parser.get_lines())
        self.parser.close()
        return Chapter(
            chapter_id=str(id),
            user_id=self.user_id,
            title=chapter_name,
            str_data=str_data,
            html_data=html_data,
            chunker=self.chunker,
            chapter_path=self.path_content,
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

    def is_audio_done(self) -> bool:
        return all(i.audio for i in self.get_chunks())

    def is_img_done(self) -> bool:
        return all(i.image_url != "" for i in self.get_chunks())

    def is_done(self):
        assert self.book_state
        if self.is_sum_done() and self.is_prompt_done() and self.is_img_done():
            self.book_state.is_done = True
            self.dump_it()
            return True
        else:
            return False

    def dump_it(self):
        assert self.book_state
        json_state = self.book_state.model_dump_json(indent=4)
        with open(f"{self.path_content}/book_state.json", "w") as file:
            file.write(json_state)

    def load_it(self):
        book_state_path = f"{self.path_content}/book_state.json"
        if os.path.exists(book_state_path):
            with open(book_state_path, "r") as file:
                try:
                    self.book_state = BookState.model_validate_json(file.read())
                except ValidationError:
                    return False

    def __repr__(self) -> str:
        return f"Name:{self.name} , Chapters:{len(self.chapters)}, Chunks : {len(self.get_chunks())}"


def test():
    state = load_archived(user="b5bfc116-dd81-475a-8425-537a50621706", name="AF")
    print(state)


def main() -> None:
    book: Book = Book(
        "./test_books/AF.epub", user_id="b5bfc116-dd81-475a-8425-537a50621706"
    )
    for i in book.get_chunks():
        print(i.chapter_id, " ", i.chunk_id)
        if i.image_url:
            continue

        # assert i
        # if not i.places or not i.characters:
        #   continue
        print("-" * 50)
        print(f"Chapter:{i.chapter_id}-{i.chunk_id}")

        print("Summary")
        print(f"\t - {i.summary}")
        print()

        print("characters")
        for k, v in i.characters.items():
            print(f"\t - {k} : {v}")
        print()

        print("places")
        for k, v in i.places.items():
            print(f"\t - {k} : {v}")

        print("prompt")
        print(f"{i.scene_title} : {i.prompt} ")
        print("\n\n")

        print("IMAGE")
        print(f"{i.scene_title} : {i.image_url} ")
        print("\n\n")
        break


if __name__ == "__main__":
    test()

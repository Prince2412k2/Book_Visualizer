from typing import List, Optional, Union, Tuple
from huggingface_hub import login
from joblib.memory import tokenize
from numpy import append
from transformers import AutoTokenizer
from dataclasses import dataclass
from logger_module import logger
import asyncio


@dataclass
class Tokenizer:
    api_key: str
    model_name: str = "mistralai/Mistral-Nemo-Instruct-2407"

    def __post_init__(self):
        try:
            login(token=self.api_key)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        except Exception as error:
            logger.error(f"Error while downloading tokenizer, {error=}")

    async def tokenize(self, text: str) -> Optional[Tuple[int, List[int]]]:
        try:
            tokens: List[int] = self.tokenizer.encode(text, add_special_tokens=False)
        except Exception as error:
            logger.warning(f"Error while counting token, {error=}")
            return 0, []
        return len(tokens), tokens

    async def detokenize(self, tokens: List[int]) -> Optional[str]:
        try:
            decoded_text = self.tokenizer.decode(tokens)
            return decoded_text
        except Exception as error:
            logger.error(f"Error while Decoading tokens, {error=}")


@dataclass
class Chunker:
    max_len: int
    tokenizer: Tokenizer

    async def chunk(self, content: List[Tuple[str, str]]) -> List[Tuple[str, str, str]]:
        """
        Splits text into chunks that do not exceed the token limit.

        -> List of (Id: str, chunk_text: str)
        """
        total_chunks = []

        for id, (orig_id, text) in enumerate(content):
            num_tokens, tokens = await self.tokenizer.tokenize(text)
            count = 1
            start = 0
            while start < num_tokens:
                chunk_tokens = tokens[start : start + self.max_len]
                chunk_text = await self.tokenizer.detokenize(chunk_tokens)
                chunk_id = f"CH{id}C{count}"
                total_chunks.append((chunk_id, orig_id, chunk_text))
                count += 1
                start += self.max_len  # Move to next chunk

        return total_chunks


##test
from reader import ebook


async def main():
    tokenizer = Tokenizer()
    chunker = Chunker(max_len=200, tokenizer=tokenizer)
    book = ebook(("./books/HP.epub"))
    chpt = book.get_chapters()

    chunks = await chunker.chunk(chpt[1:2])
    print((chpt[1][1]) == "".join([chunk[2] for chunk in chunks]))


asyncio.run(main())

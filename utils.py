from typing import List, Optional, Union, Tuple
from huggingface_hub import login
from transformers import AutoTokenizer
from dataclasses import dataclass
from logger_module import logger
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"


@dataclass
class Tokenizer:
    api_key: str
    model_name: str = "meta-llama/Llama-3.1-8B-Instruct"

    def __post_init__(self):
        try:
            login(token=os.environ.get("HF_API"))
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        except Exception as error:
            logger.error(f"Error while downloading tokenizer, {error=}")

    def tokenize(self, text: str) -> Optional[Tuple[int, List[int]]]:
        try:
            tokens: List[int] = self.tokenizer.encode(text, add_special_tokens=False)
        except Exception as error:
            logger.warning(f"Error while counting token, {error=}")
            return 0, []
        return len(tokens), tokens

    def detokenize(self, tokens: List[int]) -> Optional[str]:
        try:
            decoded_text = self.tokenizer.decode(tokens)
            return decoded_text
        except Exception as error:
            logger.error(f"Error while Decoading tokens, {error=}")


@dataclass
class Chunker:
    max_len: int
    tokenizer: Tokenizer

    def chunk(self, content: List[Tuple[str, str]]) -> List[Tuple[str, str, str]]:
        """
        Splits text into chunks that do not exceed the token limit.

        -> List of (Id: str, chunk_text: str)
        """
        total_chunks = []

        for id, (orig_id, text) in enumerate(content):
            num_tokens, tokens = self.tokenizer.tokenize(text)
            count = 1
            start = 0
            while start < num_tokens:
                chunk_tokens = tokens[start : start + self.max_len]
                chunk_text = self.tokenizer.detokenize(chunk_tokens)
                chunk_id = f"${id}#{count}"
                total_chunks.append((chunk_id, orig_id, chunk_text))
                count += 1
                start += self.max_len  # Move to next chunk

        return total_chunks


def main():
    tokenizer = AutoTokenizer.from_pretrained(
        pretrained_model_name_or_path="meta-llama/Llama-3.1-8B-Instruct"
    )

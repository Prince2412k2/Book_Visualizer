from typing import List, Optional, Union, Tuple
from huggingface_hub import login
from transformers import AutoTokenizer
from dataclasses import dataclass
from logger_module import logger
import os
import unicodedata
import codecs
from dotenv import load_dotenv

load_dotenv()


def normalize_text(text) -> str:
    # Decode all escape sequences (e.g., \n, \u3000, \xNN)
    text = codecs.decode(text, "unicode_escape")

    # Normalize Unicode (fixes accents, special symbols, converts full-width to half-width)
    text = unicodedata.normalize("NFKC", text)

    # Remove excessive spaces and newlines
    text = " ".join(text.split())

    return text


@dataclass
class Tokenizer:
    _instance = None  # Store the single instance
    api_key: Optional[str]
    model_name: str = "meta-llama/Llama-3.1-8B-Instruct"

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __post_init__(self):
        hf_api = os.environ.get("HF_API")
        if not hf_api:
            raise Exception("HF_API for Tokenizer is Null")
        try:
            login(token=hf_api)
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, use_fast=True, trust_remote_code=True
            )
        except Exception as error:
            logger.error(f"Error while downloading tokenizer, {error=}")
        return self

    def tokenize(self, text: str) -> Tuple[int, List[int]]:
        try:
            tokens: List[int] = self.tokenizer.encode(
                text, add_special_tokens=False, truncation=False
            )
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
    _instance = None  # Store the single instance
    max_len: int
    tokenizer: Tokenizer

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def chunk(self, str_content: str) -> List[str]:
        """
        Splits text into chunks that do not exceed the token limit.

        -> List[str]
        """
        total_chunks = []

        clean_text = normalize_text(str_content)
        if clean_text is not None:
            num_tokens, tokens = self.tokenizer.tokenize(clean_text)
        else:
            raise Exception("normalize_text raised an error")
        start, count = 0, 1
        while start < num_tokens:
            chunk_tokens = tokens[start : start + self.max_len]
            chunk_text = self.tokenizer.detokenize(chunk_tokens)
            total_chunks.append(chunk_text)
            count += 1
            start += self.max_len  # Move to next chunk
        return total_chunks


def get_chunker(max_len):
    tokenizer = Tokenizer(os.environ.get("HF_API"))
    return Chunker(max_len=max_len, tokenizer=tokenizer)

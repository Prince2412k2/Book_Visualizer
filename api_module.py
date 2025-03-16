from typing import Dict, List, Optional, Type, Tuple
from pydantic import BaseModel, Field, ValidationError
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from logger_module import logger
from utils import Chunker, Tokenizer
import requests
import asyncio
from prompts import SUMMARY_ROLE
from json.decoder import JSONDecodeError
import os
from dotenv import load_dotenv
import time

load_dotenv()
summary_role = ""


## HeadersSchema
class HeadersSchema(BaseModel):
    authorization: str = Field(..., alias="Authorization")
    content_type: str = Field(default="application/json", alias="Content-Type")

    @classmethod
    def create(cls, api_key: str) -> "HeadersSchema":
        return cls(Authorization=f"Bearer {api_key}")

    class Config:
        populate_by_name = True


## PayloadSchema
class GrammarSchema(BaseModel):
    type_: str = Field(alias="type", default="json")
    value: dict = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class ParameterSchema(BaseModel):
    repetition_penalty: Optional[float] = 1.3
    grammar: GrammarSchema


class MessageSchema(BaseModel):
    role: str
    content: str


class SummaryPayloadSchema(BaseModel):
    model: str
    messages: List[MessageSchema]
    temperature: float
    stream: bool
    max_completion_tokens: int = 2048
    response_format: Dict[str, str] = {"type": "json_object"}


class SummaryResponseSchema(BaseModel):
    summary: str
    characters: Dict[str, str]
    places: Dict[str, str]


class SummaryOutputSchema(SummaryResponseSchema):
    id: str


class SummaryContentSchema(BaseModel):
    past_context: str
    current_chapter: str
    character_list: Dict[str, str]
    places_list: Dict[str, str]


##Requests


class LLM_API(ABC):
    @abstractmethod
    def messages(
        self, content: str, character: Dict[str, str], places: Dict[str, str]
    ) -> List[MessageSchema]:
        pass

    @abstractmethod
    def get(self, message: List[MessageSchema]) -> str:
        pass

    @abstractmethod
    def validate_json(
        self, raw_data: str, schema: Type[BaseModel]
    ) -> Optional[Type[BaseModel]]:
        pass


@dataclass
class Summary:
    api_key: str
    url: str = "https://api.groq.com/openai/v1/chat/completions"
    role: str = SUMMARY_ROLE
    model: str = "llama-3.1-8b-instant"
    temperature: float = 0.1
    stream: bool = False
    repetition_penalty: float = 1.5
    max_tokens: int = 6000

    def messages(
        self,
        content: str,
        previous_summary: str,
        characters: Dict[str, str],
        places: Dict[str, str],
    ) -> List[MessageSchema]:
        return [
            MessageSchema(role="system", content=self.role),
            MessageSchema(
                role="user",
                content=SummaryContentSchema(
                    past_context=previous_summary,
                    current_chapter=content,
                    character_list=characters,
                    places_list=places,
                ).model_dump_json(by_alias=True),
            ),
        ]

    def get(self, messages: List[MessageSchema]) -> Tuple[bool, str]:
        payload = SummaryPayloadSchema(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            stream=self.stream,
            parameters=ParameterSchema(
                repetition_penalty=self.repetition_penalty,
                grammar=GrammarSchema(value=SummaryResponseSchema.model_json_schema()),
            ),
        ).model_dump()

        headers = HeadersSchema.create(api_key=self.api_key).model_dump(by_alias=True)
        response = requests.post(url=self.url, headers=headers, json=payload)
        if response.status_code == 200:
            response_data = response.json()
            assistant_message = response_data["choices"][0]["message"]["content"]
            return False, assistant_message
        else:
            logger.warning(f"Error: {response.json()}")
            return True, "ERROR_API_CALL"

    def validate_json(
        self, raw_data: str, schema: Type[SummaryResponseSchema]
    ) -> Optional[SummaryResponseSchema]:
        """
        Validates JSON data against a provided Pydantic schema.

        :param data: JSON string to be validated.
        :param schema: A Pydantic model class to validate against.
        :return: A tuple where the first element is a boolean indicating if there was an error,
                 and the second element is either the validated data or a list of error details.
        """
        try:
            parsed_data = json.loads(raw_data)
            validated_data = schema.model_validate(parsed_data)
            return validated_data
        except (ValidationError, JSONDecodeError):
            logger.warning("ValidationError")


class SummaryLoop(BaseModel):
    content: List[Tuple[str, str]]
    summary: Summary
    summary_pool: List[SummaryOutputSchema] = Field(default_factory=list)
    chunked_content: List[Tuple[str, str, str]] = Field(default_factory=list)

    def initialize(self) -> Optional["SummaryLoop"]:
        hf_api = os.environ.get("HF_API")
        if not hf_api:
            logger.error("[SummaryLoop] HF_API Not defined ")
            return None

        self.summary_pool = [
            SummaryOutputSchema(
                summary="This is The first chapeter There is No context",
                places={},
                characters={},
                id="",
            ),
        ]
        tokenizer = Tokenizer(api_key=hf_api)
        logger.trace("tokenizer set")
        chunker = Chunker(max_len=self.summary.max_tokens, tokenizer=tokenizer)
        logger.trace("Chunker set")
        self.chunked_content = chunker.chunk(content=self.content)
        logger.trace("Chapters Chunked")

        return self

    def run(self) -> None:
        """
        Assuming book comes in the form of ((id,title_chapter,chapter_content),..)
        """
        for idx, (id, title, content) in enumerate(self.chunked_content):
            past_context = self.summary_pool[idx]
            message = self.summary.messages(
                content=content,
                previous_summary=past_context.summary,
                characters=past_context.characters,
                places=past_context.places,
            )
            error, response = self.summary.get(messages=message)

            if not error:
                validated_response = self.summary.validate_json(
                    response, SummaryResponseSchema
                )

                if validated_response is not None:
                    logger.trace(f"Chunk_{id=} Done")
                    self.summary_pool.append(
                        SummaryOutputSchema(**validated_response.model_dump(), id=id)
                    )
                    time.sleep(20)
                    continue

            self.summary_pool.append(past_context)
            logger.warning(f"error getting {id=}")

    @property
    def get_summary_pool(self):
        return self.summary_pool


async def test() -> None:
    from reader import ebook

    api = os.environ.get("GROQ_API")
    if not api:
        raise Exception("API NOT SET IN .env, HF_API=None")

    book = ebook("./exp_book/LP.epub")
    chapter_content = book.get_chapters()

    sum = Summary(
        api_key=api,
    )

    looper = SummaryLoop(content=chapter_content, summary=sum).initialize()
    if not looper:
        return None
    looper.run()
    for i in looper.get_summary_pool:
        if not i.places or not i.characters:
            continue
        print("-" * 50)
        print(f"Chapter:{i.id}")
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
        print("\n\n")


if __name__ == "__main__":
    asyncio.run(test())

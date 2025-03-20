from typing import Dict, List, Optional, Type, Tuple, Union
from pydantic import BaseModel, Field, ValidationError
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json

from logger_module import logger
from utils import Chunker, Tokenizer
import requests
import asyncio
from prompts import (
    MAX_VALIDATION_ERROR_TRY,
    SUMMARY_ROLE,
    SUMMARY_VALIDATION_RESOLVE_ROLE,
)
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
    top_p: float = 0.8
    frequency_penalty: float = 1.0
    presence_penalty: float = 1.5


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
    role: str = (
        f"{SUMMARY_ROLE} follow given schema: {SummaryOutputSchema.model_json_schema()}"
    )
    validation_role: str = f"{SUMMARY_VALIDATION_RESOLVE_ROLE} Schema :{SummaryOutputSchema.model_json_schema()}"
    model: str = "llama-3.1-8b-instant"
    temperature: float = 0.4
    stream: bool = False
    repetition_penalty: float = 1.5
    max_tokens: int = 6000

    def get_messages(
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

    def validation_messages(self, input_text: str) -> List[MessageSchema]:
        return [
            MessageSchema(role="system", content=self.validation_role),
            MessageSchema(
                role="user",
                content=input_text,
            ),
        ]

    def get(self, messages: List[MessageSchema]) -> Tuple[int, str]:
        payload = SummaryPayloadSchema(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            stream=self.stream,
        ).model_dump(by_alias=True)

        headers = HeadersSchema.create(api_key=self.api_key).model_dump(by_alias=True)
        response = requests.post(url=self.url, headers=headers, json=payload)
        code = response.status_code
        if code == 200:
            response_data = response.json()
            assistant_message = response_data["choices"][0]["message"]["content"]
            logger.info(
                f"200 : Input_Tokens={response_data['usage']['prompt_tokens']} | Output_Tokens={response_data['usage']['completion_tokens']}  | Time={response_data['usage']['total_time']}"
            )
            return code, assistant_message
        else:
            try:
                if response.json()["error"]["code"] == "json_validate_failed":
                    return 422, response.json()["error"]["failed_generation"]
            except:
                logger.warning(f"Error: {response.json()}")
                return code, "ERROR_API_CALL"

        return code, "ERROR_API_CALL"

    def validate_json(
        self, raw_data: str, schema: Type[SummaryResponseSchema]
    ) -> Union[SummaryResponseSchema, bool]:
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
            return False


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
            message = self.summary.get_messages(
                content=content,
                previous_summary=past_context.summary,
                characters=past_context.characters,
                places=past_context.places,
            )
            status_code, response = self.summary.get(messages=message)

            if status_code == 200:
                validated_response = self.summary.validate_json(
                    response, SummaryResponseSchema
                )

                if validated_response:
                    logger.trace(f"Chunk_{id=} Done")
                    self.summary_pool.append(
                        SummaryOutputSchema(
                            **(validated_response.model_dump(by_alias=True)), id=id
                        )
                    )
                    continue
                else:
                    output = self.handle_validation_error(response)
                    if output:
                        past_context = output
            elif status_code == 422:
                output = self.handle_validation_error(response)
                if output:
                    past_context = output

            self.summary_pool.append(past_context)
            logger.warning(f"{status_code=} error getting{id=}")

    def handle_validation_error(self, input_text):
        message = self.summary.validation_messages(input_text)
        for idx in range(MAX_VALIDATION_ERROR_TRY):
            status_code, response = self.summary.get(messages=message)
            if status_code == 200:
                validated_response = self.summary.validate_json(
                    response, SummaryOutputSchema
                )
                if validated_response:
                    logger.info("Validation error resolved")
                    return validated_response
            elif status_code == 422:
                message = self.summary.validation_messages(response)
            logger.warning(f"Validation Unresolved on try {idx + 1}")
        logger.error("COULDNT VALIDATE THE CHUNK, SKIPPING...")
        return None

    @property
    def get_summary_pool(self):
        return self.summary_pool


async def test() -> None:
    from reader import ebook

    api = os.environ.get("GROQ_API")
    if not api:
        raise Exception("API NOT SET IN .env, HF_API=None")

    book = ebook("./exp_book/stranger.pdf")
    chapter_content = book.get_chapters()[1:6]
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

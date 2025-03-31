from typing import Dict, List, Optional, Type, Tuple, Union
from pydantic import BaseModel, Field, ValidationError
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json

from reader_new import Book, Chapter, Chunk
from logger_module import logger
import requests
import asyncio
from prompts import (
    MAX_VALIDATION_ERROR_TRY,
    SUMMARY_ROLE,
    SUMMARY_VALIDATION_RESOLVE_ROLE,
    PROMPT_ROLE,
    PROMPT_VALIDATION_RESOLVE_ROLE,
)
from api_module import config
from json.decoder import JSONDecodeError
import os
from dotenv import load_dotenv

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


##SummaryScehma
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


##PromptSchema
class PromptPayloadSchema(BaseModel):
    model: str
    messages: List[MessageSchema]
    temperature: float
    stream: bool
    max_completion_tokens: int = 2048
    response_format: Dict[str, str] = {"type": "json_object"}
    top_p: float = 0.8
    frequency_penalty: float = 1.0
    presence_penalty: float = 1.5


class PromptResponseSchema(BaseModel):
    scene_title: str = ""
    prompt: str = ""


class PromptOutputSchema(PromptResponseSchema):
    id: Optional[str] = None

    def __eq__(self, value: str) -> bool:
        return self.id == value


class PromptContentSchema(BaseModel):
    input_text: str
    character_list: Dict[str, str]
    places_list: Dict[str, str]


##Requests


class LLM_API(ABC):
    @abstractmethod
    def get_messages(
        self, content: str, character: Dict[str, str], places: Dict[str, str]
    ) -> List[MessageSchema]:
        pass

    @abstractmethod
    def validation_messages(self, input_text: str) -> List[MessageSchema]:
        pass

    @abstractmethod
    def get(self, messages: List[MessageSchema]) -> Tuple[int, str]:
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
    role: str = f"{SUMMARY_ROLE} follow given schema: {SummaryResponseSchema.model_json_schema()}"
    validation_role: str = f"{SUMMARY_VALIDATION_RESOLVE_ROLE} Schema :{SummaryResponseSchema.model_json_schema()}"
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


@dataclass
class Prompt:
    api_key: str
    url: str = "https://api.groq.com/openai/v1/chat/completions"
    role: str = (
        f"{PROMPT_ROLE} follow given schema: {PromptResponseSchema.model_json_schema()}"
    )
    validation_role: str = f"{PROMPT_VALIDATION_RESOLVE_ROLE} Schema :{PromptResponseSchema.model_json_schema()}"
    model: str = "llama-3.1-8b-instant"
    temperature: float = 0.4
    stream: bool = False
    repetition_penalty: float = 1.5
    max_tokens: int = 6000

    def get_messages(
        self,
        input_text: str,
        characters: Dict[str, str],
        places: Dict[str, str],
    ) -> List[MessageSchema]:
        return [
            MessageSchema(role="system", content=self.role),
            MessageSchema(
                role="user",
                content=PromptContentSchema(
                    input_text=input_text,
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
        payload = PromptPayloadSchema(
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
        self, raw_data: str, schema: Type[PromptResponseSchema]
    ) -> Union[PromptResponseSchema, bool]:
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


@dataclass
class SummaryLoop:
    book: Book
    summary_handler: Summary
    summary_pool: List[SummaryOutputSchema] = Field(default_factory=list)
    init_chunk: Optional[Chunk] = None

    def __post_init__(self) -> None:
        self.init_chunk = Chunk(
            chunk_id="",
            chapter_id=0,
            chunk="",
            summary="This is The first chapeter There is No context",
            characters={},
            places={},
        )

    def run(self) -> None:
        """
        Assuming book comes in the form of ((id,title_chapter,chapter_content),..)
        """
        past_context = self.init_chunk
        for idx, chunk in enumerate(self.book.get_chunks()):
            message = self.summary_handler.get_messages(
                content=chunk.chunk,
                previous_summary=past_context.summary,
                characters=past_context.characters,
                places=past_context.places,
            )
            status_code, response = self.summary_handler.get(messages=message)

            if status_code == 200:
                validated_response = self.summary_handler.validate_json(
                    response, SummaryResponseSchema
                )

                if validated_response:
                    logger.trace(f"Chunk_{chunk.chunk_id=} Done")
                    chunk.set_sum(
                        summary=validated_response.summary,
                        characters=validated_response.characters,
                        places=validated_response.places,
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
            past_context = chunk
            logger.warning(f"{status_code=} error getting{id=}")

    def handle_validation_error(self, input_text):
        message = self.summary_handler.validation_messages(input_text)
        for idx in range(MAX_VALIDATION_ERROR_TRY):
            status_code, response = self.summary_handler.get(messages=message)
            if status_code == 200:
                validated_response = self.summary_handler.validate_json(
                    response, SummaryOutputSchema
                )
                if validated_response:
                    logger.info("Validation error resolved")
                    return validated_response
            elif status_code == 422:
                message = self.summary_handler.validation_messages(response)
            logger.warning(f"Validation Unresolved on try {idx + 1}")
        logger.error("COULDNT VALIDATE THE CHUNK, SKIPPING...")
        return None

    @property
    def get_book(self):
        return self.book


class PromptLoop(BaseModel):
    book: Book
    content: List[Tuple[str, str]]
    prompt: Prompt
    prompt_pool: List[PromptOutputSchema] = Field(default_factory=list)
    chunked_content: List[Tuple[str, str, str]] = Field(default_factory=list)

    def run(self) -> None:
        """
        Assuming book comes in the form of ((id,title_chapter,chapter_content),..)
        """
        for (id, title, content), sum in zip(self.chunked_content, self.summary_pool):
            prompt_out = PromptOutputSchema()
            message = self.prompt.get_messages(
                input_text=content, characters=sum.characters, places=sum.places
            )

            status_code, response = self.prompt.get(messages=message)

            if status_code == 200:
                validated_response = self.summary.validate_json(
                    response, PromptResponseSchema
                )

                if validated_response:
                    logger.trace(f"Chunk_{id=} Done")
                    self.prompt_pool.append(
                        PromptOutputSchema(
                            **(validated_response.model_dump(by_alias=True)), id=id
                        )
                    )
                    continue
                else:
                    output = self.handle_validation_error(response)
                    if output:
                        prompt_out = output
            elif status_code == 422:
                output = self.handle_validation_error(response)
                if output:
                    prompt_out = output

            self.prompt_pool.append(prompt_out)
            logger.warning(f"{status_code=} error getting{id=}")

    def handle_validation_error(self, input_text):
        message = self.prompt.validation_messages(input_text)
        for idx in range(MAX_VALIDATION_ERROR_TRY):
            status_code, response = self.prompt.get(messages=message)
            if status_code == 200:
                validated_response = self.prompt.validate_json(
                    response, PromptResponseSchema
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
    def get_prompt_pool(self):
        return self.prompt_pool


def test() -> None:
    from reader_new import Book

    api = os.environ.get("GROQ_API")
    if not api:
        raise Exception("API NOT SET IN .env, HF_API=None")

    book = Book("./test_books/PP.epub")
    sum = Summary(
        api_key=api,
    )

    looper = SummaryLoop(book=book, summary_handler=sum)

    looper.run()
    for i in book.get_chunks():
        if not i.places or not i.characters:
            continue
        print("-" * 50)
        print(f"Chapter:{i.chunk_id}")
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
    test()

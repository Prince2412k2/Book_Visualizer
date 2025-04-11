# TODO: Implement saving and caching also merge audio genration

import threading
import asyncio
from typing import Any, Dict, List, Optional, Type, Tuple, Union
from pydantic import BaseModel, Field, ValidationError
from dataclasses import dataclass
import json
import uuid

from reader_new import Book, Chunk
from logger_module import logger
import requests
import time
from prompts import (
    MAX_VALIDATION_ERROR_TRY,
    SUMMARY_ROLE,
    SUMMARY_VALIDATION_RESOLVE_ROLE,
    PROMPT_ROLE,
    PROMPT_VALIDATION_RESOLVE_ROLE,
    STYLE_TAG,
)
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


class PromptContentSchema(BaseModel):
    input_text: str
    character_list: Dict[str, str]
    places_list: Dict[str, str]


##Image Schemas


class Lora(BaseModel):
    model: str = "civitai:695825@778670"
    weight: float = 1


class ImageRequestSchema(BaseModel):
    positivePrompt: str
    # negativePrompt: str = ""  # IMAGE_NEGATIVE_PROMPT
    model: str = "runware:101@1"
    CFGScale: float = 3.5
    height: int = 512
    width: int = 512
    taskType: str = "imageInference"
    taskUUID: str = Field(default_factory=lambda: str(uuid.uuid4()))
    outputType: str = "URL"  # or "base64Data"
    outputFormat: str = "WEBP"
    checkNSFW: bool = True
    scheduler: str = "FlowMatchEulerDiscreteScheduler"
    includeCost: bool = True
    lora: List[Lora] = Field(default_factory=lambda: [Lora()])
    numberResults: int = 1
    steps: int = 30


class ImageItem(BaseModel):
    taskType: str
    imageUUID: str
    taskUUID: str
    cost: float
    seed: int
    imageURL: str
    # imageBase64Data: str
    NSFWContent: bool


class ImageResponseSchema(BaseModel):
    data: List[ImageItem]


# SUMMARY###############################################################################################################################################################################
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

    def __post_init__(self):
        self.headers = HeadersSchema.create(api_key=self.api_key).model_dump(
            by_alias=True
        )
        self.session = requests.Session()

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

    def get(
        self,
        messages: List[MessageSchema],
        max_retries=3,
    ) -> Tuple[int, str]:
        payload = SummaryPayloadSchema(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            stream=self.stream,
        ).model_dump(by_alias=True)

        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.post(
                    url=self.url, headers=self.headers, json=payload, timeout=10
                )

                code = response.status_code
                if code == 200:
                    response_data = response.json()
                    assistant_message = response_data["choices"][0]["message"][
                        "content"
                    ]
                    logger.info(
                        f"[Summary] 200 : Input_Tokens={response_data['usage']['prompt_tokens']} | Output_Tokens={response_data['usage']['completion_tokens']}  | Time={response_data['usage']['total_time']}"
                    )
                    return code, assistant_message

                elif code in [500, 502, 503, 504]:  # Retry for server errors
                    logger.warning(
                        f"[Summary] Server error ({code}), retrying {attempt}/{max_retries}..."
                    )

                else:
                    try:
                        if (
                            response.json().get("error", {}).get("code")
                            == "json_validate_failed"
                        ):
                            return 422, response.json()["error"]["failed_generation"]
                    except Exception as e:
                        logger.warning(f"[Summary] Error parsing API response: {e}")
                    return code, "ERROR_API_CALL"

            except (
                requests.ConnectionError,
                requests.Timeout,
                requests.exceptions.RequestException,
            ) as e:
                logger.warning(
                    f"[Summary] Connection error: {e}, retrying {attempt}/{max_retries}..."
                )

            time.sleep(2**attempt)  # Exponential backoff: 2s, 4s, 8s

        return 500, "ERROR_MAX_RETRIES"

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
            logger.warning("[Summary] ValidationError")
            return False


@dataclass
class SummaryLoop:
    book: Book
    summary_handler: Summary
    init_chunk: Optional[Chunk] = None

    def __post_init__(self) -> None:
        self.init_chunk = Chunk(
            path="./uploaded_books/Temp",
            chapter_id="0",
            chunk="",
            summary="This is The first chapeter There is No context",
            characters={},
            places={},
        )

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        """
        Assuming book comes in the form of ((id,title_chapter,chapter_content),..)
        """
        past_context = self.init_chunk
        assert past_context
        for chunk in self.book.get_chunks():
            if chunk.summary:
                continue
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

                if isinstance(validated_response, SummaryResponseSchema):
                    logger.trace(f"[Summary] : Chunk_{chunk.chunk_id=} Done")
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
                else:
                    chunk.set_sum(
                        summary=past_context.summary,
                        characters=past_context.characters,
                        places=past_context.places,
                    )
            else:
                chunk.set_sum(
                    summary=past_context.summary,
                    characters=past_context.characters,
                    places=past_context.places,
                )

            past_context = chunk
            logger.warning(f"[Summary] : {status_code=} error getting{id=}")
        loop.close()

    def handle_validation_error(self, input_text):
        message = self.summary_handler.validation_messages(input_text)
        for idx in range(MAX_VALIDATION_ERROR_TRY):
            status_code, response = self.summary_handler.get(messages=message)
            if status_code == 200:
                validated_response = self.summary_handler.validate_json(
                    response, SummaryOutputSchema
                )
                if validated_response:
                    logger.info("[Summary] : Validation error resolved")
                    return validated_response
            elif status_code == 422:
                message = self.summary_handler.validation_messages(response)
            logger.warning(f"[Summary] : Validation Unresolved on try {idx + 1}")
        logger.error("[Summary] : COULDNT VALIDATE THE CHUNK, SKIPPING...")
        return None

    @property
    def get_book(self):
        return self.book


# Prompt ###############################################################################################################################################################################
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

    def __post_init__(self):
        self.headers = HeadersSchema.create(api_key=self.api_key).model_dump(
            by_alias=True
        )
        self.session = requests.Session()

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

    def get(
        self,
        messages: List[MessageSchema],
        max_retries=3,
    ) -> Tuple[int, str]:
        payload = PromptPayloadSchema(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            stream=self.stream,
        ).model_dump(by_alias=True)

        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.post(
                    url=self.url, headers=self.headers, json=payload, timeout=10
                )

                code = response.status_code
                if code == 200:
                    response_data = response.json()
                    assistant_message = response_data["choices"][0]["message"][
                        "content"
                    ]
                    logger.info(
                        f"[Prompt] : 200 : Input_Tokens={response_data['usage']['prompt_tokens']} | Output_Tokens={response_data['usage']['completion_tokens']}  | Time={response_data['usage']['total_time']}"
                    )
                    return code, assistant_message

                elif code in [500, 502, 503, 504]:  # Retry for server errors
                    logger.warning(
                        f"[Prompt] : Server error ({code}), retrying {attempt}/{max_retries}..."
                    )

                else:
                    try:
                        if (
                            response.json().get("error", {}).get("code")
                            == "json_validate_failed"
                        ):
                            return 422, response.json()["error"]["failed_generation"]
                    except Exception as e:
                        logger.warning(f"[Prompt] : Error parsing API response: {e}")
                return code, "ERROR_API_CALL"

            except (
                requests.ConnectionError,
                requests.Timeout,
                requests.exceptions.RequestException,
            ) as e:
                logger.warning(
                    f"[Prompt] : Connection error: {e}, retrying {attempt}/{max_retries}..."
                )

            time.sleep(2**attempt)  # Exponential backoff: 2s, 4s, 8s

        return 500, "ERROR_MAX_RETRIES"

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
            logger.warning("[Prompt] : ValidationError")
            return False


class PromptLoop(BaseModel):
    book: Book
    prompt_handler: Prompt

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        """
        Assuming book comes in the form of ((id,title_chapter,chapter_content),..)
        """
        is_done = False
        while not is_done:
            for idx, chunk in enumerate(self.book.get_chunks()):
                if chunk.prompt:
                    continue

                message = self.prompt_handler.get_messages(
                    input_text=chunk.chunk,
                    characters=chunk.characters,
                    places=chunk.places,
                )

                status_code, response = self.prompt_handler.get(messages=message)

                if status_code == 200:
                    validated_response = self.prompt_handler.validate_json(
                        response, PromptResponseSchema
                    )

                    if isinstance(validated_response, PromptResponseSchema):
                        logger.trace(f"[Prompt] : Chunk_{chunk.chunk_id=} Done")
                        chunk.set_prompt(
                            scene_title=validated_response.scene_title,
                            prompt=validated_response.prompt,
                        )
                        continue

                logger.warning(f"[Prompt] : {status_code=} error getting{idx=}")
            is_done = self.book.is_prompt_done()
        logger.info("[Prompt] : Prompts Done for ALL Chunks")
        loop.close()

    def handle_validation_error(self, input_text):
        message = self.prompt_handler.validation_messages(input_text)
        for idx in range(MAX_VALIDATION_ERROR_TRY):
            status_code, response = self.prompt_handler.get(messages=message)
            if status_code == 200:
                validated_response = self.prompt_handler.validate_json(
                    response, PromptOutputSchema
                )
                if validated_response:
                    logger.info("[Summary] : Validation error resolved")
                    return validated_response
            elif status_code == 422:
                message = self.prompt_handler.validation_messages(response)
            logger.warning(f"[Prompt] : Validation Unresolved on try {idx + 1}")
        logger.error("[Prompts] : COULDNT VALIDATE THE CHUNK, SKIPPING...")
        return None

    @property
    def get_book(self):
        return self.book


# Image###############################################################################################################################################################################
@dataclass
class Image:
    api_key: str
    url: str = "https://api.runware.ai/v1"
    headers: Dict[str, Any] = Field(default_factory=dict)

    def __post_init__(self):
        self.headers = HeadersSchema.create(api_key=self.api_key).model_dump(
            by_alias=True
        )
        self.session = requests.Session()

    def get(self, payload, max_retries=3) -> Tuple[int, Optional[ImageResponseSchema]]:
        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.post(
                    url=self.url, headers=self.headers, json=[payload], timeout=30
                )
                logger.debug(f"try: {attempt}")
                code = response.status_code
                logger.debug(f"status_code : {code}")
                logger.debug(response.text)
                if code == 200:
                    response_data = response.json()
                    response_model = ImageResponseSchema.model_validate(response_data)
                    logger.info(
                        f"[Image] : 200 : | task={response_model.data[0].taskUUID} | cost = {response_model.data[0].cost}$ | NSFW = {response_model.data[0].NSFWContent}"
                    )
                    return code, response_model

                elif code in [500, 502, 503, 504]:  # Retry for server errors
                    logger.warning(
                        f"[Image] : Server error ({code}), retrying {attempt}/{max_retries}..."
                    )

            except (
                requests.ConnectionError,
                requests.Timeout,
                requests.exceptions.RequestException,
            ) as e:
                logger.warning(
                    f"[Image] : Connection error: {e}, retrying {attempt}/{max_retries}..."
                )

            time.sleep(2**attempt)  # Exponential backoff: 2s, 4s, 8s

        return 500, None


class ImageLoop(BaseModel):
    book: Book
    image_handler: Image

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        """
        Assuming book comes in the form of ((id,title_chapter,chapter_content),..)
        """
        is_prompt_done = False
        response: Optional[ImageResponseSchema]
        while not is_prompt_done:
            for idx, chunk in enumerate(self.book.get_chunks()):
                if chunk.image_url or not chunk.prompt:
                    continue
                payload = ImageRequestSchema(positivePrompt=STYLE_TAG + chunk.prompt)

                status_code, response = self.image_handler.get(
                    payload=payload.model_dump(mode="json")
                )

                if status_code == 200:
                    if response:
                        chunk.set_img(
                            url=response.data[0].imageURL,
                            task_id=response.data[0].taskType,
                        )
                        continue

                logger.warning(f"[Image] : {status_code=} error getting{idx=}")

            is_prompt_done = self.book.is_img_done()
        while not self.book.is_done():
            time.sleep(1)
        logger.info("[Image] : Prompts Done for ALL Chunks")
        loop.close()


def process_book(book: Book):
    groq_api = os.environ.get("GROQ_API")
    img_api = os.environ.get("IMAGE_API")
    if not groq_api:
        raise Exception("GROQ_API NOT SET IN .env")
    if not img_api:
        raise Exception("IMAGE_API NOT SET IN .env")

    book_state = book.book_state
    assert book_state
    if book_state.is_done:
        return True
    sum = Summary(api_key=groq_api)
    prompt = Prompt(api_key=groq_api)
    image = Image(api_key=img_api)

    looper_sum = SummaryLoop(book=book, summary_handler=sum)
    looper_prompt = PromptLoop(book=book, prompt_handler=prompt)
    looper_img = ImageLoop(book=book, image_handler=image)

    thread_img = threading.Thread(target=looper_img.run)
    thread_prompt = threading.Thread(target=looper_prompt.run)
    thread_sum = threading.Thread(target=looper_sum.run)

    thread_img.start()
    thread_prompt.start()
    thread_sum.start()

    thread_img.join()
    thread_prompt.join()
    thread_sum.join()


def test() -> None:
    from reader_new import Book

    book: Book = Book(
        "./test_books/AF.epub", user_id="b5bfc116-dd81-475a-8425-537a50621706"
    )
    process_book(book)
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

        print("prompt")
        print(f"{i.scene_title} : {i.prompt} ")
        print("\n\n")

        print("IMAGE")
        print(f"{i.scene_title} : {i.image_url} ")
        print("\n\n")


if __name__ == "__main__":
    test()

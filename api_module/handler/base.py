import api_module
from api_module.schemas.base import PromptInputSchema, SummaryInputSchema, Task
from api_module.schemas.groq_schema import GroqPayloadSchema, GroqResponseSchema
from api_module.utils import clean_json
from pydantic import BaseModel, ValidationError
import json
from logger_module import logger
from api_module.schemas import (
    HeaderSchema,
    PayloadSchema,
    ResponseSchema,
    MessageSchema,
    ValidationErrorSchema,
)
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, Union, Tuple, List
from dataclasses import dataclass
from config import API_KEY, MAX_VALIDATION_ERROR_TRY
from reader_new import Book
import requests

# TODO: ADD GROQ Handler


@dataclass
class LanguageAPICall:
    url: str
    headers: Dict[str, str]
    output_schema: ResponseSchema

    def post(self, payload: BaseModel) -> Tuple[int, dict]:
        """Handling Groq validation error as code 422"""
        response = requests.post(url=self.url, headers=self.headers, json=payload)

        if response.ok:
            try:
                json_response = response.json()  # ✅ Ensure it's JSON
                if not isinstance(json_response, dict):  # ✅ Ensure it's a dict
                    raise ValueError(
                        "[call_api] Expected a JSON object, but got a different type."
                    )
            except requests.exceptions.JSONDecodeError as e:
                raise ValueError("[call_api] Response is not valid JSON.") from e

            logger.info(f"[call_api] Code : {response.status_code}")
            return response.status_code, json_response

            # try:
            #    error_response=ValidationErrorSchema(**response.json())
            #    if error_response.error.code== "json_validate_failed":
            #        return 422, error_response.error.failed_generation
            # except:
            #    logger.warning(f"Error: {response.json()}")
        logger.info(f"[call_api] Code : {response.status_code}")
        return response.status_code, {"Error": response.status_code}

    def validate_structure(
        self, data: str, schema: BaseModel
    ) -> Union[bool, BaseModel]:
        """Validates JSON data against a provided Pydantic schema.
        :param data: JSON string to be validated.
        :param schema: A Pydantic model class to validate against.
        :return: A tuple where the first element is a boolean indicating if there was an error,
                 and the second element is either the validated data or a list of error details.
        """
        try:
            parsed_data = json.loads(data)
            validated_data = schema.model_validate(parsed_data)
            return validated_data
        except (ValidationError, json.JSONDecodeError):
            logger.warning("ValidationError")
            return False

    """
    def handle_validation_error(self, task: BaseModel, input_text: str):
        message = self.validation_messages(input_text)

        for idx in range(MAX_VALIDATION_ERROR_TRY):
            status_code, response = llm_call(messages=message)
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
"""


@dataclass
class IHandlerLLM(ABC):
    task: Task
    api: str
    url: str
    payload: BaseModel
    headers: HeaderSchema

    response_model: BaseModel
    validation_error_model: Optional[BaseModel] = None

    @abstractmethod
    def __post_init__(self):
        pass

    @abstractmethod
    def feed_input(
        self, text: Union[SummaryInputSchema, PromptInputSchema, str]
    ) -> None:
        pass

    @abstractmethod
    def get_valid_msg(self, role: str, text: str) -> List[MessageSchema]:
        pass

    @abstractmethod
    def set_payload(self, text: str) -> Tuple[str, dict, dict]:
        pass

    @abstractmethod
    def call(self) -> Tuple[int, str]:
        pass

    @abstractmethod
    def validate_error(self, role: str, input_text: str) -> BaseModel:
        pass


@dataclass
class GroqHandler(IHandlerLLM):
    payload: GroqPayloadSchema
    response_model: GroqResponseSchema
    url: str = "https://api.groq.com/openai/v1/chat/completions"
    api: str = API_KEY

    def __post_init__(self):
        self.headers = HeaderSchema().create(self.api)
        self.llm_api = LanguageAPICall(
            url=self.url, headers=self.headers, output_schema=self.response_model
        )

    def feed_input(
        self, text: Union[SummaryInputSchema, PromptInputSchema, str]
    ) -> None:
        if isinstance(text, str):
            prompt = text
        else:
            prompt = text.model_dump(by_alias=True)
        self.payload.set_input(prompt=prompt)

    def get_valid_msg(self, role: str, text: str) -> List[MessageSchema]:
        return [
            MessageSchema(role="system", content=role),
            MessageSchema(role="user", content=text),
        ]

    def call(self) -> Tuple[int, str]:
        """
        200 is sucessful,
        422(custom) is validation error
        """
        status_code, response = self.llm_api.post(self.payload)
        output = "ERROR"
        if status_code == 200:
            output = GroqResponseSchema.validate_json(response).choices.message.content

        elif status_code == 400:
            try:
                output = ValidationErrorSchema.validate_json(
                    response
                ).error.failed_generation
                status_code = 422
            except Exception as e:
                pass
        return status_code, output

'''
    def solve_validate_error(
        self, role: str, input_text: str, schema: BaseModel
    ) -> BaseModel:
        msg = self.get_valid_msg(role=role, text=input_text)

        for idx in range(MAX_VALIDATION_ERROR_TRY):
            status_code, response = self.call()
            if status_code == 200:
                validated_response = self.llm_api.validate_structure(
                    data=response, schema=schema
                )
                if validated_response:
                    logger.info("Validation error resolved")
                    return validated_response
            elif status_code == 422:
                message = self.summary.validation_messages(response)
            logger.warning(f"Validation Unresolved on try {idx + 1}")
        logger.error("COULDNT VALIDATE THE CHUNK, SKIPPING...")
        return None
'''
@dataclass
class Summary
    book:Book
    handler:Type[IHandlerLLM]
    
    def loop(self):
        for chunk in self.book.get_chapters

def main() -> None:
    handler = HFHandler(api_key="sac", url="csvd", model="guyb")
    ## OR
    handler = HFHandler(api_key="sac", url="cvs")
    handler.set_model(model_name="csb")
    handler.set_max_token(tokens=2008)
    handler.add_role("ROLE")
    handler.set_input("INPUT")
    url, headers, payload = handler.get()
    print(f"{url=}", end="\n\n")
    print(f"{headers=}", end="\n\n")
    print(f"{payload=}", end="\n\n")


if __name__ == "__main__":
    main()

from typing import Dict, List, Optional, Union
from typing_extensions import Tuple
from pydantic import BaseModel, Field
from logger_module import logger
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
from prompts import summary_role
from utils import TokenCounter


## schema
class HeadersSchema(BaseModel):
    authorization: str = Field(..., alias="Authorization")
    content_type: str = Field(default="application/json", alias="Content-Type")

    @classmethod
    def create(cls, api_key: str) -> "HeadersSchema":
        return cls(Authorization=f"Bearer {api_key}")

    class Config:
        populate_by_name = True


class GrammarSchema(BaseModel):
    type_: str = Field(alias="type", default="json")
    value: dict = Field(default_factory=dict)


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
    max_tokens: int
    parameters: ParameterSchema


class SummaryResponseSchema(BaseModel):
    summary: str
    characters: Dict[str, str]
    places: Dict[str, str]


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


@dataclass
class Summary:
    api_key: str
    url: str = "https://api-inference.huggingface.co/models/mistralai/Mistral-Nemo-Instruct-2407/v1/chat/completions"
    role: str = summary_role
    model: str = "mistralai/Mistral-Nemo-Instruct-2407"
    temperature: float = 0.5
    stream: bool = False
    max_tokens: int = 32000
    repetition_penalty: float = 1.3

    async def messages(
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

    async def get(self, messages: List[MessageSchema]) -> str:
        payload = SummaryPayloadSchema(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            stream=self.stream,
            max_tokens=self.max_tokens,
            parameters=ParameterSchema(
                repetition_penalty=self.repetition_penalty,
                grammar=GrammarSchema(value=SummaryResponseSchema.model_json_schema()),
            ),
        ).model_json_schema()

        headers = HeadersSchema(Authorization=self.api_key).model_dump_json()

        return json.dumps(payload.model_dump())


class SumamaryLoop(BaseModel):
    init_messages: MessageSchema
    summary_pool: Tuple[SummaryResponseSchema] = Field(init=False)

    def __post_init__(self) -> "SumamaryLoop":
        self.summary_pool = (
            SummaryResponseSchema(
                summary="This is The first chapeter There is No context",
                places={},
                characters={},
            ),
        )
        return self

    def run(self, book_content: Tuple[Tuple[str]]) -> Bool:
        """
        Assuming book comes in the form of ((title_chapter,chapter_content),..)
        """

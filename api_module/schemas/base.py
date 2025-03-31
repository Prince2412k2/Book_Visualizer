from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from abc import ABC


from logger_module import logger
from prompts import SUMMARY_ROLE, PROMPT_ROLE
from api_module.config import MODEL_NAME, MAXTOKENS, TEMPERATURE


class Task(Enum):
    SUMMARY = "SUM"
    PROMPT = "PROMPT"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"


class Handler(Enum):
    HF = "HF"
    OLLAMA = "OLLAMA"
    GROQ = "GROQ"


##BaseShemas
class MessageSchema(BaseModel):
    """Define roles for instruct model"""

    role: str
    content: Union[str, dict]


class HeaderSchema(BaseModel):
    Authorization: str = Field(default="", alias="Authorization")
    content_type: str = Field(default="application/json", alias="Content-Type")

    @classmethod
    def create(cls, api_key: str) -> "HeaderSchema":
        return cls(Authorization=f"Bearer {api_key}")

    class Config:
        populate_by_name = True


class PayloadSchema(BaseModel):
    """Basic payload for a Instruct Model"""

    model: str = MODEL_NAME
    messages: List[MessageSchema] = Field(default=[])
    temperature: float = TEMPERATURE
    stream: bool = Field(init=False, default=False)
    # max_tokens: Optional[int] = MAXTOKENS

    def set_model(self, model_name: str):
        self.model = model_name
        return self

    def set_temperature(self, temperature: float):
        self.temperature = temperature
        return self

    def set_max_token(self, tokens: int):
        self.max_tokens = tokens
        return self

    def set_role(self, content: str):
        if self.messages:
            self.messages[0] = MessageSchema(role="system", content=content)
        else:
            self.messages.append(MessageSchema(role="system", content=content))
        return self

    def set_input(self, prompt: str):
        if len(self.messages) < 2:
            self.messages.append(MessageSchema(role="user", content=prompt))
        else:
            self.messages[1].content = prompt
        return self


class UsageSchema(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ResponseSchema(BaseModel, ABC):
    """
    format of Response LLM-API gives
    Depeneds on API
    """

    ...


##BaseSummarySchema
class SummaryOutputSchema(BaseModel):
    summary: str
    characters: Dict[str, str]
    places: Dict[str, str]


class SummaryInputSchema(BaseModel):
    """Format of input LLM expects"""

    past_context: str
    current_chapter: str
    character_list: Dict[str, str]
    places_list: Dict[str, str]


##BasePromptSchema
class PromptOutputSchema(BaseModel): ...


class PromptInputSchema(BaseModel): ...


class PromptResponseSchema(BaseModel, ABC):
    """
    format of Response LLM-API gives
    (Depeneds on the API)
    """

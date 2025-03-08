from enum import Enum
from typing import Dict, List, Optional, Type, Union
from pydantic import BaseModel, Field
from abc import ABC

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logger_module import logger

# from utils import Chunker, Tokenizer
from prompts import SUMMARY_ROLE, PROMPT_ROLE


class Task(Enum):
    SUMMARY = "SUM"
    PROMPT = "PROMPT"


##BaseShemas
class MessageSchema(BaseModel):
    """Define roles for instruct model"""

    role: str
    content: Union[str, dict]


class PayloadSchema(BaseModel):
    """Basic payload for a Instruct Model"""

    model: str = ""
    messages: List[Type[BaseModel]] = Field(default=[])
    temperature: float = 0.5
    stream: bool = Field(init=False, default=False)
    max_tokens: int = 32000

    def set_model(self, model_name: str):
        self.model = model_name
        return self

    def set_temperature(self, temperature: float):
        self.temperature = temperature
        return self

    def set_max_token(self, tokens: int):
        self.max_tokens = tokens
        return self

    def add_message(self, role: str, content: str):
        self.messages.append(MessageSchema(role=role, content=content))
        return self


###BaseSummarySchemas
class SummaryOutputSchema(BaseModel):
    """Format of output we want from LLM"""

    summary: str
    characters: Dict[str, str]
    places: Dict[str, str]


class SummaryInputSchema(BaseModel):
    """Format of input LLM expects"""

    past_context: str
    current_chapter: str
    character_list: Dict[str, str]
    places_list: Dict[str, str]


class SummaryResponseSchema(BaseModel, ABC):
    """format of Response LLM-API gives"""

    ...


###BasePromptSchemas
class PromptOutputSchema(BaseModel): ...


class PromptInputSchema(BaseModel): ...


class PromptResponseSchema(BaseModel, ABC): ...


##HuggingFaceHandlerSchema
class HFHeaderSchema(BaseModel):
    authorization: str = Field(..., alias="Authorization")
    content_type: str = Field(default="application/json", alias="Content-Type")

    @classmethod
    def create(cls, api_key: str) -> "HFHeaderSchema":
        return cls(Authorization=f"Bearer {api_key}")

    class Config:
        populate_by_name = True


class GrammarSchema(BaseModel):
    """HuggingFace grammar schema for valid json output"""

    type_: str = Field(alias="type", default="json")
    value: dict = SummaryOutputSchema.model_json_schema()

    class Config:
        populate_by_name = True


class ParameterSchema(BaseModel):
    """HuggingFace parameter schema for valid json output"""

    repetition_penalty: Optional[float] = 1.3
    grammar: GrammarSchema


class HFPayloadSchema(PayloadSchema):
    """HuggingFace Payload schema for valid summary|prompt output"""

    task: Task = Task.SUMMARY
    parameter: ParameterSchema = ParameterSchema(grammar=GrammarSchema())

    def set_task(self, task: Task):
        self.task = task
        if self.task == Task.SUMMARY:
            self.parameter = ParameterSchema(
                grammar=GrammarSchema(value=SummaryOutputSchema.model_json_schema())
            )
            self.add_message(role="system", content=SUMMARY_ROLE)
            return self

        elif self.task.value == "PROMPT":
            self.parameter = ParameterSchema(
                grammar=GrammarSchema(value=PromptOutputSchema.model_json_schema())
            )
            self.add_message(role="system", content=PROMPT_ROLE)
            return self

        else:
            logger.error(
                f"[HFPayloadSchema] Unkown Task:{task}, Supported : [SUMMARY | PROMPT]"
            )


##OllamaHandleSchemas
class OllamaSummaryPayloadSchema(PayloadSchema):
    """Ollama payload schema for ollama API handler"""

    format: dict = SummaryOutputSchema.model_json_schema()


class OllamaSummaryResponseSchema(SummaryResponseSchema):
    """Ollama API Response Format"""

    created_at: str
    message: MessageSchema
    total_duration: int

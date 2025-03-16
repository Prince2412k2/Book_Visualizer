from typing import List, Optional
from pydantic import BaseModel, Field

from .base import (
    MessageSchema,
    PayloadSchema,
    SummaryOutputSchema,
    PromptOutputSchema,
    Task,
    ResponseSchema,
    UsageSchema,
)

from logger_module import logger
from prompts import SUMMARY_ROLE, PROMPT_ROLE


##Defines PAYLOAD for HuggingFace API
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

    task: Task = Field(default=Task.SUMMARY, exclude=True)
    parameters: ParameterSchema = ParameterSchema(grammar=GrammarSchema())

    def set_task(self, task: Task):
        self.task = task
        if self.task == Task.SUMMARY:
            self.parameter = ParameterSchema(
                grammar=GrammarSchema(value=SummaryOutputSchema.model_json_schema())
            )
            self.add_role(content=SUMMARY_ROLE)
            return self

        elif self.task.value == "PROMPT":
            self.parameter = ParameterSchema(
                grammar=GrammarSchema(value=PromptOutputSchema.model_json_schema())
            )
            self.add_role(content=PROMPT_ROLE)
            return self

        else:
            logger.error(
                f"[HFPayloadSchema] Unkown Task:{task}, Supported : [SUMMARY | PROMPT]"
            )


##Defines RESPONSE of Huggingface api
class HFChoiceSchema(BaseModel):
    message: MessageSchema


class HFResponseSchema(ResponseSchema):
    choices: List[HFChoiceSchema]
    usage: UsageSchema


def main() -> None:
    raw_response = {
        "id": "chatcmpl-123456789",
        "object": "chat.completion",
        "created": 1710000000,
        "model": "gpt-4-turbo",
        "system_fingerprint": "fp_123abc",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "logprobs": {
                    "content": [
                        {
                            "token": "Hello",
                            "logprob": -0.5,
                            "top_logprobs": [
                                {"token": "Hi", "logprob": -0.6},
                                {"token": "Hey", "logprob": -0.7},
                            ],
                        }
                    ]
                },
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I assist you today?",
                },
            }
        ],
        "usage": {"completion_tokens": 20, "prompt_tokens": 10, "total_tokens": 30},
    }

    payload = HFPayloadSchema(model="MODEL_NAME").add_role("ROLE")
    response = HFResponseSchema.model_validate(raw_response)
    print("payload")
    print(payload.model_dump_json(indent=2, by_alias=True))
    print("\n\n\nResponse")
    print(response)


if __name__ == "__main__":
    main()

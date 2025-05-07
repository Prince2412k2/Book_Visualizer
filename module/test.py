from prompts import SUMMARY_ROLE
from base_schemas import (
    PayloadSchema,
    SummaryOutputSchema,
    HeaderSchema,
)
import re
import json
import requests

test = """
The old grandfather clock in Evelyn’s study struck midnight as she traced the edges of the faded letter in her hands. The ink had smudged over the years, but the message was still clear:  

*"Meet me at the willow tree when the moon is full. I have something to tell you."*  

Her heart pounded. The letter had no name, no date—just those eleven words. And yet, she had found it tucked inside an old book… one that had belonged to her mother.  

Outside, the wind howled, shaking the branches of the towering willow in the backyard. Evelyn hesitated. The moon was full tonight.  

She grabbed her coat.  

Then, just as she reached for the doorknob—  

A knock echoed through the house.
        """

api = "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"


def clean_json(text):
    return re.sub(r"^```json\s*|\s*```$", "", text.strip(), flags=re.DOTALL)


from pydantic import BaseModel, Field


class JsonSchema(BaseModel):
    strict: bool = True
    schema_: dict = Field(
        alias="schema", default=SummaryOutputSchema.model_json_schema()
    )

    class Config:
        populate_by_name = True


class ResponseSchema(BaseModel):
    """HuggingFace grammar schema for valid json output"""

    type_: str = Field(alias="type", default="json_schema")
    json_schema: dict = JsonSchema().model_dump(by_alias=True)

    class Config:
        populate_by_name = True


class CustomPayloadSchema(PayloadSchema):
    response_format: dict
    structured_output: bool = True


resp_for = ResponseSchema().model_dump(by_alias=True)
headers = HeaderSchema(Authorization=api).create(api)
payload = CustomPayloadSchema(
    model="google/gemini-2.0-flash-lite-preview-02-05:free", response_format=resp_for
)
payload.add_message(role="system", content=f"{SUMMARY_ROLE}")
payload.set_input(test)
import time

start = time.time()
response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers=headers.model_dump(),
    json=payload.model_dump(),
)
end = time.time()

jsond = clean_json(response.json()["choices"][0]["message"]["content"])
print(jsond)
jsond = json.loads(jsond)
# print(jsond, end="\n\n\n")
output = SummaryOutputSchema.model_validate(jsond)
print(output.model_dump_json(indent=2))
# payload.model_dump_json())
print(end - start)

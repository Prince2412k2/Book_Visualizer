from abc import ABC, abstractmethod
import json
from pydantic import BaseModel, ValidationError, Field
from typing import Dict, Any, Optional, Self, Type
import requests


from logger_module import logger
from schemas import (
    HFPayloadSchema,
    HeaderSchema,
    SummaryOutputSchema,
    Task,
    GroqPayloadSchema,
    GroqResponseSchema,
)


##LLM Interface
class LLMInterface(ABC):
    @abstractmethod
    def call(self) -> Any:
        pass


##HuggingFaceHandler
class HFHandler(LLMInterface, HFPayloadSchema):
    api_key: str
    url: str

    def call(self) -> Optional[Any]:
        payload = self.model_dump()
        headers = HeaderSchema(Authorization=self.api_key)

        try:
            response = requests.post(
                url=self.url, json=payload, headers=headers.model_dump()
            )
            logger.info(f"[HFHandler] response_status : {response.status_code}")

            if not response.ok:
                logger.warning(
                    f"[HFHandler] Request Failed {response.status_code} : {response.text}"
                )
                return None
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                logger.warning("[HFHandler] Failed to parse JSON from Response")
                return None
        except Exception as e:
            logger.warning(f"[HFHandler] Post Request Error : {e}")


class GroqHandler(LLMInterface, GroqPayloadSchema):
    api_key: str
    url: str = "https://api.groq.com/openai/v1/chat/completions"
    headers: Optional[HeaderSchema] = None

    def __post_init__(self):
        self.headers = HeaderSchema.create(self.api_key)

    def get_payload(self):
        payload = self.model_dump_json(
            exclude={"api_key", "task", "url", "headers"}
        ).encode("utf-8")
        return payload

    def call(self):
        if not self.headers:
            logger.warning("[GroqHandler] Header Not defined")
            return None
        payload = self.model_dump_json(exclude={"api_key", "task", "url", "headers"})
        try:
            response = requests.post(
                url=self.url,
                data=payload.encode("utf-8"),
                headers=self.headers.model_dump(),
            )
            logger.info(f"[GroqHandler] response_status: {response.status_code}")
            if not response.ok:
                logger.warning(
                    f"[GroqHandler] Request Failed {response.status_code}: {response.text}"
                )
                return None
            try:
                json_response = response.json()
            except requests.exceptions.JSONDecodeError:
                logger.warning("[GroqHandler] Failed to parse JSON from Response")
                return None
            try:
                validated_response = GroqResponseSchema.model_validate(json_response)
                return validated_response
            except ValidationError as e:
                logger.warning(f"[GroqHandler] Pydantic validation failed: {e}")
                return None
        except Exception as e:
            logger.error(f"[GroqHandler] Post Request Error: {e}", exc_info=True)
            return None


class Loop(BaseModel):
    task_type: Task

    def __post_init__(self): ...


import time


def main():
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api = os.environ.get("GROQ_API")
    if not api:
        return None
    api = GroqHandler(api_key=api)
    prmpt = """
    The neon glow of Blackwood Diner flickered under the cold drizzle. Detective Elias Grant pushed open the glass door, the bell jingling as he stepped inside. The scent of burnt coffee and stale grease filled the air. At the corner booth, Mira Caldwell, a journalist with ink-stained fingers, waited with her notepad half-open.
    "They’re calling it the 'Vanishing Lights,'" she said, tapping her pen against the table. "Three disappearances in a week, all near Crescent Pier."
    Elias slid into the booth. "No bodies, no witnesses. Just their cars left behind, engines still running."
    Across town, in the dimly lit backroom of O'Hara's Pub, Daniel Rourke, a smuggler with too many debts, poured himself a drink. The whispers had reached him too. People vanishing without a trace. A storm was coming, and he had a bad feeling he was already in too deep.
    As the rain thickened, the streetlights outside Hollow Creek Motel flickered once—then went dark."""
    api.set_model("llama3-8b-8192")
    api.set_task(Task.SUMMARY)
    api.set_input(prompt=prmpt)
    print(api.get_payload())

    start = time.time()
    out = api.call()
    end = time.time()
    print("Raw API Response:", out)
    print("_" * 100)

    if out is not None:
        content_data = out.choices[0].message.content

        if isinstance(content_data, str):
            try:
                content_data = json.loads(content_data)
                # print(content_data)
            except json.JSONDecodeError as e:
                print("JSON Decode Error:", e)

        try:
            valid_out = SummaryOutputSchema.model_validate(content_data)
            print(valid_out.model_dump_json())
        except Exception as e:
            print("Validation failed:", e)
    else:
        print("out is none")
    logger.warning(f"{end - start}")


if __name__ == "__main__":
    main()

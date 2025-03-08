from abc import ABC, abstractmethod
from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum
import requests

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logger_module import logger
from base_schemas import HFPayloadSchema, MessageSchema, HFHeaderSchema, Task


##LLM Interface
class LLMInterface(ABC):
    @abstractmethod
    def call(self):
        pass


##HuggingFaceHandler
class HFHandler(LLMInterface, HFPayloadSchema):
    api_key: str
    url: str

    def call(self) -> Optional[Any]:
        payload = self.model_dump_json()
        headers = HFHeaderSchema(Authorization=self.api_key)

        try:
            response = requests.post(
                url=self.url, data=payload, headers=headers.model_dump()
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


def main():
    api = HFHandler(
        api_key="ascxs",
        url="xs",
    )
    api.set_model("ac").set_temperature(0.2).set_max_token(32000).set_task(Task.SUMMARY)
    print(api.model_dump_json())


if __name__ == "__main__":
    main()

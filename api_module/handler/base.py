from logger_module import logger
from api_module.schemas import HeaderSchema, HFPayloadSchema
from abc import ABC, abstractmethod
from typing import Any


class LLMInterface(ABC):
    @abstractmethod
    def get(self) -> Any:
        pass


class HFHandler(HFPayloadSchema):
    api_key: str
    url: str

    def get(self):
        if not self.api_key:
            logger.error("[HFHandler] Missing API key")
        if not self.url:
            logger.error("[HFHandler] Missing URL")
        if not self.model:
            logger.error("[HFHandler] Missing model")
        if len(self.messages) < 2:
            logger.error("[HFHandler] No messages provided")

        headers = HeaderSchema().create(api_key=self.api_key)
        payload = self.model_dump(by_alias=True)
        return (
            self.url,
            headers,
            payload,
        )

class GroqHandler(GroqHandler)


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

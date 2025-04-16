from google.cloud import texttospeech
import os
from dotenv import load_dotenv
from typing import Optional

from pydantic import BaseModel
from logger_module import logger

from reader_new import Book

load_dotenv()


class Audio(BaseModel):
    service_acc_path: str

    def __post_init__(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.service_acc_path
        self.client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="en-GB",  # Match the voice name
            name="en-GB-Wavenet-B",  # British English male voice
            ssml_gender=texttospeech.SsmlVoiceGender.MALE,
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

    def synthesize_speech(self, text: str, id: str) -> Optional[bytes]:
        input_text = texttospeech.SynthesisInput(text=text)

        try:
            response = self.client.synthesize_speech(
                input=input_text, voice=self.voice, audio_config=self.audio_config
            )
            logger.info(f"[Audio] Chunk:{id} is done")
            return response.audio_content

        except Exception as e:
            logger.warning(f"[Audio] Error getting audio, error : {e}")
            return None


class AudioLoop(BaseModel):
    book: Book
    audio_handler: Audio

    def run(self) -> None:
        is_sum_done = False
        while not is_sum_done:
            for chunk in self.book.get_chunks():
                audio_bytes = self.audio_handler.synthesize_speech(
                    chunk.summary, id=f"{chunk.chapter_id}/{chunk.chunk_id}"
                )
                if audio_bytes:
                    chunk.set_audio(audio_bytes)
            is_sum_done = self.book.is_sum_done()


def test():
    from reader_new import Book

    book = Book("./exp_book/LP.epub", user_id="b5bfc116-dd81-475a-8425-537a50621706")
    service_account_json = "./exalted-skein-446217-e2-e83f57244ce8.json"
    auido_handler = Audio(service_acc_path=service_account_json)
    audio_loop = AudioLoop(
        book=book,
        audio_handler=auido_handler,
    )
    audio_loop.run()


if __name__ == "__main__":
    test()

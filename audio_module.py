from google.cloud import texttospeech
import os
from dotenv import load_dotenv
from typing import List, Optional
from logger_module import logger

from reader_new import Book

load_dotenv()

service_account_json = "./exalted-skein-446217-e2-e83f57244ce8.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_json


class Audio:
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


class AudioLoop:
    book: Book
    audio_handler: Audio

    def run(self) -> None:
        is_sum_done = False
        while not is_sum_done:
            for chunk in self.book.get_chunks():
                audio_bytes=self.audio_handler.synthesize_speech(
                    chunk.summary, id=f"{chunk.chapter_id}/{chunk.chunk_id}"
                )
                if audio_bytes:

                    
            is_sum_done = self.book.is_sum_done()
        # return [(idx, synthesize_speech(i[1], idx)) for idx, i in enumerate(list_chapters)]

    def save_file(content:bytes)->bool:
        with open("output.mp3", "wb") as f:
            f.write(content)

def test():
    from reader import ebook

    book = ebook("./exp_book/LP.epub")
    chapter_content = book.get_chapters()
    audio = loop_for_speech(chapter_content)
    for idx, i in enumerate(audio):
        if i[1]:
            with open(f"./audio_out/{i[0]}", "wb") as file:
                file.write(i[1])
        else:
            logger.warning(f"Audio for Chapter : {idx} is None")


if __name__ == "__main__":
    test()




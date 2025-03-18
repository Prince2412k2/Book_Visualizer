from google.cloud import texttospeech
import os
from dotenv import load_dotenv
from typing import List
from logger_module import logger

load_dotenv()

service_account_json = "./exalted-skein-446217-e2-e83f57244ce8.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_json


def synthesize_speech(text: str, idx: int):
    # Initialize the Text-to-Speech client
    client = texttospeech.TextToSpeechClient()

    # Set the text input to be synthesized (plain text)
    input_text = texttospeech.SynthesisInput(text=text)

    # Build the voice request
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-GB",  # Match the voice name
        name="en-GB-Wavenet-B",  # British English male voice
        ssml_gender=texttospeech.SsmlVoiceGender.MALE,
    )

    # Specify the type of audio file you want to receive
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    try:
        # Perform the text-to-speech request
        response = client.synthesize_speech(
            input=input_text, voice=voice, audio_config=audio_config
        )
        logger.info(f"Chapter:{idx} done")
        return response.audio_content

    except Exception as e:
        logger.warning(f"[synthesize_speech] Error getting audio, error : {e}")


def loop_for_speech(list_chapters: List[str]):
    return [(idx, synthesize_speech(i[1], idx)) for idx, i in enumerate(list_chapters)]


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

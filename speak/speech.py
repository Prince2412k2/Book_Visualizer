import os
import logging
from deepgram.utils import verboselogs

from deepgram import (
    DeepgramClient,
    SpeakOptions,
)

text = """
    As the days pass, Meursault begins to reflect on his life and his relationship with his mother(sad).
    He realizes that they were never particularly close, and that he had rarely visited her during her last years at the nursing home.
    He wonders if his lack of attachment to his mother is why he is struggling to mourn her properly.
    One evening, Meursault goes to a café to drink and watch the crowd.
    He finds himself drawn to a woman named Marie, who is attracted to his detached demeanor.
    They begin a casual affair, with Meursault finding solace in Marie's company and her ability to distract him from his thoughts.
    """


SPEAK_TEXT = {"text": text}
filename = "test.mp3"


def main():
    try:
        # STEP 1 Create a Deepgram client using the API key from environment variables
        deepgram = DeepgramClient(api_key="63407be4062455775c293bece203cbe1b19a636a")

        # STEP 2 Call the save method on the speak property
        options = SpeakOptions(model="aura-luna-en")

        response = deepgram.speak.rest.v("1").save(filename, SPEAK_TEXT, options)
        print(response.to_json(indent=4))

    except Exception as e:
        print(f"Exception: {e}")


if __name__ == "__main__":
    main()

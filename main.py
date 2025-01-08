import typing
from reader import ebook, printl, printd
import requests
from huggingface_hub import InferenceClient
from typing import Optional
import json
import time
import ast
from functools import lru_cache
from dotenv import load_dotenv
import os


load_dotenv()
API = os.getenv("HF_API")

##stabilityai
client = InferenceClient(
    "stabilityai/stable-diffusion-3.5-large-turbo",
    token=API,
)

##QWEN:2.5
headers = {
    "Authorization": f"Bearer {API}",
    "Content-Type": "application/json",
}
url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3/v1/chat/completions"


def msg(text: str) -> list:
    message = [
        {
            "role": "system",
            "content": """ NOTE-"Only Output a python list and nothing else".
                Seprate the given TEXT whenever the setting changes and write image-generation prompt for each separated scene in Details,
                put these Prompts in single Python List. use character names whenever posible. 
                input->TEXT,
                Output format->["","","",....]
            """,
        },
        {
            "role": "user",
            "content": f"""TEXT: {text}""",  # This should be your input text that describes the scenes
        },
    ]
    return message


def read_json(raw_json: str) -> Optional[dict]:
    try:
        data = json.loads(raw_json)
        return data
    except json.JSONDecodeError as e:
        print(f"Error: {e}")
        print("\n\n\n" + raw_json)


def read_list(raw_text):
    try:
        lst = ast.literal_eval(raw_text)
        return lst
    except ValueError as e:
        print(f"Error: {e}")
        print("\n\n\n" + raw_text)
        return None


@lru_cache(maxsize=1024)
def get_images(key, value):
    image = client.text_to_image(
        value + ", Style: hand-painted, vintage, novel,book,classic ",
        height=528,
        width=720,
    )
    image.save(f"./output/ST_{key}.png")


def get_scene(text: str) -> Optional[str]:
    messages = msg(text)
    data = {
        "messages": messages,
        "max_tokens": 1000,  # Specify the maximum length of the response
        "temperature": 0.5,  # Control the randomness of the response
        "stream": False,
    }
    response = requests.post(url, headers=headers, json=data)

    # Check the response status code and process the output
    if response.status_code == 200:
        response_data = response.json()
        # Extract the assistant's message content
        assistant_message = response_data["choices"][0]["message"]["content"]
        return assistant_message
    else:
        print(f"Error: {response.status_code}, {response.text}")  # Print error details
        return None


def main() -> None:
    book = ebook("./books/stranger.pdf")
    chapter = book.get_chapters()[5][1]
    pmpt = get_scene(chapter)
    # scenes = read_json(pmpt)
    scene_list = read_list(pmpt)

    try:
        for idx, i in enumerate(scene_list):
            get_images(idx, i)
            print(idx, " : downloaded")
            print(i, end="\n\n\n")
            time.sleep(30)
    except Exception as e:
        print(f"LOOP ERROR : {e}")
        # print("\n\n\n INPUT---------------" + chapter)


def text() -> None:
    book = ebook("./books/stranger.pdf")
    chapter = book.get_chapters()[1][1]
    pmpt = get_scene(chapter)
    print(pmpt)


if __name__ == "__main__":
    main()

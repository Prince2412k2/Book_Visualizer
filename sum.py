from reader import ebook
import requests
from typing import Optional, Text
from dotenv import load_dotenv
import os
import time


def save_strings_to_file(strings, filename):
    with open(filename, "w", encoding="utf-8") as file:
        for string in strings:
            file.write(string + "\n\n\n")  # Write each string followed by a newline


load_dotenv()
API = os.getenv("HF_API")
##mistralai
headers = {"Authorization": f"Bearer {API}"}
url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-Coder-32B-Instruct/v1/chat/completions"


def msg(text: str, chapter: int, context: str) -> list:
    messages_1 = [
        {
            "role": "system",
            "content": """ create a summary of given story chapter without losing its essence, do not conclude the story say to be continued at the end""",
        },
        {
            "role": "user",
            "content": text,  # This should be your input text that describes the scenes
        },
    ]
    messages_2 = [
        {
            "role": "system",
            "content": """create a summary of given story chapter based on the context of previous chapter summary. do not conclude the story, say to be continue at the end """,
        },
        {
            "role": "user",
            "content": f"context:{context}  Story:{text}",  # This should be your input text that describes the scenes
        },
    ]
    return messages_1 if chapter == 0 else messages_2


def get_summary(text: str, chapter: int, context: str = "") -> Optional[str]:
    messages = msg(text, chapter, context)
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


# def summarize_chapters(text:str)->list:


def main():
    book = ebook("./books/HP.epub")
    chapters = book.get_chapters()
    summary = [""]
    start_time = time.time()
    for idx, (chap, content) in enumerate(chapters):
        # if idx == 6:
        #    break
        summary.append(f"\n\n{chap}\n{get_summary(content, idx, summary[-1])}")
        print(f"{chap} done")
    end_time = time.time()
    save_strings_to_file(summary, "./output/HP_summary.txt")
    print("file saved")
    print(f"Took {end_time-start_time} secconds")


if __name__ == "__main__":
    main()

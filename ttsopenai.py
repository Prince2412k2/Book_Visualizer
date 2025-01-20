import requests
from reader import ebook

url = "https://api.ttsopenai.com/uapi/v1/story-maker"
headers = {
    "Content-Type": "application/json",
    "x-api-key": "tts-389eea7fb1622e6a8b1ffa8f0814628d",
}


def gen(text):
    data = {
        "name": "Name of the story",
        "blocks": [
            {
                "name": "Name of the block",
                "input": "Text to be converted into speech",
                "silence_before": 2,
                "voice_id": "OA001",
                "emotion": "neutral",
                "model": "tts-1",
                "speed": 1,
                "duration": 0,
            }
        ],
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        # Assuming the API returns the audio in a binary format
        with open("output_audio.mp3", "wb") as file:
            file.write(response.content)
        print("Audio saved as 'output_audio.mp3'")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())


book = ebook("./books/LP.epub")
text = book.get_chapters()[0][1]
print(text)

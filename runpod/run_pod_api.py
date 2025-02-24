import os
import requests

## fetch api from ".env"
# api = os.environ.get("RUNPOD_API_KEY")
api = "rpa_ANRSXZ63FDP4KV1ZIAZPU3FE0FM6DSBR4C2UBDGN0jd0cb"
print(api)

model_name = "mistralai/Mistral-7B-Instruct-v0.3"
data = {
    "messages": [
        {
            "role": "system",
            "content": "Talk like a poet.",
        },
        {
            "role": "user",
            "content": "What is big bang??",
        },
    ]
}


headers = {"Content-Type": "application/json", "Authorization": api}

data = {"input": {"prompt": "Your prompt"}}

response = requests.post(
    "https://api.runpod.ai/v2/bv6h5bstwtu8m3/run", headers=headers, json=data
)
if response.status_code == 200:
    result = response.json()
    print(result)  # Extract the response text
else:
    print(f"Error {response.status_code}: {response.text}")

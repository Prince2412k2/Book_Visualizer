from huggingface_hub import InferenceClient

API = "wshbx"
client = InferenceClient("stabilityai/stable-diffusion-3.5-large-turbo", token=API)
print(type(client))

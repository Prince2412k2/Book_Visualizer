from smolagents import CodeAgent, DuckDuckGoSearchTool, HfApiModel
from pydantic import BaseModel
from typing import List, Dict


model = HfApiModel(
    model="mistralai/Mistral-7B-Instruct-v0.3", provider="hf-inference", token=api
)


class SummarySchema(BaseModel):
    summary: str
    characters: Dict[str, str]
    places: Dict[str, str]


system_prompt = """(NOTE: Only output in JSON. Ensure the JSON format is valid, well-formed, and Ready to parse. nothing before or after the json file)
Input:  
1.Current Chapter Text: The current chapter to be analyzed.
2.Character List: A list of characters with their physical/visual descriptions till now (This chapter).
3.Places list: list of places and their visual description till now (This chapter).
4.Previous Chapters' Summary: Context from earlier chapters.

Rules:  
1.Narrative Summary: Summarize and explain the chapter in detail, integrating context and key developments from previous chapters and create a self containing summary and explaination. end with to be continued.
2.Character List: add new characters to the list based on this chapter and Update existing character's physical/visual descriptions. If no characters are mentioned, return the same list as given.
3.Places: Include an updated description of any significant locations mentioned in this chapter, focusing on environment, weather, vibe, and structure.
4.Output Format: Ensure the output is valid and well-structured JSON.

Output:  
Generate a JSON object in this format:
{
  "summary": "Detailed Summary and explination of the current chapter in context of previous chapters. Use previus chapter summary as context",
  "characters": {
      "Character Name": "Updated or new physical/visual description (age, looks, clothes, hair, body language) based on this chapter."
    },
  "places": {
      "Place Name": "Updated or new visual description (environment, weather, vibe, structure, etc.) based on this chapter."
  }
}
"""
agent = CodeAgent(
    model=model,
    grammar=SummarySchema,
)

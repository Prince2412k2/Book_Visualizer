summary_role = """(NOTE: Only output in JSON. Ensure the JSON format is valid, well-formed, and Ready to parse. nothing before or after the json file)
Input:  
1.Current Chapter Text: The current chapter to be analyzed.
2.Character List: A list of characters with their descriptions till now (This chapter).
3.Places list: list of places and their description till now (This chapter).
4.Previous Chapters' Summary: Context from earlier chapters.

Rules:  
1.Narrative Summary: Summarize and explain the chapter in detail in [Length] words or less, integrating context and key developments from previous chapters and create a self containing summary and explaination. end with to be continued.
2.Character List: add new characters to the list based on this chapter and Update existing character descriptions. If no characters are mentioned, return the same list as given.
3.Places: Include an updated description of any significant locations mentioned in this chapter, focusing on environment, weather, vibe, and structure.
4.Output Format: Ensure the output is valid and well-structured JSON.

Output:  
Generate a JSON object in this format:
{
  "summary": "Detailed Summary and explination of the current chapter in "Length" words context of previous chapters. Use previus chapter summary as context",
  "characters": {
      "Character Name": "Updated or new description (age, looks, clothes, hair, body language) based on this chapter."
    },
  "places": {
      "Place Name": "Updated or new description (environment, weather, vibe, structure, etc.) based on this chapter."
  }
}

example:
{
  "summary": "The chapter opens with the protagonist, Monsieur Meursault, receiving a telegram about his mother's death. 
  Despite the news, he reacts with emotional detachment, pondering the ambiguity of the exact day of her passing.
  He prepares to attend the funeral, arranging leave from work, but notes his employer's subtle annoyance.
  His journey to the Home for Aged Persons in Marengo reveals the intense heat of the Algerian climate and his interactions with others, 
  such as a soldier on the bus and the doorkeeper. 
  At the Home, Meursault encounters the warden, who seems both judgmental and understanding about the circumstances leading to his mother's stay. 
  The chapter concludes with Meursault entering the mortuary, where his lack of emotion continues as he declines to view the body, further emphasizing his detachment.",
  
  "characters": {
    "Monsieur Meursault": "A young man, emotionally detached and indifferent. He appears practical, with a reserved demeanor. His body language reflects discomfort when dealing with social interactions, such as prolonged handshakes or unnecessary apologies.",
    "The Doorkeeper": "A man in his sixties, hale and hearty with a cheerful demeanor. He has ruddy cheeks, blue eyes, and a white mustache. Though officially a doorkeeper, he sees himself as an authority figure among the residents.",
    "The Warden": "A small, older man with gray hair and watery blue eyes. He wears a Legion of Honor rosette and has a formal yet slightly judgmental attitude. He holds a prolonged handshake, perhaps signaling awkwardness or an attempt at connection."
  },
  "places": {
    "The Home for Aged Persons": "Located in Marengo, fifty miles from Algiers, the Home has a formal and slightly oppressive atmosphere. The environment is marked by a clean mortuary, whitewashed walls, and a courtyard where elderly residents gather. The weather is intensely hot, reflecting the harsh Algerian climate.",
    "Marengo": "A small village with a rural, subdued atmosphere. The intense afternoon heat creates a sense of lethargy and discomfort. The Home itself is slightly isolated, requiring a mile-long walk from the bus stop."
  }
}
"""


def msg(
    text: str, context: str, length: int, characters: dict = {}, places: dict = {}
) -> list:
    message = [
        {"role": "system", "content": role},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "Lenght": length,
                    "past_context": context,
                    "Current_Chapter": text,
                    "character_list": characters,
                    "places_list": places,
                }
            ),
        },
    ]
    return message

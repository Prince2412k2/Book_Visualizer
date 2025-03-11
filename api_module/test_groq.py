
def get_recipe(recipe_name: str) -> SummaryOutputSchema:
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": f"{SUMMARY_ROLE}"
                # Pass the json schema to the model. Pretty printing improves results.
                f" The JSON object must use the schema: {json.dumps(SummaryOutputSchema.model_json_schema(), indent=2)}",
            },
            {
                "role": "user",
                "content": f"{recipe_name}",
            },
        ],
        model="llama-3.2-1b-preview",  # Correct placement as a keyword argument
        temperature=0,
        # Streaming is not supported in JSON mode
        stream=False,
        # Enable JSON mode by setting the response format
        response_format={"type": "json_object"},

from typing import NamedTuple

"""
Constants for parameters of API call
"""


# Model Configuration
MODEL_NAME: str = "llama-3.1-8b-instant"

# Temperature: Controls randomness (higher = more creative, lower = more deterministic)
TEMPERATURE: float = 0.6

# Top-P (Nucleus Sampling): Controls probability cutoff for token selection (higher = more diverse)
TOP_P: float = 0.8

# Frequency Penalty: Reduces repetition of frequent tokens (higher = less repetition)
FREQUENCY_PENALTY: float = 1.0

# Presence Penalty: Encourages diversity by discouraging previously used tokens (higher = more novelty)
PRESENCE_PENALTY: float = 1.5

# Maximum tokens allowed in the model output
MAXTOKENS: int = 7500

# Maximum Output token count for generated summaries
MAX_OUTPUT_SUMMARY: int = 2000

# Maximum Output token count for prompt output
MAX_OUTPUT_PROMPT: int = 2000

# Chunk length for processing large inputs
CHUNK_LENGTH: int = MAXTOKENS


class ImageConfig(NamedTuple):
    pass


class AudioConfig(NamedTuple):
    pass

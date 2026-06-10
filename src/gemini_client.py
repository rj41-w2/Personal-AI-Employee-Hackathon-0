import os
from google import genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")


def call_gemini(system_prompt, user_prompt, model=None):
    model_name = model or GEMINI_MODEL
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=model_name,
        contents=user_prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt
        )
    )
    return response.text

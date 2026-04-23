import os

from dotenv import load_dotenv
from openai import OpenAI


# Load environment variables from the local .env file.
load_dotenv()


# Read Azure OpenAI settings from environment variables.
endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT")
model_name = os.getenv("AZURE_FOUNDRY_MODEL")
api_key = os.getenv("AZURE_FOUNDRY_API_KEY")


# Check that all required values exist before making the API call.
missing_keys = []
if not endpoint:
    missing_keys.append("AZURE_FOUNDRY_ENDPOINT")
if not model_name:
    missing_keys.append("AZURE_FOUNDRY_MODEL")
if not api_key:
    missing_keys.append("AZURE_FOUNDRY_API_KEY")

if missing_keys:
    print("Missing required environment variables:")
    for key in missing_keys:
        print(f"- {key}")
    raise SystemExit(1)


# Create the OpenAI client using Azure endpoint and API key from .env.
client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)


# Ask a simple test question to verify the model call works.
response = client.chat.completions.create(
    model=model_name,
    messages=[
        {
            "role": "user",
            "content": "How many R's are there in te word raspberry?",
        }
    ],
)


# Print the model output so it is easy to confirm in terminal.
print("Model response:")
print(response.choices[0].message.content)

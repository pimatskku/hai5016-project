import os

from dotenv import load_dotenv
from openai import OpenAI

# Load values from the .env file into environment variables.
load_dotenv()

# Read Azure Foundry/OpenAI settings from environment variables.
endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT")
model_name = os.getenv("AZURE_FOUNDRY_MODEL")
api_key = os.getenv("AZURE_FOUNDRY_API_KEY")

# Stop early with a clear message if any required variable is missing.
if not endpoint or not model_name or not api_key:
    print("Missing one or more environment variables:")
    print("- AZURE_FOUNDRY_ENDPOINT")
    print("- AZURE_FOUNDRY_MODEL")
    print("- AZURE_FOUNDRY_API_KEY")
    raise SystemExit(1)

# Create an OpenAI-compatible client that points to your Azure endpoint.
client = OpenAI(base_url=endpoint, api_key=api_key)

# Ask a simple test question to verify the model call works.
response = client.chat.completions.create(
    model=model_name,
    messages=[
        {
            "role": "user",
            "content": "How many R's are there in strawberry?",
        }
    ],
)

# Print the model response to confirm everything is working.
print("Model reply:")
print(response.choices[0].message.content)

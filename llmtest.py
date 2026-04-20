"""Very simple Azure LLM connectivity test.

This script asks the model:
"How many R's are in strawberry?"
"""

import os

from dotenv import load_dotenv
from openai import AzureOpenAI


def main() -> None:
    # Load environment variables from .env file.
    load_dotenv()

    # Read Azure Foundry / Azure OpenAI settings from environment variables.
    api_key = os.getenv("AZURE_FOUNDRY_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
    model_name = os.getenv("AZURE_FOUNDRY_MODEL") or os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not api_key or not endpoint or not model_name:
        print("Missing required environment variables.")
        print("Please set one of these groups in your .env file:")
        print("1) AZURE_FOUNDRY_API_KEY, AZURE_FOUNDRY_ENDPOINT, AZURE_FOUNDRY_MODEL")
        print("2) AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT")
        return

    # Create Azure OpenAI client.
    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version="2024-02-01",
    )

    # Send one simple test question.
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": "How many R's are in strawberry? Please answer with only the number.",
            }
        ],
        temperature=0,
    )

    print("Azure LLM response:")
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()

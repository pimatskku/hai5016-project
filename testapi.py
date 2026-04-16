import os
from pathlib import Path

from openai import OpenAI


def load_dotenv(dotenv_path: str = ".env") -> None:
    """Lightweight .env loader to avoid extra dependencies."""
    env_file = Path(dotenv_path)
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def main() -> None:
    load_dotenv()

    api_key = os.getenv("AZURE_FOUNDRY_API_KEY")
    endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT")
    model = os.getenv("AZURE_FOUNDRY_MODEL")

    missing = [
        name
        for name, value in {
            "AZURE_FOUNDRY_API_KEY": api_key,
            "AZURE_FOUNDRY_ENDPOINT": endpoint,
            "AZURE_FOUNDRY_MODEL": model,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit(f"Missing required env vars: {', '.join(missing)}")

    client = OpenAI(api_key=api_key, base_url=endpoint)
    question = "How many R's are there in the word raspberry?"

    response = client.responses.create(
        model=model,
        input=question,
    )

    print("Question:", question)
    print("Model response:")
    print(response.output_text)


if __name__ == "__main__":
    main()

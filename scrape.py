import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

ALLOWED_MEAL_TYPES = {"breakfast", "lunch", "dinner", "unknown"}

# Common non-meal placeholders that should not be saved as a menu item.
INVALID_MEAL_NAMES = {
    "",
    "nan",
    "none",
    "null",
    "menu",
    "meal",
    "restaurant",
    "cafeteria",
    "food",
    "kcal",
}


def parse_arguments() -> argparse.Namespace:
    """Read command-line options for input file and confidence threshold."""
    parser = argparse.ArgumentParser(description="Scrape campus menus and save JSONL")
    parser.add_argument(
        "--excel",
        default="Campus restaurant websites.xlsx",
        help="Path to the input Excel file",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.6,
        help="Minimum confidence score for meal_name",
    )
    return parser.parse_args()


def setup_logging() -> Path:
    """Configure loguru to log both to file and console."""
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_path = logs_dir / f"scrape-{datetime.now().strftime('%Y-%m-%d')}.log"

    logger.remove()
    logger.add(log_path, level="INFO", encoding="utf-8")
    logger.add(lambda message: print(message, end=""), level="INFO")

    return log_path


def load_settings() -> tuple[str, str, str]:
    """Load required Azure OpenAI-compatible settings from .env."""
    load_dotenv()

    endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT", "").strip()
    model_name = os.getenv("AZURE_FOUNDRY_MODEL", "").strip()
    api_key = os.getenv("AZURE_FOUNDRY_API_KEY", "").strip()

    missing = []
    if not endpoint:
        missing.append("AZURE_FOUNDRY_ENDPOINT")
    if not model_name:
        missing.append("AZURE_FOUNDRY_MODEL")
    if not api_key:
        missing.append("AZURE_FOUNDRY_API_KEY")

    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Missing required .env variables: {missing_text}")

    return endpoint, model_name, api_key


def resolve_excel_path(requested_path: str) -> Path:
    """Resolve the Excel path and try common filename variants."""
    direct_path = Path(requested_path)
    if direct_path.exists():
        return direct_path

    fallback_names = [
        "campus_restaurant_websites.xlsx",
        "Campus restaurant websites.xlsx",
    ]
    for name in fallback_names:
        fallback_path = Path(name)
        if fallback_path.exists():
            return fallback_path

    return direct_path


def normalize_column_name(value: Any) -> str:
    """Normalize a column name for case-insensitive matching."""
    text = "" if pd.isna(value) else str(value)
    return text.strip().lower()


def load_sources(excel_path: Path) -> list[dict[str, str]]:
    """Read website sources from Excel and return clean source rows."""
    raw_df = pd.read_excel(excel_path, header=None)

    header_row_index = None
    for row_index in range(len(raw_df)):
        row_values = [normalize_column_name(value) for value in raw_df.iloc[row_index].tolist()]
        if "university" in row_values and "url" in row_values:
            header_row_index = row_index
            break

    if header_row_index is None:
        raise ValueError("Could not find Excel header row with 'University' and 'url/Url'.")

    df = pd.read_excel(excel_path, header=header_row_index)
    normalized_map = {normalize_column_name(col): col for col in df.columns}

    if "university" not in normalized_map or "url" not in normalized_map:
        raise ValueError("Excel file must contain 'University' and 'url' columns.")

    university_col = normalized_map["university"]
    url_col = normalized_map["url"]
    restaurant_col = normalized_map.get("restaurant")

    sources: list[dict[str, str]] = []
    for _, row in df.iterrows():
        university = "" if pd.isna(row[university_col]) else str(row[university_col]).strip()
        url = "" if pd.isna(row[url_col]) else str(row[url_col]).strip()
        restaurant_name = ""
        if restaurant_col is not None and not pd.isna(row[restaurant_col]):
            restaurant_name = str(row[restaurant_col]).strip()

        if not url.startswith("http"):
            continue

        sources.append(
            {
                "university": university,
                "url": url,
                "restaurant_name": restaurant_name,
            }
        )

    return sources


def fetch_readable_text(client: httpx.Client, url: str) -> str:
    """Download a page and extract readable text."""
    response = client.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script/style content to reduce noise for extraction.
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
    non_empty_lines = [line for line in lines if line]

    return "\n".join(non_empty_lines)


def ask_model_for_menus(
    openai_client: OpenAI,
    model_name: str,
    page_text: str,
    source: dict[str, str],
) -> list[dict[str, Any]]:
    """Ask the model to extract menu items as JSON from plain text."""
    text_for_model = page_text[:16000]

    system_prompt = (
        "You extract cafeteria menu information from webpage text. "
        "Return valid JSON only."
    )

    user_prompt = (
        "Extract menu items from this text.\n"
        "Use these fields for each item:\n"
        "- menu_date (YYYY-MM-DD when possible, otherwise empty string)\n"
        "- meal_type (breakfast, lunch, dinner, or unknown)\n"
        "- meal_name (actual meal name only)\n"
        "- price_krw (numbers only as string, empty string if unknown)\n"
        "- restaurant_name (restaurant/cafeteria name if available, else empty string)\n"
        "- confidence (0 to 1, confidence that meal_name is a real meal)\n\n"
        "Rules:\n"
        "- Do not include general text, announcements, or invalid meal names.\n"
        "- If not sure a meal_name is a meal, set confidence low (<0.6).\n"
        "- Keep meal_type lowercase.\n\n"
        "Return JSON object with one key: menus.\n"
        "Example: {\"menus\": [{...}]}\n\n"
        f"University: {source['university']}\n"
        f"URL: {source['url']}\n"
        f"Known restaurant_name: {source['restaurant_name']}\n\n"
        "Page text:\n"
        f"{text_for_model}"
    )

    response = openai_client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )

    raw_content = response.choices[0].message.content or "{}"
    parsed = json.loads(raw_content)
    menus = parsed.get("menus", [])

    if not isinstance(menus, list):
        return []

    return menus


def normalize_meal_type(value: Any) -> str:
    """Map free-text meal type into the allowed set."""
    text = "" if value is None else str(value).strip().lower()
    if text in ALLOWED_MEAL_TYPES:
        return text

    if "breakfast" in text or text == "b":
        return "breakfast"
    if "lunch" in text or text == "l":
        return "lunch"
    if "dinner" in text or text == "d":
        return "dinner"

    return "unknown"


def normalize_price(value: Any) -> str:
    """Keep only numeric KRW price content as a string."""
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    digits = re.sub(r"[^0-9]", "", text)
    return digits


def is_valid_meal_name(value: Any) -> bool:
    """Reject empty or obviously invalid meal names."""
    if value is None:
        return False

    text = str(value).strip()
    if not text:
        return False

    if text.lower() in INVALID_MEAL_NAMES:
        return False

    # Very short tokens are likely not actual meal names.
    if len(text) < 2:
        return False

    return True


def build_menu_record(
    item: dict[str, Any],
    source: dict[str, str],
    scrape_date: str,
    confidence_threshold: float,
) -> dict[str, str] | None:
    """Validate and normalize one extracted menu item."""
    meal_name = item.get("meal_name", "")
    confidence = item.get("confidence", 0)

    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        confidence_value = 0.0

    if confidence_value < confidence_threshold:
        return None

    if not is_valid_meal_name(meal_name):
        return None

    menu_date = "" if item.get("menu_date") is None else str(item.get("menu_date")).strip()
    restaurant_name = ""
    if item.get("restaurant_name") is not None:
        restaurant_name = str(item.get("restaurant_name")).strip()
    if not restaurant_name:
        restaurant_name = source["restaurant_name"]

    record = {
        "scrape_date": scrape_date,
        "url": source["url"],
        "menu_date": menu_date,
        "meal_type": normalize_meal_type(item.get("meal_type", "unknown")),
        "meal_name": str(meal_name).strip(),
        "price_krw": normalize_price(item.get("price_krw", "")),
        "university": source["university"],
        "restaurant_name": restaurant_name,
        "restaurant": restaurant_name,
    }

    return record


def main() -> None:
    """Run the end-to-end scraping and extraction flow."""
    args = parse_arguments()
    log_path = setup_logging()
    logger.info(f"Logging to {log_path}")

    excel_path = resolve_excel_path(args.excel)
    if not excel_path.exists():
        logger.error(f"Excel file not found: {excel_path}")
        raise SystemExit(1)

    try:
        endpoint, model_name, api_key = load_settings()
    except ValueError as error:
        logger.error(str(error))
        raise SystemExit(1)

    try:
        sources = load_sources(excel_path)
    except Exception as error:
        logger.exception(f"Failed to read Excel sources: {error}")
        raise SystemExit(1)

    if not sources:
        logger.warning("No valid sources were found in Excel file.")
        raise SystemExit(0)

    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)

    output_path = results_dir / f"menus-{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    logger.info(f"Output file: {output_path}")
    logger.info(f"Sources to process: {len(sources)}")

    openai_client = OpenAI(base_url=endpoint, api_key=api_key)

    total_written = 0
    with output_path.open("a", encoding="utf-8") as output_file:
        with httpx.Client(
            timeout=httpx.Timeout(5.0),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as http_client:
            for index, source in enumerate(sources, start=1):
                logger.info(
                    f"[{index}/{len(sources)}] Processing {source['university']} | {source['url']}"
                )

                try:
                    page_text = fetch_readable_text(http_client, source["url"])
                except Exception as error:
                    logger.error(f"Skipping URL due to fetch failure: {source['url']} | {error}")
                    continue

                if not page_text.strip():
                    logger.warning(f"No readable text found, skipping: {source['url']}")
                    continue

                try:
                    extracted_items = ask_model_for_menus(
                        openai_client=openai_client,
                        model_name=model_name,
                        page_text=page_text,
                        source=source,
                    )
                except Exception as error:
                    logger.error(
                        f"Skipping URL due to model extraction failure: {source['url']} | {error}"
                    )
                    continue

                scrape_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                written_for_url = 0

                for item in extracted_items:
                    if not isinstance(item, dict):
                        continue

                    record = build_menu_record(
                        item=item,
                        source=source,
                        scrape_date=scrape_date,
                        confidence_threshold=args.confidence_threshold,
                    )
                    if record is None:
                        continue

                    output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                    output_file.flush()
                    total_written += 1
                    written_for_url += 1

                logger.info(
                    f"Completed URL with {written_for_url} valid menu items written: {source['url']}"
                )

    logger.info(f"Done. Total menu items written: {total_written}")
    logger.info(f"Saved JSONL to: {output_path}")


if __name__ == "__main__":
    main()

"""
test_url_check.py
-----------------
Step 1 – probe every URL in campus_menu_sources before running the real scraper.

For each row it will:
  1. Try to fetch the page (5-second timeout).
  2. Look for food-related content (Korean and English keywords).
  3. Try to identify which CSS selector best wraps the menu content.
  4. Print a summary table.
  5. Mark rows with no food content as valid = False in Supabase.
  6. Update content_div_selector in Supabase where a good div was found.

Run this BEFORE running scrape.py to make sure the source data is clean.
"""

import os
import re
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv
from loguru import logger
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
REQUEST_TIMEOUT_SECONDS = 8.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36"
)

# Korean and English words that should appear on a cafeteria menu page.
# If none of these are found the page probably isn't showing menu data.
FOOD_KEYWORDS = [
    # Korean
    "메뉴", "식단", "식사", "점심", "저녁", "아침", "밥", "국",
    "kcal", "칼로리", "원", "가격",
    # English
    "menu", "meal", "lunch", "dinner", "breakfast", "rice", "soup",
    "price", "won", "cafeteria", "restaurant",
]

# CSS selectors to try, in order of preference.
# We pick the first one that contains a food keyword.
CANDIDATE_SELECTORS = [
    # id-based
    "#menu", "#content", "#main-content", "#foodmenu", "#food-menu",
    "#menu-content", "#mainContent", "#sub_content", "#contents",
    # class-based
    ".menu", ".food-menu", ".menu-content", ".meal-info",
    ".board_view", ".view_content", ".content_area", ".main_content",
    ".sub_content", ".cafeteria", ".restaurant",
    # Korean university common patterns
    ".tab-content", ".table_wrap", ".tbl_wrap",
    # Generic fallback
    "main", "article", "#wrap",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "test_url_check.log"
    logger.remove()
    logger.add(log_path, rotation="1 MB", encoding="utf-8")
    logger.add(lambda message: print(message, end=""))


def contains_food_keywords(text: str) -> bool:
    """Return True if any food keyword appears in the text (case-insensitive)."""
    lower_text = text.lower()
    return any(keyword.lower() in lower_text for keyword in FOOD_KEYWORDS)


def find_best_selector(soup: BeautifulSoup) -> str | None:
    """
    Try each candidate CSS selector and return the first one whose
    element contains at least one food keyword.
    Returns None if nothing matched.
    """
    for selector in CANDIDATE_SELECTORS:
        element = soup.select_one(selector)
        if element and contains_food_keywords(element.get_text()):
            return selector

    # Fallback: scan ALL divs and pick the one with the most food keyword hits
    best_selector = None
    best_score = 0

    for div in soup.find_all("div"):
        text = div.get_text()
        score = sum(1 for kw in FOOD_KEYWORDS if kw.lower() in text.lower())
        if score > best_score:
            best_score = score
            # Build a selector from id or class if available
            div_id = div.get("id")
            div_class = div.get("class")
            if div_id:
                best_selector = f"#{div_id}"
            elif div_class:
                # Use the first class only to keep it simple
                best_selector = f".{div_class[0]}"
            else:
                best_selector = "div"

    # Only return a selector if it scored at least 2 keyword hits
    if best_score >= 2:
        return best_selector

    return None


def check_url(client: httpx.Client, url: str) -> dict:
    """
    Fetch a URL and return a result dictionary with:
      - status: "ok" | "timeout" | "http_error" | "no_content"
      - http_code: int or None
      - has_food: bool
      - selector: str or None  (best CSS selector found)
      - error: str or None
    """
    result = {
        "status": "ok",
        "http_code": None,
        "has_food": False,
        "selector": None,
        "error": None,
    }

    try:
        response = client.get(url.strip())
        result["http_code"] = response.status_code
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script / style noise before checking
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        page_text = soup.get_text()
        result["has_food"] = contains_food_keywords(page_text)

        if result["has_food"]:
            result["selector"] = find_best_selector(soup)
        else:
            result["status"] = "no_content"

    except httpx.TimeoutException:
        result["status"] = "timeout"
        result["error"] = "Request timed out"
    except httpx.HTTPStatusError as exc:
        result["status"] = "http_error"
        result["http_code"] = exc.response.status_code
        result["error"] = str(exc)
    except httpx.HTTPError as exc:
        result["status"] = "http_error"
        result["error"] = str(exc)
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_logging()
    load_dotenv()

    # Connect to Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        raise EnvironmentError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

    db: Client = create_client(supabase_url, supabase_key)

    # Fetch all rows from campus_menu_sources
    response = db.table("campus_menu_sources").select(
        "id, university_name, campus, source_url, valid"
    ).execute()
    rows = response.data
    logger.info(f"Loaded {len(rows)} rows from campus_menu_sources")

    headers = {"User-Agent": USER_AGENT}
    results_summary = []

    with httpx.Client(
        headers=headers,
        follow_redirects=True,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as http_client:
        total = len(rows)

        for index, row in enumerate(rows, start=1):
            url = row["source_url"]
            row_id = row["id"]
            name = f"{row['university_name']} / {row.get('campus') or 'main'}"

            logger.info(f"[{index}/{total}] Testing: {name}  →  {url}")

            result = check_url(http_client, url)

            # Decide what to write back to Supabase
            update_payload = {}

            if result["status"] == "ok" and result["has_food"]:
                logger.info(
                    f"  ✓ OK  |  food found  |  selector: {result['selector'] or '(none detected)'}"
                )
                if result["selector"]:
                    update_payload["content_div_selector"] = result["selector"]
            elif result["status"] == "no_content":
                logger.warning(f"  ✗ No food keywords found — marking valid=False")
                update_payload["valid"] = False
            elif result["status"] == "timeout":
                logger.warning(f"  ✗ Timeout — marking valid=False")
                update_payload["valid"] = False
            elif result["status"] in ("http_error", "error"):
                logger.error(
                    f"  ✗ {result['status'].upper()}: {result['error']} — marking valid=False"
                )
                update_payload["valid"] = False

            # Write the update to Supabase (only if there's something to change)
            if update_payload:
                db.table("campus_menu_sources").update(update_payload).eq("id", row_id).execute()
                logger.info(f"  → Updated DB: {update_payload}")

            results_summary.append({
                "name": name,
                "url": url,
                "status": result["status"],
                "http_code": result["http_code"],
                "has_food": result["has_food"],
                "selector": result["selector"],
            })

            # Small polite delay between requests
            time.sleep(0.5)

    # Print a final summary table
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    for r in results_summary:
        flag = "✓" if r["has_food"] else "✗"
        logger.info(
            f"  {flag}  [{r['status']:12s}]  code={r['http_code'] or '---'}  "
            f"sel={r['selector'] or 'none':30s}  {r['name']}"
        )

    total_ok = sum(1 for r in results_summary if r["has_food"])
    total_bad = len(results_summary) - total_ok
    logger.info(f"\nTotal: {total_ok} good, {total_bad} failed/no-content out of {len(results_summary)}")


if __name__ == "__main__":
    main()

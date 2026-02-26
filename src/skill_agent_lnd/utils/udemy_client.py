import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

def load_config() -> dict[str, Any]:
    """Load configuration from environment variables or fallback to JSON file."""
    # Priority 1: Environment Variables
    env_config = {
        "account_id": os.getenv("UDEMY_ACCOUNT_ID"),
        "account_name": os.getenv("UDEMY_SUBDOMAIN"),
        "client_id": os.getenv("UDEMY_CLIENT_ID"),
        "client_secret": os.getenv("UDEMY_CLIENT_SECRET"),
    }

    # If all env vars are present, return them
    if all(env_config.values()):
        logger.info("Loaded Udemy config from Environment Variables")
        return env_config

    # Priority 2: Local Config File (Fallback)
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parents[3]
    config_path = project_root / "udemy" / "config.json"

    if not config_path.exists():
        config_path = Path("udemy/config.json").resolve()

    try:
        if config_path.exists():
            with config_path.open("r") as f:
                logger.info(f"Loaded Udemy config from {config_path}")
                config = json.load(f)
                if isinstance(config, dict):
                    return config
    except Exception as e:
        logger.error(f"Failed to load Udemy config: {e}")

    return {}

# Initialize credentials
_config = load_config()
ACCOUNT_ID = _config.get("account_id")
SUBDOMAIN = _config.get("account_name")
CLIENT_ID = _config.get("client_id")
CLIENT_SECRET = _config.get("client_secret")

SKILL_ALIAS_MAP = {
    "nextjs": "next.js",
    "expressjs": "express", # 'express' with boundary check is safe
    "vuejs": "vue.js",
    "angularjs": "angular",
    "node.js": "node", # normalize to simple 'node' if needed
    "nodejs": "node.js",
}

def _match_skill(query: str, title: str) -> bool:
    """
    Helper to match a skill query against a course title using regex and aliases.
    """
    q_raw = query.lower()
    t = title.lower()

    # 1. Check Aliases
    # If the query is in our map, use the mapped version (e.g. nextjs -> next.js)
    search_term = SKILL_ALIAS_MAP.get(q_raw, q_raw)

    # SPECIAL EXCLUSION: If searching for "express", exclude "adobe" (Adobe Express)
    if search_term == "express" and "adobe" in t:
        return False

    # 2. Regex Match with Word Boundaries
    try:
        # specific handling for dot escaping
        escaped_term = re.escape(search_term)
        pattern = r"\b" + escaped_term + r"\b"
        if re.search(pattern, t):
            return True

        # Special Case: 'js' suffix removal for unmapped terms (fallback)
        if q_raw.endswith("js") and len(q_raw) > 2 and q_raw not in SKILL_ALIAS_MAP:
            base = q_raw[:-2]
            if len(base) > 2:
                 pattern_base = r"\b" + re.escape(base) + r"\b"
                 if re.search(pattern_base, t):
                     return True

    except Exception:
        # Fallback to simple substring
        if search_term in t:
            return True

    return False

def fetch_single_course(skill_name: str, language: str = "en") -> dict[str, Any]:
    """
    Fetches the first matching course for a skill by iterating through pages.
    """
    if not all([ACCOUNT_ID, SUBDOMAIN, CLIENT_ID, CLIENT_SECRET]):
        return {}

    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Accept": "application/json, version=2.0",
    }

    url = (
        f"https://{SUBDOMAIN}.udemy.com/api-2.0/organizations/"
        f"{ACCOUNT_ID}/courses/list/"
    )

    page = 1

    try:
        # Scan up to 200 pages (20,000 courses) - Fast scan
        while page <= 200:
            if page % 20 == 0: # Log less frequently
                 logger.info(f"Scanning page {page} for '{skill_name}'...")

            params: dict[str, Any] = {
                "page": page,
                "page_size": 100, # Maximize page size for speed
                "fields[course]": "id,title,url,headline,visible_instructors,locale",
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Udemy API returned {response.status_code}")
                break

            data = response.json()
            results = data.get("results", [])
            if not results:
                break

            for course in results:
                title = course.get("title", "")

                if _match_skill(skill_name, title):
                    # Language filter
                    if language:
                        course_locale = course.get("locale", {})
                        if isinstance(course_locale, dict):
                            course_lang = course_locale.get("locale", "")
                        else:
                            course_lang = ""

                        if not course_lang.lower().startswith(language.lower()):
                            continue

                    course_url = course.get("url", "")
                    if not course_url.startswith("http"):
                        course_url = f"https://{SUBDOMAIN}.udemy.com{course_url}"

                    instructors = ", ".join(
                        [i.get("title") for i in course.get("visible_instructors", [])]
                    )

                    return {
                        "title": course.get("title"),
                        "url": course_url,
                        "headline": course.get("headline"),
                        "instructors": instructors
                    }

            if not data.get("next"):
                break
            page += 1

        return {}
    except Exception as e:
        logger.error(f"Error fetching course for {skill_name}: {e}")
        return {}

def get_smart_recommendations(missing_skills: list[str]) -> dict[str, Any]:
    """
    Returns individual course recommendations for each missing skill.
    """
    recommendations: dict[str, Any] = {
        "comprehensive_courses": [],
        "individual_courses": {}
    }

    for skill in missing_skills:
        logger.info(f"Searching Udemy for skill: {skill}")
        course = fetch_single_course(skill)
        if course:
            recommendations["individual_courses"][skill] = course
        else:
            logger.info(f"No course found for skill: {skill}")

        # No sleep to match original script speed
        # time.sleep(0.5)

    return recommendations

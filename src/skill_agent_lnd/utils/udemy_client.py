import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
    "expressjs": "express",  # 'express' with boundary check is safe
    "vuejs": "vue.js",
    "angularjs": "angular",
    "node.js": "node",  # normalize to simple 'node' if needed
    "nodejs": "node.js",
    "mongodb": "mongodb",
}


def _match_skill(query: str, title: str) -> bool:
    """
    Helper to match a skill query against a course title using regex and aliases.
    """
    q_raw = query.lower()
    t = title.lower()

    # 1. Check Aliases
    search_term = SKILL_ALIAS_MAP.get(q_raw, q_raw)

    # SPECIAL EXCLUSION: If searching for "express", exclude "adobe" (Adobe Express)
    if search_term == "express" and "adobe" in t:
        return False

    # 2. Regex Match with Word Boundaries
    try:
        escaped_term = re.escape(search_term)
        pattern = r"\b" + escaped_term + r"\b"
        if re.search(pattern, t):
            return True

        # Special Case: 'js' suffix removal
        if q_raw.endswith("js") and len(q_raw) > 2 and q_raw not in SKILL_ALIAS_MAP:
            base = q_raw[:-2]
            if len(base) > 2:
                pattern_base = r"\b" + re.escape(base) + r"\b"
                if re.search(pattern_base, t):
                    return True

    except Exception:
        pass

    # 3. Fallback: Check original query if different
    if q_raw != search_term:
        if q_raw in t:
            return True

    # 4. Final Fallback: Simple substring match for search term
    if search_term in t:
        return True

    return False


def _create_retry_session() -> requests.Session:
    """Create a requests session with retry logic for 429/5xx errors."""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,  # wait 1s, 2s, 4s...
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_courses_for_skills(skills: List[str], language: str = "en") -> Dict[str, Any]:
    """
    Scans the Udemy organization catalog to find one matching course for each skill in the list.
    
    This uses a single-pass scan of the catalog (up to a limit) to find matches for all 
    skills simultaneously, which is much more efficient than scanning for each skill individually.
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

    # Track which skills we still need to find
    remaining_skills = set(skills)
    found_courses: Dict[str, Any] = {}
    
    session = _create_retry_session()
    
    page = 1
    # Limit scanning to 200 pages (~20,000 courses) to avoid infinite loops
    # This aligns with the logic in final_udemy_coursefetcher.py but for multiple skills
    MAX_PAGES = 200 

    try:
        while page <= MAX_PAGES and remaining_skills:
            if page % 10 == 0:
                logger.info(f"Scanning page {page}... Remaining skills: {remaining_skills}")

            params = {
                "page": page,
                "page_size": 100,  # Maximize page size for speed
                "fields[course]": "id,title,url,headline,visible_instructors,locale",
            }

            response = session.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"Udemy API returned {response.status_code} on page {page}")
                break

            data = response.json()
            results = data.get("results", [])
            
            if not results:
                break

            # Iterate through courses on this page
            for course in results:
                title = course.get("title", "")
                
                # Check against all remaining skills
                skills_found_in_this_course = set()
                for skill in remaining_skills:
                    if _match_skill(skill, title):
                        # Language filter
                        if language:
                            course_locale = course.get("locale", {})
                            if isinstance(course_locale, dict):
                                course_lang = course_locale.get("locale", "")
                            else:
                                course_lang = ""
                            
                            if not course_lang.lower().startswith(language.lower()):
                                continue

                        # Found a match!
                        course_url = course.get("url", "")
                        if not course_url.startswith("http"):
                            course_url = f"https://{SUBDOMAIN}.udemy.com{course_url}"

                        instructors = ", ".join(
                            [i.get("title") for i in course.get("visible_instructors", [])]
                        )

                        found_courses[skill] = {
                            "title": course.get("title"),
                            "url": course_url,
                            "headline": course.get("headline"),
                            "instructors": instructors,
                        }
                        skills_found_in_this_course.add(skill)
                        logger.info(f"Found course for '{skill}': {title}")
                
                # Remove found skills from the search set
                remaining_skills -= skills_found_in_this_course
                if not remaining_skills:
                    break

            if not data.get("next"):
                break
                
            page += 1

    except Exception as e:
        logger.error(f"Error scanning Udemy catalog: {e}")

    return found_courses


def get_smart_recommendations(missing_skills: list[str]) -> dict[str, Any]:
    """
    Returns individual course recommendations for each missing skill.
    """
    logger.info(f"Starting batched search for skills: {missing_skills}")
    
    # Use the single-pass scanner
    found_courses_map = fetch_courses_for_skills(missing_skills)
    
    recommendations: dict[str, Any] = {
        "comprehensive_courses": [],
        "individual_courses": found_courses_map,
    }
    
    # Log what was not found
    for skill in missing_skills:
        if skill not in found_courses_map:
            logger.info(f"No course found for skill: {skill}")

    return recommendations
import requests
import base64
import json
import os


def load_config(config_path="config.json"):
    """Load configuration from JSON file."""
    if not os.path.exists(config_path):
        # Check parent directory if not found in current directory
        # This handles cases where scripts are run from a subdirectory
        parent_config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), config_path
        )
        if os.path.exists(parent_config_path):
            config_path = parent_config_path
        else:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    return config


# Load configuration from file
config = load_config()
ACCOUNT_ID = config.get("account_id")
SUBDOMAIN = config.get("account_name")
CLIENT_ID = config.get("client_id")
CLIENT_SECRET = config.get("client_secret")


def fetch_top_10_courses(skill_name, language="en"):
    """
    Fetches the top 10 courses matching the given skill name and language.

    Args:
        skill_name (str): The skill to search for in course titles
        language (str): Language code to filter by (default: "en"). Set to None for all languages.

    Returns:
        list: List of course dictionaries containing course information
    """
    # Base64 encode credentials
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Accept": "application/json, version=2.0",
    }

    # URL for listing courses for the organization
    url = f"https://{SUBDOMAIN}.udemy.com/api-2.0/organizations/{ACCOUNT_ID}/courses/list/"

    found_courses = []
    page = 1
    page_size = 50
    max_matches = 10

    try:
        while len(found_courses) < max_matches:
            params = {
                "page": page,
                "page_size": page_size,
                "fields[course]": "id,title,url,headline,avg_rating,num_subscribers,visible_instructors,locale",
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                print(f"Error: Status {response.status_code} - {response.text}")
                break

            data = response.json()
            results = data.get("results", [])

            if not results:
                break

            # Filter current page
            for course in results:
                title = course.get("title", "")
                if skill_name.lower() in title.lower():
                    # Check language match if language filter is specified
                    if language:
                        course_locale = course.get("locale", {})
                        course_language = (
                            course_locale.get("locale", "")
                            if isinstance(course_locale, dict)
                            else ""
                        )
                        # Check if course language starts with the requested language (e.g. "en_US" starts with "en")
                        if not course_language.lower().startswith(language.lower()):
                            continue

                    found_courses.append(course)
                    if len(found_courses) >= max_matches:
                        break

            # Check if there is a next page
            if data.get("next") is None:
                break

            page += 1

        return found_courses

    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def fetch_top_course_link(skill_name, language="en"):
    """
    Fetches the link to the first top course matching the given skill name and language.

    Args:
        skill_name (str): The skill to search for in course titles
        language (str): Language code to filter by (default: "en"). Set to None for all languages.

    Returns:
        str: URL link to the top course, or None if no course found
    """
    # Base64 encode credentials
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Accept": "application/json, version=2.0",
    }

    # URL for listing courses for the organization
    url = f"https://{SUBDOMAIN}.udemy.com/api-2.0/organizations/{ACCOUNT_ID}/courses/list/"

    page = 1
    page_size = 50

    try:
        while True:
            params = {
                "page": page,
                "page_size": page_size,
                "fields[course]": "id,title,url,headline,avg_rating,num_subscribers,visible_instructors,locale",
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                print(f"Error: Status {response.status_code} - {response.text}")
                return None

            data = response.json()
            results = data.get("results", [])

            if not results:
                return None

            # Find first matching course
            for course in results:
                title = course.get("title", "")
                if skill_name.lower() in title.lower():
                    # Check language match if language filter is specified
                    if language:
                        course_locale = course.get("locale", {})
                        course_language = (
                            course_locale.get("locale", "")
                            if isinstance(course_locale, dict)
                            else ""
                        )
                        if not course_language.lower().startswith(language.lower()):
                            continue

                    # Construct the course URL
                    course_url = course.get("url", "")
                    if course_url:
                        # Full URL format for Udemy Business
                        if course_url.startswith("http"):
                            full_url = course_url
                        else:
                            full_url = f"https://{SUBDOMAIN}.udemy.com{course_url}"
                        return full_url
                    else:
                        # Fallback: use course ID
                        course_id = course.get("id", "")
                        return f"https://{SUBDOMAIN}.udemy.com/course/{course_id}/"

            # Check if there is a next page
            if data.get("next") is None:
                return None

            page += 1

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

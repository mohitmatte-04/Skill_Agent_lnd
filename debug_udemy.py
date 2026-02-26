import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from skill_agent_lnd.utils.udemy_client import get_smart_recommendations

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("skill_agent_lnd.utils.udemy_client")
logger.setLevel(logging.INFO)

# Add src to path
sys.path.append(str(Path.cwd() / "src"))

# Load env vars
load_dotenv()


def debug_batch_search(skills):
    print(f"\n--- Batch Search Test for: {skills} ---")
    start_time = time.time()

    # Use the main entry point function
    result = get_smart_recommendations(skills)

    end_time = time.time()

    print("\nResults:")
    found = result.get("individual_courses", {})
    for skill in skills:
        if skill in found:
            print(f"✅ {skill}: {found[skill]['title']}")
        else:
            print(f"❌ {skill}: Not found")

    print(f"\nTime taken: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    debug_batch_search(["nextjs", "expressjs", "mongodb", "react"])

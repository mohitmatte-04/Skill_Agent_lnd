import sys
import os
from pathlib import Path

# Add src to python path so we can import the package
sys.path.append(str(Path("src").resolve()))

try:
    from skill_agent_lnd.agent import root_agent
    print(f"Successfully imported root_agent: {root_agent.name}")
except Exception as e:
    print(f"Failed to import root_agent: {e}")
    import traceback
    traceback.print_exc()

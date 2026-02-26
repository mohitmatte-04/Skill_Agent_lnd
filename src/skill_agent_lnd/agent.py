"""Top level agent for data agent (BigQuery only)."""

import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Any, cast

import yaml
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_agent_dir = Path(__file__).parent


def load_config() -> None:
    yaml_file = _agent_dir / "agent_settings.yaml"

    # 1. Load .env (Backward Compatibility)
    if load_dotenv():
        logger.info("✅ Loaded .env file")

    # 2. Load YAML (New Config Format)
    if yaml_file.exists():
        try:
            with yaml_file.open("r") as f:
                yaml_config = yaml.safe_load(f)
            if yaml_config and isinstance(yaml_config, dict):
                for key, value in yaml_config.items():
                    os.environ[str(key)] = str(value)
                logger.info(f"✅ Loaded YAML config from {yaml_file}")
        except Exception as e:
            logger.error(f"❌ Failed to load YAML config from {yaml_file}: {e}")


load_config()

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.agents.callback_context import CallbackContext  # noqa: E402
from google.genai import types  # noqa: E402

from .prompts import return_instructions_root  # noqa: E402
from .sub_agents.bigquery.tools import (  # noqa: E402
    get_database_settings as get_bq_database_settings,
)
from .tools import call_bigquery_agent, search_udemy_courses  # noqa: E402

# Set up logging
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

# Initialize module-level config variables
_dataset_config: dict[str, Any] = {}
_database_settings: dict[str, Any] = {}
_supported_dataset_types = ["bigquery"]  # BigQuery only
_required_dataset_config_params = ["name", "description"]


def load_dataset_config() -> dict[str, Any]:
    """Load the dataset configurations for the agent from the config file"""

    # Default to bigquery_only_dataset_config.json if not set
    dataset_config_str = os.getenv(
        "DATASET_CONFIG_FILE", "bigquery_only_dataset_config.json"
    )
    dataset_config_path = Path(dataset_config_str)

    if not dataset_config_path.is_absolute():
        dataset_config_path = _agent_dir / dataset_config_path
        _logger.info(f"Resolved dataset config path to: {dataset_config_path}")

    with dataset_config_path.open("r", encoding="utf-8") as f:
        dataset_config = cast(dict[str, Any], json.load(f))

    if "datasets" not in dataset_config:
        _logger.fatal("No 'datasets' entry in dataset config")

    for dataset in dataset_config["datasets"]:
        if "type" not in dataset:
            _logger.fatal("Missing dataset type")
        if dataset["type"] not in _supported_dataset_types:
            _logger.fatal("Dataset type '%s' not supported", dataset["type"])

        for p in _required_dataset_config_params:
            if p not in dataset:
                _logger.fatal(
                    "Missing required param '%s' from %s dataset config",
                    p,
                    dataset["type"],
                )

    return dataset_config


def get_database_settings(db_type: str) -> dict[str, Any]:
    """Wrapper function to get database settings by type"""
    if db_type not in _supported_dataset_types:
        raise ValueError(f"Unsupported database type: {db_type}")
    if db_type == "bigquery":
        return get_bq_database_settings()
    raise ValueError(f"Unsupported database type: {db_type}")


def init_database_settings(dataset_config: dict[str, Any]) -> dict[str, Any]:
    """Initializes the database settings for the configured datasets"""
    db_settings = {}
    for dataset in dataset_config["datasets"]:
        db_settings[dataset["type"]] = get_database_settings(dataset["type"])
    return db_settings


def get_dataset_definitions_for_instructions() -> str:
    """Returns the dataset definitions instructions block"""

    dataset_definitions = """
<DATASETS>
"""
    for dataset in _dataset_config["datasets"]:
        dataset_type = dataset["type"]
        dataset_definitions += f"""
<{dataset_type.upper()}>
<DESCRIPTION>
{dataset["description"]}
</DESCRIPTION>
<SCHEMA>
--------- The schema of the relevant database with a few sample rows. --------
{_database_settings[dataset_type]["schema"]}
</SCHEMA>
</{dataset_type.upper()}>

"""
    dataset_definitions += """
</DATASETS>
"""

    if "cross_dataset_relations" in _dataset_config:
        dataset_definitions += f"""
<CROSS_DATASET_RELATIONS>
--------- The cross dataset relations between the configured datasets. ---------
{_dataset_config["cross_dataset_relations"]}
</CROSS_DATASET_RELATIONS>
"""

    return dataset_definitions


def load_database_settings_in_context(callback_context: CallbackContext) -> None:
    """Load database settings into the callback context on first use."""
    if "database_settings" not in callback_context.state:
        callback_context.state["database_settings"] = _database_settings


def get_root_agent() -> LlmAgent:
    tools: list[Any] = []

    for dataset in _dataset_config["datasets"]:
        if dataset["type"] == "bigquery":
            tools.append(call_bigquery_agent)

    # Add Udemy search tool
    tools.append(search_udemy_courses)

    agent = LlmAgent(
        model=os.getenv("ROOT_AGENT_MODEL", "gemini-2.5-flash"),
        name="bigquery_root_agent",
        instruction=return_instructions_root()
        + get_dataset_definitions_for_instructions(),
        global_instruction=(
            f"""
            You are a BigQuery Data Agent.
            Todays date: {date.today()}
            """
        ),
        tools=tools,
        before_agent_callback=load_database_settings_in_context,
        generate_content_config=types.GenerateContentConfig(temperature=0.01),
    )

    return agent


# Initialize dataset configurations and database info before the agent starts
_dataset_config = load_dataset_config()
print("loading dataset settings")
_database_settings = init_database_settings(_dataset_config)
print("loaded db settings")


# Fetch the root agent
root_agent = get_root_agent()

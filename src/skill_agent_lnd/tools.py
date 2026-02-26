"""Custom tools for the LLM agent."""

import logging
from typing import Any

from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from .sub_agents.bigquery.agent import bigquery_agent

logger = logging.getLogger(__name__)


async def call_bigquery_agent(
    question: str,
    tool_context: ToolContext,
) -> Any:
    """Tool to call bigquery database (nl2sql) agent.

    Args:
        question: The natural language question to ask the database.
        tool_context: The tool context.

    Returns:
        The result from the BigQuery agent.
    """
    logger.debug("call_bigquery_agent: %s", question)

    agent_tool = AgentTool(agent=bigquery_agent)

    bigquery_agent_output = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    # Store output in state for potential downstream use
    tool_context.state["bigquery_agent_output"] = bigquery_agent_output
    return bigquery_agent_output


async def search_udemy_courses(
    missing_skills: list[str],
    tool_context: ToolContext,
) -> dict:
    """Tool to search Udemy for courses covering the missing skills.

    This tool intelligently searches for both comprehensive courses covering
    multiple skills and individual courses for specific gaps.

    Args:
        missing_skills: List of skill names identified as gaps (e.g., ["React", "Node.js"]).
        tool_context: The tool context.

    Returns:
        A dictionary containing:
        - "comprehensive_courses": List of courses covering multiple skills.
        - "individual_courses": Dictionary mapping each skill to a specific course.
    """
    from .utils.udemy_client import get_smart_recommendations

    logger.info(f"Searching Udemy for missing skills: {missing_skills}")
    
    try:
        recommendations = get_smart_recommendations(missing_skills)
        return recommendations
    except Exception as e:
        logger.error(f"Error fetching Udemy recommendations: {e}")
        return {"error": "Failed to fetch course recommendations."}
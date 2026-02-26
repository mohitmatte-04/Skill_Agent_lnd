"""Unit tests for custom tools."""

from unittest.mock import patch

import pytest

from skill_agent_lnd.tools import call_bigquery_agent, search_udemy_courses


class TestSearchUdemyCourses:
    """Tests for the search_udemy_courses function."""

    @pytest.mark.asyncio
    @patch("skill_agent_lnd.utils.udemy_client.get_smart_recommendations")
    async def test_search_udemy_courses_success(
        self, mock_get_recs, mock_tool_context
    ) -> None:
        """Test that search_udemy_courses returns recommendations."""
        mock_get_recs.return_value = {"status": "success", "courses": []}

        result = await search_udemy_courses(["Python"], mock_tool_context)

        assert result["status"] == "success"
        mock_get_recs.assert_called_once_with(["Python"])

    @pytest.mark.asyncio
    @patch("skill_agent_lnd.utils.udemy_client.get_smart_recommendations")
    async def test_search_udemy_courses_error(
        self, mock_get_recs, mock_tool_context
    ) -> None:
        """Test that search_udemy_courses handles exceptions."""
        mock_get_recs.side_effect = Exception("API error")

        result = await search_udemy_courses(["Python"], mock_tool_context)

        assert "error" in result
        assert result["error"] == "Failed to fetch course recommendations."


class TestCallBigqueryAgent:
    """Tests for the call_bigquery_agent function."""

    @pytest.mark.asyncio
    @patch("google.adk.tools.agent_tool.AgentTool.run_async")
    async def test_call_bigquery_agent_success(
        self, mock_run_async, mock_tool_context
    ) -> None:
        """Test that call_bigquery_agent returns result from sub-agent."""
        mock_run_async.return_value = {"data": "bq result"}

        result = await call_bigquery_agent("What is the data?", mock_tool_context)

        assert result == {"data": "bq result"}
        assert mock_tool_context.state["bigquery_agent_output"] == {"data": "bq result"}

"""Integration tests for agent configuration and component wiring.

This module validates the basic structure and wiring of ADK app components.
Tests are pattern-based and validate integration points regardless of specific
implementation choices (plugins, tools, etc.).

Future: Container-based smoke tests for CI/CD will be added here.
"""

from skill_agent_lnd.agent import root_agent


class TestAgentIntegration:
    """Pattern-based integration tests for Agent configuration."""

    def test_agent_has_required_configuration(self) -> None:
        """Verify agent has required configuration fields."""
        agent = root_agent

        # Required: agent name
        assert agent.name is not None
        assert isinstance(agent.name, str)
        assert len(agent.name) > 0

        # Required: agent model
        assert agent.model is not None
        assert isinstance(agent.model, str)
        assert len(agent.model) > 0

    def test_agent_instructions_are_valid_if_configured(self) -> None:
        """Verify agent instructions (if configured) are valid strings."""
        agent = root_agent

        # Instruction is optional - if configured, should be non-empty string
        if agent.instruction is not None:
            assert isinstance(agent.instruction, str)
            assert len(agent.instruction) > 0

    def test_agent_tools_are_valid_if_configured(self) -> None:
        """Verify agent tools (if any) are properly initialized."""
        agent = root_agent

        # Tools are optional - if configured, should be a list
        if agent.tools is not None:
            assert isinstance(agent.tools, list)
            # Each tool should be an object instance
            for tool in agent.tools:
                assert tool is not None
                assert callable(tool) or hasattr(tool, "name")

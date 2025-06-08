"""Agent for managing Home Assistant areas."""

import logging

from google.adk.agents import LlmAgent

from homeassistant.core import HomeAssistant

from custom_components.rulebook.interaction_layer import (
    async_get_areas,
    async_create_area,
)
from custom_components.rulebook.storage import async_read_parsed_rulebook
from custom_components.rulebook.types import RulebookConfigEntry
from custom_components.rulebook.data.home import ParsedHomeDetails


from .const import AGENT_MODEL

_LOGGER = logging.getLogger(__name__)


def async_create_agent(
    hass: HomeAssistant, config_entry: RulebookConfigEntry
) -> LlmAgent:
    """Create an Area agent.

    Args:
        hass: The Home Assistant instance.
        config_entry: The configuration entry for the rulebook.

    Returns:
        An LlmAgent instance for managing areas.
    """

    async def get_areas_tool() -> list[dict[str, str | None]]:
        """Fetches all defined areas in Home Assistant.

        Returns:
            A list of dictionaries, where each dictionary represents an area
            and contains its 'name' and 'id'.
        """
        return await async_get_areas(hass)

    async def get_rulebook_areas_tool() -> list[str] | None:
        """Fetches area mentions from the parsed rulebook.

        Returns:
            A list of area names mentioned in the rulebook, or None if not found.
        """
        parsed_rulebook: ParsedHomeDetails | None = await async_read_parsed_rulebook(
            hass, config_entry.entry_id
        )
        if parsed_rulebook and parsed_rulebook.area_mentions:
            return parsed_rulebook.area_mentions
        return None

    async def create_home_assistant_area_tool_func(
        area_name: str,
    ) -> dict[str, str | None] | None:
        """Creates a new area in Home Assistant.

        Args:
            area_name: The name of the area to create.

        Returns:
            A dictionary with 'name' and 'id' of the created area, or None if creation failed.
        """
        return await async_create_area(hass, area_name)

    return LlmAgent(
        name="AreaManager",
        model=AGENT_MODEL,
        description=(
            "Manages and answers questions about Home Assistant areas. "
            "Can list existing areas, compare them with the rulebook, and identify discrepancies."
        ),
        instruction=(
            "You are an expert in Home Assistant areas and the user's rulebook. "
            "Your goal is to help the user align their Home Assistant areas with their rulebook. "
            "When asked about areas, or to check area configurations: "
            "1. Use the 'get_areas_tool' tool to fetch current area information from Home Assistant. "
            "2. Use the 'get_rulebook_areas_tool' tool to fetch area names mentioned in the rulebook. "
            "3. Compare these two lists of areas. "
            "4. Report any discrepancies to the user. Specifically, tell them: "
            "   - Which areas are mentioned in the rulebook but NOT defined in Home Assistant. "
            "   - Which areas are defined in Home Assistant but NOT mentioned in the rulebook. "
            "5. For areas mentioned in the rulebook but not in Home Assistant, you can offer to create them using the 'create_home_assistant_area_tool_func' tool. Ask for confirmation before creating an area. "
            "Present this information clearly. If there are no discrepancies, inform the user that the areas are aligned."
        ),
        tools=[
            get_areas_tool,
            get_rulebook_areas_tool,
            create_home_assistant_area_tool_func,
        ],
    )

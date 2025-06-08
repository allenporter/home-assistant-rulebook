"""Agent for managing Home Assistant persons."""

import logging

from google.adk.agents import LlmAgent

from homeassistant.core import HomeAssistant

from custom_components.rulebook.interaction_layer import (
    async_get_persons,
    async_guide_user_to_create_person,
)
from custom_components.rulebook.storage import async_read_parsed_rulebook
from custom_components.rulebook.types import RulebookConfigEntry
from custom_components.rulebook.data.home import (
    ParsedHomeDetails,
)

from .const import AGENT_MODEL

_LOGGER = logging.getLogger(__name__)


def async_create_agent(
    hass: HomeAssistant, config_entry: RulebookConfigEntry
) -> LlmAgent:
    """Create a Person agent.

    Args:
        hass: The Home Assistant instance.
        config_entry: The configuration entry for the rulebook.

    Returns:
        An LlmAgent instance for managing persons.
    """

    async def get_persons_tool() -> list[dict[str, str | None]]:
        """Fetches all defined persons in Home Assistant.

        Returns:
            A list of dictionaries, where each dictionary represents a person
            and contains their 'name' and 'id' (entity_id).
        """
        return await async_get_persons(hass)

    async def get_rulebook_persons_tool() -> list[str] | None:
        """Fetches person mentions from the parsed rulebook.

        Returns:
            A list of person names mentioned in the rulebook, or None if not found.
        """
        parsed_rulebook: ParsedHomeDetails | None = await async_read_parsed_rulebook(
            hass, config_entry.entry_id
        )
        if parsed_rulebook and parsed_rulebook.key_people:
            return parsed_rulebook.key_people
        _LOGGER.debug("No key people found in parsed rulebook or rulebook not found.")
        return None

    async def create_person_guidance_tool_func(person_name: str) -> dict[str, str]:
        """Creates a persistent notification to guide the user to add a person.

        Args:
            person_name: The name of the person for whom to create the notification.

        Returns:
            A dictionary indicating the result of the operation.
        """
        _LOGGER.debug("Tool called to guide creation of person: %s", person_name)
        return await async_guide_user_to_create_person(hass, person_name)

    return LlmAgent(
        name="PersonManager",
        model=AGENT_MODEL,
        description=(
            "Manages and answers questions about Home Assistant persons. "
            "Can list existing persons, compare them with the rulebook, and identify discrepancies."
        ),
        instruction=(
            "You are an expert in Home Assistant persons and the user's rulebook. "
            "Your goal is to help the user align their Home Assistant persons with their rulebook. "
            "When asked about persons, or to check person configurations: "
            "1. Use the 'get_persons_tool' tool to fetch current person information from Home Assistant. "
            "2. Use the 'get_rulebook_persons_tool' tool to fetch person names mentioned in the rulebook. "
            "3. Compare these two lists of persons. "
            "4. Report any discrepancies to the user. Specifically, tell them: "
            "   - Which persons are mentioned in the rulebook but NOT defined in Home Assistant. "
            "   - Which persons are defined in Home Assistant but NOT mentioned in the rulebook. "
            "5. For persons mentioned in the rulebook but not in Home Assistant, ask the user if they would like guidance on how to add them. If they confirm, use the 'create_person_guidance_tool_func' to create a notification. "
            "6. For persons defined in Home Assistant but not in the rulebook, suggest adding them to the rulebook. "
            "Present this information clearly. If there are no discrepancies, inform the user that the persons are aligned."
        ),
        tools=[
            get_persons_tool,
            get_rulebook_persons_tool,
            create_person_guidance_tool_func,  # Added tool
        ],
    )

"""Agent for parsing the user's rulebook."""

import logging
from typing import Any, Optional

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from homeassistant.core import HomeAssistant

from custom_components.rulebook.const import CONF_RULEBOOK
from custom_components.rulebook.types import RulebookConfigEntry
from custom_components.rulebook.data.home import LocationDetails, ParsedHomeDetails, BasicInfo
from custom_components.rulebook.storage import (
    async_read_parsed_rulebook,
    async_write_parsed_rulebook,
)

from .const import SUMMARIZE_MODEL, PARSED_RULEBOOK_KEY

_LOGGER = logging.getLogger(__name__)


_INSTRUCTION_FORMAT = (
    "You are an expert at parsing free-form text rulebooks for smart homes. "
    "Your primary task is to understand and structure the entire rulebook provided in the prompt. "
    "Analyze the rulebook text to identify: "
    "1. Global/Basic Information (home name, location details, key people, default language). "
    "2. Areas and their structure (rooms, zones, associated devices, sub-areas). "
    "3. Utility Providers (electricity, gas, internet, water with names and service types). "
    "Your information will later be used to create Smart Home Rules independently, but you are not responsible for that. "
    "You MUST respond with a single, comprehensive JSON object that strictly conforms to the 'ParsedHomeDetails' schema. "
    "The schema defines keys like 'raw_text', 'parsed_status', 'basic_info', 'floors', 'areas', 'utility_providers'. "
    "Ensure all parts of the rulebook are mapped to the appropriate fields in this schema. "
    "If a section of the rulebook is unclear or missing, use null or empty lists/objects for the corresponding schema fields where appropriate, "
    "but always return a valid JSON object matching the schema structure."
    "\n\n"
    "The user's rulebook is as follows:\n\n"
    "{rulebook_text}\n\n"
)


class RulebookTools:
    """Tool for working with the parsed rulebook."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the tool."""
        self._hass = hass

    async def update_basic_info(
        self, home_name: Optional[str], default_language: Optional[str]
    ) -> dict[str, Any]:
        """Tool to update basic information about the home.

        Args:
            home_name: The name of the smart home. Can be null.
            default_language: The default language for interactions. Can be null.

        Returns:
            A message indicating the outcome of the operation.
        """
        try:
            parsed_rulebook = await async_read_parsed_rulebook(self._hass)
            if not parsed_rulebook:
                parsed_rulebook = ParsedHomeDetails(
                    raw_text="Initial rulebook created by tool.",
                    parsed_status="created_by_tool",
                    basic_info=BasicInfo(home_name=home_name, default_language=default_language),
                )
            else:
                # Ensure basic_info is initialized
                if parsed_rulebook.basic_info is None:
                    parsed_rulebook.basic_info = BasicInfo()

                # Now we can safely access attributes
                if home_name is not None:
                    parsed_rulebook.basic_info.home_name = home_name
                if default_language is not None:
                    parsed_rulebook.basic_info.default_language = default_language

            await async_write_parsed_rulebook(self._hass, parsed_rulebook)
            current_basic_info = parsed_rulebook.basic_info
            return {
                "status": "success",
                "message": "Basic information updated successfully.",
                "basic_info": current_basic_info.model_dump() if current_basic_info else None,
            }
        except Exception as e:
            _LOGGER.error("Failed to update basic information: %s", e)
            return {"status": "error", "message": f"Error persisting rulebook: {e}"}

    async def update_location_details(
        self,
        description: Optional[str],
        address: Optional[str],
        city: Optional[str],
        state: Optional[str],
        country: Optional[str],
        timezone: Optional[str],
    ) -> dict[str, Any]:
        """Tool to update location details of the home.

        Args:
            description: Optional description of the home\'s location. Can be null.
            address: Street address of the home. Can be null.
            city: City where the home is located. Can be null.
            state: State or province where the home is located. Can be null.
            country: Country where the home is located. Can be null.
            timezone: Timezone of the home. Can be null.

        Returns:
            A message indicating the outcome of the operation.
        """
        try:
            parsed_rulebook = await async_read_parsed_rulebook(self._hass)
            if not parsed_rulebook:
                parsed_rulebook = ParsedHomeDetails(
                    raw_text="Initial rulebook created by tool.",
                    parsed_status="created_by_tool",
                    location_details=LocationDetails(description=description, address=address, city=city, state=state, country=country, timezone=timezone)
                )
            else:
                # Ensure location_details is initialized
                if parsed_rulebook.location_details is None:
                    parsed_rulebook.location_details = LocationDetails()

                # Now we can safely access attributes
                if description is not None:
                    parsed_rulebook.location_details.description = description
                if address is not None:
                    parsed_rulebook.location_details.address = address
                if city is not None:
                    parsed_rulebook.location_details.city = city
                if state is not None:
                    parsed_rulebook.location_details.state = state
                if country is not None:
                    parsed_rulebook.location_details.country = country
                if timezone is not None:
                    parsed_rulebook.location_details.timezone = timezone

            await async_write_parsed_rulebook(self._hass, parsed_rulebook)
            current_location_details = parsed_rulebook.location_details
            return {
                "status": "success",
                "message": "Location details updated successfully.",
                "location_details": current_location_details.model_dump() if current_location_details else None,
            }
        except Exception as e:
            _LOGGER.error("Failed to update location details: %s", e)
            return {
                "status": "error",
                "message": f"Error updating location details: {e}",
            }

    async def add_key_person(self, person_name: str) -> dict[str, Any]:
        """Tool to add a key person to the home.

        Args:
            person_name: The name of the person to add.

        Returns:
            A message indicating the outcome of the operation.
        """
        try:
            parsed_rulebook = await async_read_parsed_rulebook(self._hass)
            if not parsed_rulebook:
                parsed_rulebook = ParsedHomeDetails(
                    raw_text="Initial rulebook created by tool.",
                    parsed_status="created_by_tool",
                    key_people=[person_name] # Initialize with the person
                )
            else:
                # Ensure key_people is initialized
                if parsed_rulebook.key_people is None:
                    parsed_rulebook.key_people = []

                if person_name not in parsed_rulebook.key_people:
                    parsed_rulebook.key_people.append(person_name)
                else:
                    return {
                        "status": "info",
                        "message": f"Person '{person_name}' already exists.",
                        "key_people": parsed_rulebook.key_people,
                    }

            await async_write_parsed_rulebook(self._hass, parsed_rulebook)
            return {
                "status": "success",
                "message": f"Person '{person_name}' added successfully.",
                "key_people": parsed_rulebook.key_people,
            }
        except Exception as e:
            _LOGGER.error("Failed to add key person: %s", e)
            return {"status": "error", "message": f"Error adding key person: {e}"}

    async def remove_key_person(self, person_name: str) -> dict[str, Any]:
        """Tool to remove a key person from the home.

        Args:
            person_name: The name of the person to remove.

        Returns:
            A message indicating the outcome of the operation.
        """
        try:
            parsed_rulebook = await async_read_parsed_rulebook(self._hass)
            if not parsed_rulebook or parsed_rulebook.key_people is None:
                return {
                    "status": "info",
                    "message": "No key people to remove from or rulebook not found.",
                    "key_people": [],
                }
            # key_people is now guaranteed to be a list
            if person_name in parsed_rulebook.key_people:
                parsed_rulebook.key_people.remove(person_name)
                await async_write_parsed_rulebook(self._hass, parsed_rulebook)
                return {
                    "status": "success",
                    "message": f"Person '{person_name}' removed successfully.",
                    "key_people": parsed_rulebook.key_people,
                }
            else:
                return {
                    "status": "info",
                    "message": f"Person '{person_name}' not found.",
                    "key_people": parsed_rulebook.key_people,
                }
        except Exception as e:
            _LOGGER.error("Failed to remove key person: %s", e)
            return {"status": "error", "message": f"Error removing key person: {e}"}

    async def get_parsed_rulebook(self) -> dict[str, Any] | str:
        """Tool to retrieve the parsed rulebook.

        Retrieves the previously parsed and persisted structured representation of the user\'s rulebook.
        Returns the parsed rulebook data as a dict or an indication if it\'s not found."

        Returns:
            The ParsedHomeDetails object as a dict or a string message if not found/error.
        """
        try:
            parsed_rulebook = await async_read_parsed_rulebook(self._hass)
            if parsed_rulebook:
                return parsed_rulebook.model_dump()
            return "Parsed rulebook not found."
        except Exception as e:
            _LOGGER.error("Failed to retrieve rulebook: %s", e)
            return f"Error retrieving rulebook: {e}"


def async_create_agent(
    hass: HomeAssistant, config_entry: RulebookConfigEntry
) -> LlmAgent:
    """Create and return an instance of the RulebookParserAgent."""
    rulebook_text = config_entry.options[CONF_RULEBOOK]

    tools = RulebookTools(hass)

    return LlmAgent(
        name="RulebookParserAgent",
        model=SUMMARIZE_MODEL,
        description="Parses user rulebooks into structured JSON format and can update specific sections.",
        instruction=_INSTRUCTION_FORMAT.format(rulebook_text=rulebook_text),
        tools=[
            FunctionTool(tools.update_basic_info),
            FunctionTool(tools.update_location_details),
            FunctionTool(tools.add_key_person),
            FunctionTool(tools.remove_key_person),
            FunctionTool(tools.get_parsed_rulebook),
        ],
        disallow_transfer_to_peers=True,
    )

"""Agent for managing Home Assistant location configuration based on the rulebook."""

import logging
from typing import Any, Optional

from custom_components.rulebook.data.home import ParsedHomeDetails
from custom_components.rulebook.interaction_layer import (
    async_get_ha_location_config,
    async_set_ha_location_config,
)
from custom_components.rulebook.storage import async_read_parsed_rulebook
from custom_components.rulebook.types import RulebookConfigEntry
from google.adk.agents import LlmAgent
from homeassistant.core import HomeAssistant

from .const import SUMMARIZE_MODEL

_LOGGER = logging.getLogger(__name__)

_AGENT_NAME = "LocationManager"
_AGENT_DESCRIPTION = (
    "Manages Home Assistant's location configuration based on the rulebook. "
    "It compares the location details (latitude, longitude, location name, "
    "time zone, and unit system) specified in the rulebook with the current "
    "Home Assistant settings. If discrepancies are found, it directly updates "
    "Home Assistant's configuration to match the rulebook."
)

_BASE_INSTRUCTIONS = (
    "Your role is to ensure Home Assistant's location settings align with the "
    "details provided in the user's rulebook. "
    "1. First, use the 'get_rulebook_location_details_tool' to retrieve the location details "
    "from the rulebook. This includes latitude, longitude, location name, timezone, and unit system. "
    "2. Next, use the 'get_ha_location_config_tool' to fetch the current Home Assistant "
    "location configuration. "
    "3. Compare these two sets of information. Pay close attention to latitude, "
    "longitude, location_name, time_zone, and unit_system_metric. "
    "4. If you find any significant discrepancies, you MUST use the "
    "'set_ha_location_config_tool' to update Home Assistant's "
    "configuration to match the values from the rulebook. Provide all available "
    "rulebook location parameters to this tool. "
    "5. If the rulebook does not contain specific location details (e.g., latitude "
    "and longitude are not set), or if the details already perfectly match Home Assistant's "
    "configuration, then no action is needed. Simply report that the location "
    "is consistent or not specified sufficiently in the rulebook for an update."
    "Do not ask the user for confirmation before updating; proceed with the update if discrepancies are found."
)


def async_create_agent(
    hass: HomeAssistant, config_entry: RulebookConfigEntry
) -> LlmAgent:
    """Create a Location agent.

    Args:
        hass: The Home Assistant instance.
        config_entry: The configuration entry for the rulebook.

    Returns:
        An LlmAgent instance for managing location.
    """

    async def get_ha_location_config_tool() -> dict[str, Any]:
        """Fetches the current location configuration from Home Assistant, including latitude, longitude, elevation, location name, time zone, and unit system."""
        _LOGGER.debug("LocationAgent: Called get_ha_location_config_tool")
        return await async_get_ha_location_config(hass)

    async def get_rulebook_location_details_tool() -> dict[str, Any] | None:
        """Retrieves the location details (latitude, longitude, location name, timezone, unit system) as parsed from the rulebook."""
        _LOGGER.debug("LocationAgent: Called get_rulebook_location_details_tool")
        parsed_home_details: (
            ParsedHomeDetails | None
        ) = await async_read_parsed_rulebook(hass, config_entry.entry_id)
        if parsed_home_details and parsed_home_details.location_details:
            return parsed_home_details.location_details.model_dump(exclude_none=True)
        _LOGGER.debug("LocationAgent: No rulebook location details found")
        return None

    async def set_ha_location_config_tool(
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        elevation: Optional[int] = None,
        location_name: Optional[str] = None,
        time_zone: Optional[str] = None,
        unit_system_metric: Optional[bool] = None,
        currency: Optional[str] = None,
        country: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict[str, str]:
        """Updates Home Assistant's core location configuration with the provided parameters. All parameters are optional; only provided ones will be updated."""
        _LOGGER.debug(
            "LocationAgent: Called set_ha_location_config_tool with params: lat=%s, lon=%s, elev=%s, name=%s, tz=%s, metric=%s, currency=%s, country=%s, lang=%s",
            latitude,
            longitude,
            elevation,
            location_name,
            time_zone,
            unit_system_metric,
            currency,
            country,
            language,
        )
        return await async_set_ha_location_config(
            hass,
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
            location_name=location_name,
            time_zone=time_zone,
            unit_system_metric=unit_system_metric,
            currency=currency,
            country=country,
            language=language,
        )

    return LlmAgent(
        name=_AGENT_NAME,
        model=SUMMARIZE_MODEL,
        description=_AGENT_DESCRIPTION,
        instruction=_BASE_INSTRUCTIONS,
        tools=[
            get_ha_location_config_tool,
            get_rulebook_location_details_tool,
            set_ha_location_config_tool,
        ],
    )

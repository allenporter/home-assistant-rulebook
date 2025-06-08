"""Module for interacting with the Home Assistant instance."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar

_LOGGER = logging.getLogger(__name__)


async def async_get_areas(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Fetch all defined areas from the Area Registry.

    Args:
        hass: The Home Assistant instance.

    Returns:
        A list of dictionaries, where each dictionary represents an area
        and contains its 'name' and 'id'.
    """
    area_reg = ar.async_get(hass)
    areas = [{"name": area.name, "id": area.id} for area in area_reg.async_list_areas()]
    _LOGGER.debug("Fetched %s areas: %s", len(areas), areas)
    return areas


async def async_create_area(
    hass: HomeAssistant, area_name: str
) -> dict[str, str | None] | None:
    """Create a new area in Home Assistant.

    Args:
        hass: The Home Assistant instance.
        area_name: The name for the new area.

    Returns:
        A dictionary containing the new area's 'name' and 'id' if successful,
        otherwise None.
    """
    area_reg = ar.async_get(hass)
    try:
        area_entry = area_reg.async_create(area_name)
    except ValueError as err:
        _LOGGER.error("Failed to create area: '%s': %s", area_name, err)
        return {
            "status": "error",
            "error_message": f"Failed to create area: '{area_name}': {err}",
        }

    _LOGGER.info(
        "Successfully created area: %s (ID: %s)", area_entry.name, area_entry.id
    )
    return {"name": area_entry.name, "id": area_entry.id}

"""Module for interacting with the Home Assistant instance."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant, State
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


async def async_get_persons(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Fetch all defined persons from Home Assistant.

    Args:
        hass: The Home Assistant instance.

    Returns:
        A list of dictionaries, where each dictionary represents a person
        and contains their 'name' and 'id' (entity_id).
    """
    person_states: list[State] = hass.states.async_all("person")
    persons = [{"name": state.name, "id": state.entity_id} for state in person_states]
    _LOGGER.debug("Fetched %s persons: %s", len(persons), persons)
    return persons


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


async def async_guide_user_to_create_person(
    hass: HomeAssistant, person_name: str
) -> dict[str, str]:
    """Create a persistent notification to guide the user to add a person.

    Args:
        hass: The Home Assistant instance.
        person_name: The name of the person to guide the user to add.

    Returns:
        A dictionary indicating the status of the notification creation.
    """
    title = f"Add Person: {person_name}"
    message = (
        f"The rulebook mentions '{person_name}', but this person is not yet set up "
        f"in Home Assistant. Please go to Settings > People > Add Person to add them."
    )
    notification_id = f"rulebook_add_person_{person_name.lower().replace(' ', '_')}"

    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": title,
            "message": message,
            "notification_id": notification_id,
        },
        blocking=True,
    )
    _LOGGER.info(
        "Created persistent notification to guide adding person: %s", person_name
    )
    return {"status": "success", "person_name": person_name}

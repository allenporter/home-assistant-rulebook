"""Module for interacting with the Home Assistant instance."""

import logging
from typing import Any

from homeassistant.const import (
    CONF_UNIT_SYSTEM_IMPERIAL,
    CONF_UNIT_SYSTEM_METRIC,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar
from homeassistant.util import unit_system

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


async def async_guide_user_to_create_person(
    hass: HomeAssistant, person_name: str
) -> dict[str, str]:
    """Create a persistent notification to guide the user to add a person.

    Args:
        hass: The Home Assistant instance.
        person_name: The name of the person to guide adding.

    Returns:
        A dictionary indicating the status of the notification creation.
    """
    title = f"Add Person: {person_name}"
    message = (
        f"The rulebook mentions a person named '{person_name}' who is not yet "
        "defined in Home Assistant. To add this person, please go to "
        "Settings > People, and click on 'Add Person'."
    )
    # Create a unique notification ID to prevent duplicates if called multiple times
    # for the same person before the user acts on it.
    notification_id = f"rulebook_add_person_{person_name.lower().replace(' ', '_')}"

    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": title,
            "message": message,
            "notification_id": notification_id,
        },
        blocking=True,  # Ensures the notification is created before proceeding
    )
    _LOGGER.info(
        "Created persistent notification to guide adding person: %s", person_name
    )
    return {"status": "success", "person_name": person_name}


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


async def async_get_ha_location_config(hass: HomeAssistant) -> dict[str, Any]:
    """Fetch Home Assistant's core location configuration.

    Args:
        hass: The Home Assistant instance.

    Returns:
        A dictionary containing location details like latitude, longitude,
        elevation, location_name, time_zone, and unit_system.
    """
    config = hass.config
    location_config = {
        "latitude": config.latitude,
        "longitude": config.longitude,
        "elevation": config.elevation,
        "location_name": config.location_name,
        "time_zone": config.time_zone,
        "unit_system_metric": (config.units is unit_system.METRIC_SYSTEM),
        "currency": config.currency,
        "country": config.country,
        "language": config.language,
    }
    _LOGGER.debug("Fetched HA location config: %s", location_config)
    return location_config


async def async_set_ha_location_config(
    hass: HomeAssistant,
    latitude: float | None = None,
    longitude: float | None = None,
    elevation: int | None = None,
    location_name: str | None = None,
    time_zone: str | None = None,
    unit_system_metric: bool | None = None,
    currency: str | None = None,
    country: str | None = None,
    language: str | None = None,
) -> dict[str, str]:
    """Update Home Assistant's core location configuration.

    Args:
        hass: The Home Assistant instance.
        latitude: Target latitude.
        longitude: Target longitude.
        elevation: Target elevation.
        location_name: Target location name.
        time_zone: Target time zone.
        unit_system_metric: True for metric, False for imperial.
        currency: Target currency.
        country: Target country code.
        language: Target language code.

    Returns:
        A dictionary indicating the status of the update.
    """
    updates: dict[str, Any] = {}
    if latitude is not None:
        updates["latitude"] = latitude
    if longitude is not None:
        updates["longitude"] = longitude
    if elevation is not None:
        updates["elevation"] = elevation
    if location_name is not None:
        updates["location_name"] = location_name
    if time_zone is not None:
        updates["time_zone"] = time_zone
    if unit_system_metric is not None:
        # Ensure we have access to METRIC_SYSTEM and IMPERIAL_SYSTEM
        # These are typically attributes of hass.config.units
        updates["unit_system"] = (
            CONF_UNIT_SYSTEM_METRIC if unit_system_metric else CONF_UNIT_SYSTEM_IMPERIAL
        )
    if currency is not None:
        updates["currency"] = currency
    if country is not None:
        updates["country"] = country
    if language is not None:
        updates["language"] = language

    if not updates:
        _LOGGER.info("No location parameters provided to update")
        return {"status": "no_changes_requested"}

    try:
        await hass.config.async_update(**updates)
        _LOGGER.info(
            "Successfully updated Home Assistant location configuration: %s", updates
        )
        return {"status": "success", "updated_params": ",".join(updates.keys())}
    except HomeAssistantError as e:
        _LOGGER.error("Failed to update Home Assistant location configuration: %s", e)
        return {"status": "error", "message": str(e)}
    except Exception as e:  # Catching generic Exception for unexpected errors
        _LOGGER.error(
            "Unexpected error updating Home Assistant location configuration: %s", e
        )
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

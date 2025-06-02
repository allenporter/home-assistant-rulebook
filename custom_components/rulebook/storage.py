"""Handles storage of the parsed rulebook."""
import json
import logging
from typing import Any

from aiofiles import open as aio_open
from aiofiles.os import path as aio_path
from aiofiles.os import makedirs as aio_makedirs


from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import STORAGE_DIR, PARSED_RULEBOOK_FILENAME
from .data.home import ParsedHomeDetails

_LOGGER = logging.getLogger(__name__)


async def async_write_parsed_rulebook(
    hass: HomeAssistant, parsed_rulebook: ParsedHomeDetails, config_entry_id: str
) -> None:
    """Write the parsed rulebook to a file specific to the config entry.

    The rulebook is stored as a JSON file in the Home Assistant config directory,
    under a subdirectory named after the config_entry_id.
    """
    entry_storage_path = hass.config.path(STORAGE_DIR, config_entry_id)
    await aio_makedirs(entry_storage_path, exist_ok=True)

    file_path = hass.config.path(STORAGE_DIR, config_entry_id, PARSED_RULEBOOK_FILENAME)
    _LOGGER.debug("Writing parsed rulebook for entry %s to %s", config_entry_id, file_path)
    try:
        async with aio_open(file_path, "w") as f:
            await f.write(parsed_rulebook.model_dump_json(indent=2))
    except OSError as err:
        _LOGGER.error("Error writing parsed rulebook to %s: %s", file_path, err)
        raise HomeAssistantError(
            f"Could not write parsed rulebook to {file_path}: {err}"
        ) from err


async def async_read_parsed_rulebook(hass: HomeAssistant, config_entry_id: str) -> ParsedHomeDetails | None:
    """Read the parsed rulebook from a file specific to the config entry.

    Returns the parsed rulebook or None if the file does not exist or is invalid.
    """
    file_path = hass.config.path(STORAGE_DIR, config_entry_id, PARSED_RULEBOOK_FILENAME)
    if not await aio_path.exists(file_path):
        _LOGGER.debug("Parsed rulebook file for entry %s not found at %s", config_entry_id, file_path)
        return None

    _LOGGER.debug("Reading parsed rulebook for entry %s from %s", config_entry_id, file_path)
    try:
        async with aio_open(file_path, "r") as f:
            content = await f.read()
            data: dict[str, Any] = json.loads(content)
            return ParsedHomeDetails(**data)
    except OSError as err:
        _LOGGER.error("Error reading parsed rulebook from %s: %s", file_path, err)
        raise HomeAssistantError(
            f"Could not read parsed rulebook from {file_path}: {err}"
        ) from err
    except json.JSONDecodeError as err:
        _LOGGER.error("Error decoding parsed rulebook from %s: %s", file_path, err)
        raise HomeAssistantError(
            f"Could not decode parsed rulebook from {file_path}: {err}"
        ) from err
    except Exception as err:
        _LOGGER.error("Unexpected error reading rulebook from %s: %s", file_path, err)
        raise HomeAssistantError(
            f"Unexpected error reading rulebook from {file_path}: {err}"
        ) from err

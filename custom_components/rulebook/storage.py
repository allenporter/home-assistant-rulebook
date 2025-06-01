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
    hass: HomeAssistant, parsed_rulebook: ParsedHomeDetails
) -> None:
    """Write the parsed rulebook to a file.

    The rulebook is stored as a JSON file in the Home Assistant config directory.
    """
    storage_path = hass.config.path(STORAGE_DIR)
    if not await aio_path.isdir(storage_path):
        await aio_makedirs(storage_path)
    file_path = hass.config.path(STORAGE_DIR, PARSED_RULEBOOK_FILENAME)
    _LOGGER.debug("Writing parsed rulebook to %s", file_path)
    try:
        async with aio_open(file_path, "w") as f:
            await f.write(parsed_rulebook.model_dump_json(indent=2))
    except OSError as err:
        _LOGGER.error("Error writing parsed rulebook to %s: %s", file_path, err)
        raise HomeAssistantError(
            f"Could not write parsed rulebook to {file_path}: {err}"
        ) from err


async def async_read_parsed_rulebook(hass: HomeAssistant) -> ParsedHomeDetails | None:
    """Read the parsed rulebook from a file.

    Returns the parsed rulebook or None if the file does not exist or is invalid.
    """
    file_path = hass.config.path(STORAGE_DIR, PARSED_RULEBOOK_FILENAME)
    if not await aio_path.exists(file_path):
        _LOGGER.debug("Parsed rulebook file not found at %s", file_path)
        return None

    _LOGGER.debug("Reading parsed rulebook from %s", file_path)
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

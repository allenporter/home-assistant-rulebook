"""Config flow for rulebook integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import logging

from google import genai
from google.genai.errors import APIError, ClientError
import voluptuous as vol

from homeassistant.helpers import (
    selector,
    config_validation as cv,
)

from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaCommonFlowHandler,  # Ensure SchemaCommonFlowHandler is imported
    SchemaFlowFormStep,
)

from .const import DOMAIN, CONF_RULEBOOK, CONF_API_KEY, TIMEOUT_MILLIS

_LOGGER = logging.getLogger(__name__)


async def validate_user_input(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate the user input and test the connection."""
    _LOGGER.debug("Validating user input: %s", user_input)
    client = genai.Client(api_key=user_input[CONF_API_KEY])
    try:
        await client.aio.models.list(
            config={
                "http_options": {
                    "timeout": TIMEOUT_MILLIS,
                },
                "query_base": True,
            }
        )
        return user_input
    except (APIError, ClientError) as err:
        _LOGGER.error("Failed to connect to GenAI API: %s", err)
        return {"base": "cannot_connect"}
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected error during validation: %s", err)
        return {"base": "unknown_error"}


CONFIG_FLOW = {
    "user": SchemaFlowFormStep(
        vol.Schema(
            {
                vol.Required(CONF_API_KEY): cv.string,
                # vol.Required(CONF_AGENT_ID): selector.EntitySelector(
                #     selector.EntitySelectorConfig(domain="conversation"),
                # ),
                vol.Required(CONF_RULEBOOK): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
            }
        ),
        validate_user_input=validate_user_input,
    ),
}


async def _options_schema_factory(handler: SchemaCommonFlowHandler) -> vol.Schema:
    """Return schema for an options flow."""
    return vol.Schema(
        {
            vol.Required(
                CONF_RULEBOOK,
                default=handler.options.get(CONF_RULEBOOK, ""),
            ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
        }
    )


OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(schema=_options_schema_factory),
}


class HomeAssistantRulebookConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Switch as X."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    VERSION = 1
    MINOR_VERSION = 1

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        # registry = er.async_get(self.hass)
        # TODO: Uncomment when we have a conversation agent
        # entity_entry = registry.async_get(options[CONF_AGENT_ID])
        # assert entity_entry
        # return f"Rulebook {entity_entry.original_name}"
        return "Rulebook Agent"

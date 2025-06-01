"""Agent for parsing the user's rulebook."""

import logging

from google.adk.agents import LlmAgent

from homeassistant.core import HomeAssistant

from custom_components.rulebook.const import CONF_RULEBOOK
from custom_components.rulebook.types import RulebookConfigEntry
from custom_components.rulebook.data.home import ParsedHomeDetails

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


def async_create_agent(
    hass: HomeAssistant, config_entry: RulebookConfigEntry
) -> LlmAgent:
    """Create and return an instance of the RulebookParserAgent."""
    rulebook_text = config_entry.options[CONF_RULEBOOK]

    return LlmAgent(
        name="RulebookParserAgent",
        model=SUMMARIZE_MODEL,
        description="Parses user rulebooks into structured JSON format.",
        instruction=_INSTRUCTION_FORMAT.format(rulebook_text=rulebook_text),
        output_schema=ParsedHomeDetails,
        output_key=PARSED_RULEBOOK_KEY,
    )

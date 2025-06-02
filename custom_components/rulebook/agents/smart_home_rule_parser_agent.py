"""Agent for parsing individual smart home rules."""

import logging

from google.adk.agents import LlmAgent

from custom_components.rulebook.data.home import ParsedSmartHomeRule
from custom_components.rulebook.types import RulebookConfigEntry
from homeassistant.core import HomeAssistant
from .const import AGENT_MODEL

_LOGGER = logging.getLogger(__name__)


_RULE_PARSER_INSTRUCTION = (
    "You are an expert at parsing individual smart home rules from text snippets. "
    "Your task is to analyze the provided text snippet for a single smart home rule and extract its core components. "
    "You MUST respond with a single JSON object that strictly conforms to the 'ParsedSmartHomeRule' schema. "
    "The schema includes the following fields: "
    "  - 'rule_raw_text': The original text snippet you are parsing. This MUST be included in your response. "
    "  - 'rule_name': A concise, descriptive name for the rule (e.g., 'Turn on Porch Light at Sunset'). If not obvious, generate a suitable one. This can be null if not clearly determinable. "
    "  - 'entities_mentioned': A list of all unique Home Assistant entity IDs or descriptive names of devices, locations, or people mentioned in the rule (e.g., ['light.porch_light', 'sun.sun', 'binary_sensor.front_door_motion', 'Mom']). Extract these as accurately as possible. "
    "  - 'core_logic_text': The essential part of the rule that describes its primary trigger, conditions, and actions, in a condensed natural language form. This text will be used by another agent for more detailed parsing. (e.g., 'If motion at front door after sunset, turn on porch light for 5 minutes.'). This can be null if the core logic is not clear. "
    "Ensure all parts of the rule snippet are mapped to the appropriate fields. "
    "Always include the 'rule_raw_text' field with the original input snippet. "
    "Do not call any tools. Your only output should be the JSON object. "
    "Here is an example: "
    "Input rule text: 'When the front door motion sensor detects movement after sunset, turn on the porch light for 5 minutes and send a notification to John.' "
    "Expected JSON output: "
    "'''\n"
    "{\n"
    '  "rule_raw_text": "When the front door motion sensor detects movement after sunset, turn on the porch light for 5 minutes and send a notification to John.",\n'
    '  "rule_name": "Front Door Motion Light & Notify",\n'
    '  "entities_mentioned": ["front door motion sensor", "sunset", "porch light", "John"],\n'
    '  "core_logic_text": "If motion at front door after sunset, turn on porch light for 5 minutes and send notification to John."\n'
    "}\n"
    "'''\n"
    "The user's smart home rule text snippet is as follows:\n\n"
)


def async_create_agent(
    hass: HomeAssistant,
    config_entry: RulebookConfigEntry,
    input_key: str,
    output_key: str,
) -> LlmAgent:
    """Create and return an instance of the SmartHomeRuleParserAgent.

    This agent is responsible for parsing individual smart home rules from text snippets.
    It may be invoked multiple times in parallel to handle different rules simultaneously.
    This agent is dynamically created and as a result has a dynamic input and output
    key with details about the specific rule to parse.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        config_entry (RulebookConfigEntry): The configuration entry for the rulebook.
        input_key (str): The key in the input data where the rule text snippet is located.
        output_key (str): The key in the output data where the parsed rule will be stored.
    Returns:
        LlmAgent: An instance of the SmartHomeRuleParserAgent configured to parse smart home rules.
    """
    return LlmAgent(
        name="SmartHomeRuleParserAgent",
        model=AGENT_MODEL,
        description="Parses a single smart home rule text snippet into a structured ParsedSmartHomeRule JSON format.",
        instruction=_RULE_PARSER_INSTRUCTION + "{" + input_key + "}\n\n",
        disallow_transfer_to_peers=True,
        output_schema=ParsedSmartHomeRule,
        output_key=output_key,
    )

"""Agent for parsing the user's rulebook.

The goal of this is a workflow (series of agents/tools) that will do the following:

1. Parse the user's rulebook text into a structured JSON format.
2. Compare the parsed rulebook against existing ParsedHomeDetails in storage
   and determine if there is a "significant change" in the rulebook or if it is
    "the same" as the existing details. We will allow the LLM to judge to avoid
    updating the rulebook if it is not necessary e.g. the previous parser
    proposes minitor changes that do not affect the overall structure or
    functionality of the home automation system.
3. Persist the parsed rulebook in storage for future use by other workflows.

"""

import logging
from collections.abc import AsyncGenerator
from typing import override, Any

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from homeassistant.core import HomeAssistant

from custom_components.rulebook.const import CONF_RULEBOOK
from custom_components.rulebook.types import RulebookConfigEntry
from custom_components.rulebook.storage import (
    async_write_parsed_rulebook,
    async_read_parsed_rulebook,
)
from custom_components.rulebook.data.home import ParsedHomeDetails, ParsedSmartHomeRule

from .const import SUMMARIZE_MODEL, AGENT_MODEL
from .smart_home_rule_parser_agent import (
    async_create_agent as async_create_smart_home_rule_parser_agent,
)
from .common import ParallelMaxInFlightAgent

_LOGGER = logging.getLogger(__name__)

_MAX_CONCURRENT_RULE_PARSERS = 5

_RULEBOOK_TEXT_KEY = "rulebook_text"
_PARSED_RULEBOOK_KEY = "parsed_rulebook"
_PREVIOUS_PARSED_RULEBOOK_JSON_KEY = "previous_parsed_rulebook_json"
_PARSED_RULEBOOK_JSON_KEY = "parsed_rulebook_json"
_RULE_TEXT_INPUT_KEY = "smart_home_rule_text_{rule_index}"
_RULE_TEXT_OUTPUT_KEY = "parsed_smart_home_rule_{rule_index}"


_PARSER_INSTRUCTION = (
    "You are an expert at parsing free-form text rulebooks for smart homes. "
    "Your primary task is to understand and structure the entire rulebook provided in the prompt. "
    "Analyze the rulebook text to identify: "
    "1. Global/Basic Information (home name, default language). "
    "2. Location Details (address, timezone, etc.). "
    "3. Key People involved in the home. "
    "4. Mentions of Floors (e.g., 'first floor', 'upstairs', 'basement'). Extract these as a list of strings. "
    "5. Mentions of Areas or Structures (e.g., 'living room', 'kitchen', 'garden shed'). Extract these as a list of strings. "
    "6. Mentions of Utility Providers (e.g., 'City Electric', 'Comcast Internet'). Extract these as a list of strings. "
    "7. Individual Smart Home Rules. Extract the raw text for each distinct smart home rule you identify. These rules typically describe a cause-and-effect relationship (e.g., 'IF something happens THEN do something else'). "
    "Your information will later be used to create Smart Home Rules independently, but you are not responsible for that. "
    "You MUST respond with a single, comprehensive JSON object that strictly conforms to the 'ParsedHomeDetails' schema. "
    "The schema defines keys like 'raw_text', 'parsed_status', 'basic_info', 'location_details', 'key_people', "
    "'floor_mentions', 'area_mentions', 'utility_provider_mentions', and 'raw_smart_home_rules_text'. "
    "Populate the 'floor_mentions', 'area_mentions', and 'utility_provider_mentions' fields with lists of strings, where each string is a direct mention from the text. "
    "Populate the 'raw_smart_home_rules_text' field with a list of strings, where each string is the exact text of an individual smart home rule you extracted. "
    "Ensure all parts of the rulebook are mapped to the appropriate fields in this schema. "
    "If a section of the rulebook is unclear or missing, use null or empty lists/objects for the corresponding schema fields where appropriate, "
    "but always return a valid JSON object matching the schema structure. "
    "Do not call any tools. Your only output should be the JSON object."
    "\n\n"
    "The user's rulebook is as follows:\n\n"
    "{rulebook_text}\n\n"
)


_REVIEWER_INSTRUCTION = (
    "You are an expert at reviewing parsed rulebooks. "
    "Your primary task is to compare a newly parsed rulebook JSON with a previous version and decide if the changes are significant enough to warrant updating the stored version. "
    "The rulebook JSON now includes a 'smart_home_rules' field, which contains a list of parsed individual smart home rules. Each rule in this list conforms to the 'ParsedSmartHomeRule' schema, primarily containing 'rule_raw_text', 'rule_name', 'entities_mentioned', and 'core_logic_text'. Pay close attention to changes in this list. "
    "If you determine the changes are significant, you MUST call the 'store_rulebook' tool to save the new version. "
    "If the changes are minor or non-existent, you should NOT call the tool. "
    "After making your decision, you MUST provide a concise explanation to the user about what you did and why. "
    "Be specific but brief in your explanation. For example, if you store it, mention 1-2 key areas of change. If you don't, explain why the changes were not considered significant."
    "\\n\\n"
    "The previous parsed rulebook JSON is:\\n\\n"
    "{previous_parsed_rulebook_json}\\n\\n"
    "The new parsed rulebook JSON is:\\n\\n"
    "{parsed_rulebook_json}\\n\\n"
    "Follow these steps:"
    "1. Analyze both JSON objects to identify differences. "
    "2. Determine if these differences constitute a 'significant change'. A significant change includes modifications to structure, key information (like 'basic_info', 'location_details', 'key_people', 'floor_mentions', 'area_mentions', 'utility_provider_mentions', or the list of 'smart_home_rules' and their details), or overall content that would impact how the smart home operates or is understood. Minor formatting or rephrasing that doesn't alter meaning is not significant. Changes to 'smart_home_rules' (e.g., new rules, deleted rules, or modifications to a rule's 'rule_name', 'entities_mentioned', or 'core_logic_text') are generally considered significant. "
    "3. If changes are significant: Call the 'store_rulebook' tool. Then, respond to the user, for example: 'I found significant updates in the rulebook, particularly regarding [specific area, e.g., new smart home rules for the kitchen and updated utility provider mentions]. I have now stored the latest version.' "
    "4. If changes are NOT significant: Do NOT call the 'store_rulebook' tool. Then, respond to the user, for example: 'I reviewed the rulebook. The recent modifications appear to be minor (e.g., slight rephrasing in descriptions) and don\\\\\\'t substantially change its core details or smart home rules. The stored version remains unchanged.' "
    "Your response to the user is crucial after your decision."
)


class RulebookPipelineAgent(BaseAgent):  # type: ignore[misc]
    """Agent that orchestrates the rulebook parsing and review process."""

    hass: HomeAssistant
    config_entry: RulebookConfigEntry
    parser_agent: LlmAgent
    reviewer_agent: LlmAgent

    # model_config allows setting Pydantic configurations if needed, e.g., arbitrary_types_allowed
    model_config = {"arbitrary_types_allowed": True}

    @override
    async def _run_async_impl(  # type: ignore[misc]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Implements the custom orchestration logic for the rulebook workflow."""
        _LOGGER.info(f"[{self.name}] Starting rulebook parsing workflow.")

        rulebook_text = self.config_entry.options[CONF_RULEBOOK]
        ctx.session.state[_RULEBOOK_TEXT_KEY] = rulebook_text

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(parts=[types.Part(text="Examining your rulebook.")]),
            partial=True,
            turn_complete=False,
        )

        # 1. Initial Rulebook Parsing (extracts raw rule snippets)
        _LOGGER.info(f"[{self.name}] Running RulebookParser for initial parsing...")
        async for event in self.parser_agent.run_async(ctx):
            debug_info = event.model_dump_json(indent=2, exclude_none=True)
            _LOGGER.debug(
                f"[{self.name}] Event from RulebookParser: {debug_info[:200]}..."
            )
            # TODO: Don't return underlying data. However, this needs to be yielded
            # because it updates session state. Find a fix.
            yield event

        if (
            _PARSED_RULEBOOK_KEY not in ctx.session.state
            or not ctx.session.state[_PARSED_RULEBOOK_KEY]
        ):
            _LOGGER.error(
                f"[{self.name}] Failed to generate initial rulebook details. Aborting workflow."
            )
            # TODO: Yield useful error messages
            return

        initial_rulebook_dict = ctx.session.state[_PARSED_RULEBOOK_KEY]
        home_details = ParsedHomeDetails(**initial_rulebook_dict)
        _LOGGER.info(
            f"[{self.name}] Initial parsing complete. Found {len(home_details.raw_smart_home_rules_text)} raw rule snippets."
        )

        # 2. Parse Individual Smart Home Rules Concurrently
        if home_details.raw_smart_home_rules_text:
            _LOGGER.info(
                f"[{self.name}] Preparing to parse {len(home_details.raw_smart_home_rules_text)} rule snippets concurrently..."
            )

            subagents = []
            for i, snippet in enumerate(home_details.raw_smart_home_rules_text):
                input_key = _RULE_TEXT_INPUT_KEY.format(rule_index=i)
                output_key = _RULE_TEXT_OUTPUT_KEY.format(rule_index=i)
                rule_parser_agent = async_create_smart_home_rule_parser_agent(
                    self.hass,
                    self.config_entry,
                    input_key=input_key,
                    output_key=output_key,
                )
                subagents.append(rule_parser_agent)

                ctx.session.state[input_key] = snippet

            parallel_agent = ParallelMaxInFlightAgent(
                name="ParallelSmartHomeRuleParserAgent",
                sub_agents=subagents,
                description="Runs multiple smart home rule parser agents in parallel.",
                max_in_flight=_MAX_CONCURRENT_RULE_PARSERS,
            )

            async for event in parallel_agent.run_async(ctx):
                debug_info = event.model_dump_json(indent=2, exclude_none=True)
                _LOGGER.debug(
                    f"[{self.name}] Event from RulebookParser: {debug_info[:200]}..."
                )
                # TODO: Don't return underlying data. However, this needs to be yielded
                # because it updates session state. Find a fix.
                yield event

            # Process the results of the parallel parsing
            _LOGGER.info(
                f"[{self.name}] Finished parsing individual smart home rules. Processing results..."
            )
            parsed_smart_home_rules = []
            for i, snippet in enumerate(home_details.raw_smart_home_rules_text):
                output_key = _RULE_TEXT_OUTPUT_KEY.format(rule_index=i)
                parsed_rule_dict = ctx.session.state.get(output_key)
                if not parsed_rule_dict:
                    _LOGGER.warning(
                        f"[{self.name}] No parsed rule found for snippet {i + 1}. This may indicate an issue with the parsing agent."
                    )
                    continue
                _LOGGER.debug(
                    f"[{self.name}] Parsed rule snippet {i + 1}: {parsed_rule_dict}"
                )
                parsed_rule = ParsedSmartHomeRule(**parsed_rule_dict)
                parsed_smart_home_rules.append(parsed_rule)
            _LOGGER.info(
                f"[{self.name}] Successfully parsed {len(parsed_smart_home_rules)} smart home rules."
            )
            home_details.smart_home_rules = parsed_smart_home_rules
            # Update the main parsed rulebook in the context state with the fully parsed rules
            ctx.session.state[_PARSED_RULEBOOK_KEY] = home_details.model_dump()
        else:
            _LOGGER.info(
                f"[{self.name}] No raw smart home rule snippets found to parse."
            )

        # 3. Rulebook Review
        _LOGGER.info(f"[{self.name}] Running RulebookReviewer...")
        current_parsed_rulebook = await async_read_parsed_rulebook(
            self.hass, self.config_entry.entry_id
        )
        current_parsed_rulebook_json = (
            current_parsed_rulebook.model_dump_json(indent=2)
            if current_parsed_rulebook
            else "{}"
        )
        ctx.session.state[_PREVIOUS_PARSED_RULEBOOK_JSON_KEY] = (
            current_parsed_rulebook_json
        )
        ctx.session.state[_PARSED_RULEBOOK_JSON_KEY] = home_details.model_dump_json(
            indent=2
        )
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(
                parts=[
                    types.Part(text="Let me take a look at your previous rulebook. ")
                ]
            ),
            partial=True,
            turn_complete=False,
        )

        # Use the reviewer_agent instance attribute assigned during init
        async for event in self.reviewer_agent.run_async(ctx):
            _LOGGER.debug(
                f"[{self.name}] Event from RulebookReviewer: {event.model_dump_json(indent=2, exclude_none=True)}"
            )
            yield event

        _LOGGER.info(f"[{self.name}] Workflow finished.")


class RulebookStorageTool:
    """Tool for reading and writing the parsed rulebook to storage."""

    def __init__(self, hass: HomeAssistant, config_entry: RulebookConfigEntry) -> None:
        """Initialize the RulebookStorageTool with the Home Assistant instance."""
        self.hass = hass
        self.config_entry = config_entry

    async def store_rulebook(self, tool_context: ToolContext) -> dict[str, Any]:
        """Tool for storing the parsed rulebook for this session in storage.

        The parsed rulebook from the session is automatically injected into the
        tool context by nother agent. Invoking this tool will store the most
        recent parsed rulebook in storage.

        Returns:
        - A message indicating the result of the storage operation.
        """
        rulebook_dict = tool_context.state[_PARSED_RULEBOOK_KEY]
        home_details = ParsedHomeDetails(**rulebook_dict)

        await async_write_parsed_rulebook(
            self.hass, home_details, self.config_entry.entry_id
        )
        return {
            "success": True,
            "message": "Parsed rulebook written successfully.",
        }


def async_create_agent(
    hass: HomeAssistant, config_entry: RulebookConfigEntry
) -> LlmAgent:
    """Create and return an instance of the RulebookParserAgent."""
    parser_agent = LlmAgent(
        name="RulebookParserAgent",
        model=AGENT_MODEL,
        description="Parses user rulebooks into a structured JSON format representing ParsedHomeDetails.",
        instruction=_PARSER_INSTRUCTION,
        output_schema=ParsedHomeDetails,
        output_key=_PARSED_RULEBOOK_KEY,
    )
    tools = RulebookStorageTool(hass, config_entry)
    reviewer_agent = LlmAgent(
        name="RulebookReviewerAgent",
        model=SUMMARIZE_MODEL,
        description="Reviews the parsed rulebook for significant changes and decides if it should be persisted.",
        instruction=_REVIEWER_INSTRUCTION,
        disallow_transfer_to_peers=True,
        tools=[
            FunctionTool(func=tools.store_rulebook),
        ],
    )
    pipeline_agent = RulebookPipelineAgent(
        name="RulebookPipelineAgent",
        description="Orchestrates the rulebook parsing and review process.",
        hass=hass,
        config_entry=config_entry,
        parser_agent=parser_agent,
        reviewer_agent=reviewer_agent,
    )
    return pipeline_agent

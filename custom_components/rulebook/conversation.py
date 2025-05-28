"""Conversation agent for the Rulebook agent."""

from typing import Literal
import logging

from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

from homeassistant.components import assist_pipeline, conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant, Context
from homeassistant.helpers import device_registry as dr, intent
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, RULEBOOK
from .types import RulebookConfigEntry
from .agent_llm import agent_context, AgentContext


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RulebookConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up conversation entities."""
    agent = RulebookConversationEntity(config_entry)
    async_add_entities([agent])


class RulebookConversationEntity(
    conversation.ConversationEntity, conversation.AbstractConversationAgent
):
    """Rulebook conversation agent."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supports_streaming = True

    def __init__(self, entry: RulebookConfigEntry) -> None:
        """Initialize the agent."""
        self.entry = entry
        self._agent = entry.runtime_data.agent
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Rulebook",
            model="Rulebook Agent",
            entry_type=dr.DeviceEntryType.SERVICE,
        )
        self._session_service = InMemorySessionService()

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        assist_pipeline.async_migrate_engine(
            self.hass, "conversation", self.entry.entry_id, self.entity_id
        )
        conversation.async_set_agent(self.hass, self.entry, self)
        self.entry.async_on_unload(
            self.entry.add_update_listener(self._async_entry_update_listener)
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Process the user input and call the API."""
        try:
            await chat_log.async_update_llm_data(
                DOMAIN,
                user_input,
                None,
                "",
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        with agent_context(
            AgentContext(
                hass=self.hass,
                config_entry=self.entry,
                context=user_input.context,
            )
        ):
            await self._async_handle_chat_log(
                chat_log, user_input.context, user_input.agent_id
            )

        intent_response = intent.IntentResponse(language=user_input.language)
        assert type(chat_log.content[-1]) is conversation.AssistantContent
        intent_response.async_set_speech(chat_log.content[-1].content or "")
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=chat_log.conversation_id,
            continue_conversation=chat_log.continue_conversation,
        )

    async def _async_handle_chat_log(
        self,
        chat_log: conversation.ChatLog,
        context: Context,
        agent_id: str,
    ) -> None:
        """Generate an answer for the chat log."""
        user_id = context.user_id or "unknown_user"
        session = await self._session_service.create_session(  # noqa: F841
            app_name=RULEBOOK,
            user_id=user_id,
            session_id=chat_log.conversation_id,
        )
        runner = Runner(
            agent=self._agent, app_name=RULEBOOK, session_service=self._session_service
        )

        last_content = chat_log.content[-1]
        if not isinstance(last_content, conversation.UserContent):
            raise ValueError(
                "Last content in chat log must be UserContent, "
                f"got {type(last_content).__name__}"
            )
        content = types.Content(
            role="user", parts=[types.Part(text=last_content.content or "")]
        )

        final_response_text: str = "No response received."
        async for event in runner.run_async(
            session_id=chat_log.conversation_id, new_message=content, user_id=user_id
        ):
            _LOGGER.info(
                "Processing event: Author: %s, Type: %s, Final: %s, Content: %s",
                event.author,
                type(event).__name__,
                event.is_final_response(),
                event.content,
            )

            # Key Concept: is_final_response() marks the concluding message for the turn.
            if event.is_final_response():
                if event.content and event.content.parts:
                    # Assuming text response in the first part
                    final_response_text = event.content.parts[0].text
                elif (
                    event.actions and event.actions.escalate
                ):  # Handle potential errors/escalations
                    final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
                # Add more checks here if needed (e.g., specific error codes)
                break  # Stop processing events once the final response is found

        chat_log.async_add_assistant_content_without_tools(
            conversation.AssistantContent(
                agent_id=agent_id,
                content=final_response_text,
            )
        )

    async def _async_entry_update_listener(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Handle options update."""
        # Reload as we update device info + entity name + supported features
        await hass.config_entries.async_reload(entry.entry_id)

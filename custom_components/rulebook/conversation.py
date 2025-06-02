"""Conversation agent for the Rulebook agent."""

from collections.abc import AsyncGenerator
from typing import Literal
import logging

from google.adk.agents.run_config import StreamingMode, RunConfig
from google.adk.events.event import Event
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.errors import APIError

from google.genai import types

from homeassistant.components import assist_pipeline, conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant, Context
from homeassistant.helpers import device_registry as dr, intent
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, RULEBOOK
from .types import RulebookConfigEntry


_LOGGER = logging.getLogger(__name__)
_ERROR_GETTING_RESPONSE = "Sorry, I had a problem getting a response from the Agent."


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RulebookConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up conversation entities."""
    agent = RulebookConversationEntity(config_entry)
    async_add_entities([agent])


async def _transform_stream(
    chat_log: conversation.ChatLog,
    result: AsyncGenerator[Event, None],
) -> AsyncGenerator[conversation.AssistantContentDeltaDict]:
    """Transform an OpenAI delta stream into HA format."""
    start = True
    try:
        async for event in result:
            _LOGGER.debug(
                "Processing event: Author: %s, Type: %s, Final: %s, Content: %s",
                event.author,
                type(event).__name__,
                event.is_final_response(),
                event.content,
            )
            if event.is_final_response():
                # Note: This may be pushing up a response from a single agent run
                _LOGGER.info("Final response received")
                continue
            if not event.content or not (response_parts := event.content.parts):
                continue
            chunk: conversation.AssistantContentDeltaDict = {}
            if start:
                chunk["role"] = "assistant"
                start = False

            # Tool calls were handled by the agent, we don't propagate them. However
            # for debugging for now we just print that we called the tool.
            tool_calls = [
                f"I called {part.function_call.name} with {part.function_call.args}\n"[
                    :100
                ]
                + "..."
                for part in response_parts
                if part.function_call
            ]
            content_parts = [part.text for part in response_parts if part.text]
            content = "".join(content_parts + tool_calls)
            if not content:
                _LOGGER.warning("Received empty content from event: %s", event)
                continue
            chunk["content"] = content
            yield chunk
    except (APIError, ValueError, HomeAssistantError) as err:
        _LOGGER.exception("Error sending message: %s %s", type(err), err)
        if isinstance(err, APIError):
            message = err.message
        else:
            message = type(err).__name__
        error = f"{_ERROR_GETTING_RESPONSE}: {message}"
        raise HomeAssistantError(error) from err


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

        await self._async_handle_chat_log(
            chat_log, user_input.context, user_input.agent_id
        )

        intent_response = intent.IntentResponse(language=user_input.language)
        if not isinstance(chat_log.content[-1], conversation.AssistantContent):
            _LOGGER.error(
                "Last content in chat log is not an AssistantContent: %s. This could be due to the model not returning a valid response",
                chat_log.content[-1],
            )
            raise HomeAssistantError(_ERROR_GETTING_RESPONSE)
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
        session = await self._session_service.get_session(  # noqa: F841
            app_name=RULEBOOK,
            user_id=user_id,
            session_id=chat_log.conversation_id,
        )
        if not session:
            session = await self._session_service.create_session(  # noqa: F841
                app_name=RULEBOOK,
                user_id=user_id,
                session_id=chat_log.conversation_id,
            )

        _LOGGER.info("--- Examining Session Properties ---")
        _LOGGER.info(f"ID (`id`):                {session.id}")
        _LOGGER.info(f"Application Name (`app_name`): {session.app_name}")
        _LOGGER.info(f"User ID (`user_id`):         {session.user_id}")
        _LOGGER.info(
            f"State (`state`):           {session.state}"
        )  # Note: Only shows initial state here
        _LOGGER.info(f"Events (`events`):         {session.events}")  # Initially empty
        _LOGGER.info(
            f"Last Update (`last_update_time`): {session.last_update_time:.2f}"
        )
        _LOGGER.info("---------------------------------")

        runner = Runner(
            agent=self._agent,
            app_name=RULEBOOK,
            session_service=self._session_service,
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

        run_config = RunConfig(streaming_mode=StreamingMode.SSE)
        event_stream = runner.run_async(
            session_id=chat_log.conversation_id,
            new_message=content,
            user_id=user_id,
            run_config=run_config,
        )

        async for chunk in chat_log.async_add_delta_content_stream(
            self.entity_id, _transform_stream(chat_log, event_stream)
        ):
            _LOGGER.debug("Chunk processed")

    async def _async_entry_update_listener(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Handle options update."""
        # Reload as we update device info + entity name + supported features
        await hass.config_entries.async_reload(entry.entry_id)

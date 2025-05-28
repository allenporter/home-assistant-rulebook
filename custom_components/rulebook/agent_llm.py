"""Module for registering a conversation agent as an agent framework LLM."""

from dataclasses import dataclass
from collections.abc import AsyncGenerator, Generator, AsyncIterator
import contextvars
from contextlib import contextmanager
import logging

from google.genai import errors
from google.adk.models import LLMRegistry, BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from homeassistant.core import HomeAssistant, Context
from homeassistant.exceptions import HomeAssistantError

from .const import RULEBOOK_AGENT_ID
from .types import RulebookConfigEntry


_LOGGER = logging.getLogger(__name__)

_MODEL_NAME = "gemini-2.5-pro-preview-05-06"
_ERROR_GETTING_RESPONSE = (
    "Sorry, I had a problem getting a response from Google Generative AI."
)


@dataclass(frozen=True, kw_only=True)
class AgentContext:
    """Context for the Rulebook agent LLM."""

    hass: HomeAssistant
    config_entry: RulebookConfigEntry
    context: Context


_agent_context: contextvars.ContextVar[AgentContext | None] = contextvars.ContextVar(
    "agent_context", default=None
)


def async_register(hass: HomeAssistant, config_entry: RulebookConfigEntry) -> None:
    """Register a conversation agent as an agent framework LLM."""
    _LOGGER.debug("Registering Rulebook agent LLM with ID %s", RULEBOOK_AGENT_ID)
    LLMRegistry.register(RulebookLlm)


@contextmanager
def agent_context(agent_context: AgentContext) -> Generator[None, None, None]:
    """Context manager to set the Rulebook agent context."""
    token = _agent_context.set(agent_context)
    try:
        yield
    finally:
        _agent_context.reset(token)


async def _transform_stream(
    result: AsyncIterator[types.GenerateContentResponse],
) -> AsyncGenerator[LlmResponse, None]:
    try:
        async for response in result:
            _LOGGER.debug("Received response chunk: %s", response)

            # According to the API docs, this would mean no candidate is returned, so we can safely throw an error here.
            if response.prompt_feedback or not response.candidates:
                reason = (
                    response.prompt_feedback.block_reason_message
                    if response.prompt_feedback
                    else "unknown"
                )
                raise HomeAssistantError(
                    f"The message got blocked due to content violations, reason: {reason}"
                )

            candidate = response.candidates[0]

            if (
                candidate.finish_reason is not None
                and candidate.finish_reason != "STOP"
            ):
                # The message ended due to a content error as explained in: https://ai.google.dev/api/generate-content#FinishReason
                _LOGGER.error(
                    "Error in Google Generative AI response: %s, see: https://ai.google.dev/api/generate-content#FinishReason",
                    candidate.finish_reason,
                )
                raise HomeAssistantError(
                    f"{_ERROR_GETTING_RESPONSE} Reason: {candidate.finish_reason}"
                )

            response_parts = (
                candidate.content.parts
                if candidate.content is not None and candidate.content.parts is not None
                else []
            )

            parts = []
            for part in response_parts:
                if part.text:
                    parts.append(types.Part(text=part.text))
                if tool_call := part.function_call:
                    parts.append(
                        types.Part(
                            function_call=types.FunctionCall(
                                name=tool_call.name if tool_call.name else "",
                                args=tool_call.args,
                            ),
                        )
                    )

            yield LlmResponse(
                content=types.Content(
                    parts=parts,
                    role="assistant",
                ),
                turn_complete=True,
            )
    except (errors.APIError, ValueError) as err:
        _LOGGER.error("Error sending message: %s %s", type(err), err)
        if isinstance(err, errors.APIError):
            message = err.message
        else:
            message = type(err).__name__
        error = f"{_ERROR_GETTING_RESPONSE}: {message}"
        raise HomeAssistantError(error) from err


class RulebookLlm(BaseLlm):  # type: ignore[misc]
    """A conversation agent LLM."""

    @classmethod
    def supported_models(cls) -> list[str]:
        """Returns a list of supported models in regex for LlmRegistry."""
        return [RULEBOOK_AGENT_ID]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        if stream:
            raise ValueError("Streaming not yet supported")
        agent_context = _agent_context.get()
        if agent_context is None:
            raise ValueError(
                "Agent context not set. Use agent_context() context manager."
            )
        config_entry = agent_context.config_entry
        client = config_entry.runtime_data.client

        content = llm_request.contents[-1]
        text = content.parts[-1].text

        chat = client.aio.chats.create(model=_MODEL_NAME)
        try:
            chat_response_generator = await chat.send_message_stream(message=text)
        except (errors.APIError, errors.ClientError) as err:
            _LOGGER.error("Error sending message: %s %s", type(err), err)
            error = _ERROR_GETTING_RESPONSE
            raise HomeAssistantError(error) from err

        async for response in _transform_stream(chat_response_generator):
            yield response

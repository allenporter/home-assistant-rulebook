"""Module for registering a conversation agent as an agent framework LLM.

This is a placeholder shim and just proxies Gemini, but needs to be updated to
use the LLM Task AI API once it is available.
"""

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
    responses: AsyncIterator[types.GenerateContentResponse],
) -> AsyncGenerator[LlmResponse, None]:
    try:
        text = ""
        async for response in responses:
            _LOGGER.debug("Received response chunk: %s", response)
            llm_response = LlmResponse.create(response)
            if (
                llm_response.content
                and llm_response.content.parts
                and llm_response.content.parts[0].text
            ):
                text += llm_response.content.parts[0].text
                llm_response.partial = True
            _LOGGER.debug("Yielding response chunk: %s", llm_response)
            yield llm_response
        if (
            text
            and response
            and response.candidates
            and response.candidates[0].finish_reason == types.FinishReason.STOP
        ):
            yield LlmResponse(
                content=types.ModelContent(
                    parts=[types.Part.from_text(text="")],
                ),
            )

    except (errors.APIError, ValueError) as err:
        _LOGGER.error("Error sending message: %s %s", type(err), err)
        if isinstance(err, errors.APIError):
            message = err.message
        else:
            message = type(err).__name__
        error = f"{_ERROR_GETTING_RESPONSE}: {message}"
        raise HomeAssistantError(error) from err
    except Exception:
        _LOGGER.exception("Unexpected error while processing response")
        raise HomeAssistantError(_ERROR_GETTING_RESPONSE) from None


class RulebookLlm(BaseLlm):  # type: ignore[misc]
    """A conversation agent LLM."""

    @classmethod
    def supported_models(cls) -> list[str]:
        """Returns a list of supported models in regex for LlmRegistry."""
        return [RULEBOOK_AGENT_ID]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        if not stream:
            raise ValueError("Only streaming is supposed")
        agent_context = _agent_context.get()
        if agent_context is None:
            raise ValueError(
                "Agent context not set. Use agent_context() context manager."
            )
        config_entry = agent_context.config_entry
        client = config_entry.runtime_data.client

        # TODO: We're ignoring the entire conversation history, fix this
        # to pass agent context.
        _LOGGER.debug(
            "Generating content for LLM request: %s with model %s",
            llm_request,
            _MODEL_NAME,
        )
        # Extra debug to diagnose LLM task issues.
        _LOGGER.debug("History: %s", llm_request.contents[:-1])
        _LOGGER.debug("Current: %s", llm_request.contents[-1])
        chat = client.aio.chats.create(
            model=_MODEL_NAME,
            config=llm_request.config,
            history=llm_request.contents[:-1],  # Exclude the last content as it's the user input
        )
        content = llm_request.contents[-1]
        text = "".join(part.text for part in content.parts if part.text)
        try:
            chat_response_generator = await chat.send_message_stream(message=text)
        except (errors.APIError, errors.ClientError) as err:
            _LOGGER.error("Error sending message: %s %s", type(err), err)
            error = _ERROR_GETTING_RESPONSE
            raise HomeAssistantError(error) from err

        async for response in _transform_stream(chat_response_generator):
            yield response

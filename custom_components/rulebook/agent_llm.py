"""Module for registering a conversation agent as an agent framework LLM."""

from collections.abc import AsyncGenerator

from google.adk.models import LLMRegistry, BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import RULEBOOK_AGENT_ID


async def async_register(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Register a conversation agent as an agent framework LLM."""
    LLMRegistry.register(RulebookLlm(hass, config_entry))


class RulebookLlm(BaseLlm):  # type: ignore[misc]
    """A conversation agent LLM."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the conversation agent LLM."""
        super().__init__(model=RULEBOOK_AGENT_ID)
        self._hass = hass
        self._config_entry = config_entry

    @classmethod
    def supported_models(cls) -> list[str]:
        """Returns a list of supported models in regex for LlmRegistry."""
        return [RULEBOOK_AGENT_ID]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        if stream:
            raise ValueError("Streaming not yet supported")
        yield LlmResponse(
            content=types.Content(
                parts=[
                    types.Part(
                        text="Example",
                    )
                ],
                role="assistant",
            ),
            turn_complete=True,
        )

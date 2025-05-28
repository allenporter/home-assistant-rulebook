"""Types for the Rulebook integration."""

from dataclasses import dataclass

from google.adk.agents import LlmAgent
from google import genai

from homeassistant.config_entries import ConfigEntry


@dataclass(frozen=True, kw_only=True)
class RulebookContext:
    """Context for the Rulebook integration."""

    agent: LlmAgent
    client: genai.Client


type RulebookConfigEntry = ConfigEntry[RulebookContext]

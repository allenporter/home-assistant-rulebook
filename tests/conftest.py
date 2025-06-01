"""Fixtures for the custom component."""

from collections.abc import Generator, AsyncGenerator
import logging
from unittest.mock import patch
from typing import Literal
import uuid
from functools import partial

import pytest

from homeassistant.const import Platform, MATCH_ALL
from homeassistant.components import conversation
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry, ConfigEntryState, ConfigFlow
from homeassistant.helpers.entity import Entity
from homeassistant.setup import async_setup_component
from homeassistant.helpers import device_registry as dr, intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    MockPlatform,
    mock_integration,
    mock_platform,
    mock_config_flow,
)

from custom_components.rulebook.const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_RULEBOOK,
)

_LOGGER = logging.getLogger(__name__)


TEST_DOMAIN = "test"
TEST_DEVICE_ID = (TEST_DOMAIN, "some-device-id")
TEST_DEVICE_NAME = "Some Device Name"
TEST_AGENT = "conversation.fake_agent"
TEST_AGENT_NAME = "Llama"
TEST_RULEBOOK = """\
Location: 500 Smith Street, Brooklyn, NY, 11111
People: Mario, Peach and their kids Bowser and Luigi
Preferred temperature: Fahrenheit
Preferred distance: miles
"""
TEST_API_KEY = "test-api-key-1"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None, None, None]:
    """Enable custom integration."""
    _ = enable_custom_integrations  # unused
    yield


@pytest.fixture(name="platforms")
def mock_platforms() -> list[Platform]:
    """Fixture for platforms loaded by the integration."""
    return []


@pytest.fixture(autouse=True)
async def mock_dependencies(
    hass: HomeAssistant,
) -> None:
    """Set up the integration."""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "conversation", {})


@pytest.fixture(name="setup_integration")
async def mock_setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    platforms: list[Platform],
) -> AsyncGenerator[None]:
    """Set up the integration."""

    with patch(f"custom_components.{DOMAIN}.PLATFORMS", platforms):
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
        yield


@pytest.fixture(name="config_entry")
async def mock_config_entry(
    hass: HomeAssistant,
) -> MockConfigEntry:
    """Fixture to create a configuration entry."""
    config_entry = MockConfigEntry(
        options={
            CONF_API_KEY: TEST_API_KEY,
            CONF_RULEBOOK: TEST_RULEBOOK,
        },
        domain=DOMAIN,
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


class FakeAgent(conversation.ConversationEntity):
    """Fake agent."""

    _attr_has_entity_name = True
    _attr_name = TEST_AGENT_NAME

    def __init__(self, entity_id: str) -> None:
        """Initialize FakeAgent."""
        self._attr_unique_id = str(uuid.uuid1())
        self.entity_id = entity_id
        self.conversations: list[str] = []
        self.responses: list[str] = []

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        self.conversations.append(user_input.text)
        response = self.responses.pop() if self.responses else "No response"
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response)
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id,
        )

    async def async_prepare(self, language: str | None = None) -> None:
        """Load intents for a language."""
        return


@pytest.fixture(name="mock_entities")
def mock_entities_fixture() -> dict[Platform, list[Entity]]:
    """Fixture for entities loaded by the integration."""
    return {}


@pytest.fixture(name="test_platforms")
def mock_test_platforms(
    mock_entities: dict[Platform, list[Entity]],
) -> list[Platform]:
    """Fixture for platforms loaded by the integration."""
    return list(mock_entities.keys())


@pytest.fixture(name="test_integration")
def mock_setup_test_integration(
    hass: HomeAssistant, test_platforms: list[Platform]
) -> None:
    """Fixture to set up a mock integration."""

    async def async_setup_entry_init(
        hass: HomeAssistant, config_entry: ConfigEntry
    ) -> bool:
        """Set up test config entry."""
        await hass.config_entries.async_forward_entry_setups(
            config_entry,
            test_platforms,
        )
        return True

    async def async_unload_entry_init(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> bool:
        await hass.config_entries.async_unload_platforms(
            config_entry,
            test_platforms,
        )
        return True

    mock_platform(hass, f"{TEST_DOMAIN}.config_flow")
    mock_integration(
        hass,
        MockModule(
            TEST_DOMAIN,
            async_setup_entry=async_setup_entry_init,
            async_unload_entry=async_unload_entry_init,
        ),
    )


class MockFlow(ConfigFlow):
    """Test flow."""


@pytest.fixture(autouse=True)
async def mock_test_platform_fixture(
    hass: HomeAssistant,
    test_integration: None,
    mock_entities: dict[Platform, list[Entity]],
) -> MockConfigEntry:
    """Create a todo platform with the specified entities."""
    config_entry = MockConfigEntry(domain=TEST_DOMAIN)
    config_entry.add_to_hass(hass)

    mock_platform(hass, f"{TEST_DOMAIN}.config_flow")

    # Create a fake device for associating with entities
    device_registry: dr.DeviceRegistry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        name=TEST_DEVICE_NAME,
        identifiers={TEST_DEVICE_ID},
    )

    for domain, entities in mock_entities.items():

        async def async_setup_entry_platform(
            add_entities: list[Entity],
            hass: HomeAssistant,
            config_entry: ConfigEntry,
            async_add_entities: AddEntitiesCallback,
        ) -> None:
            """Set up test event platform via config entry."""
            async_add_entities(add_entities)

        _LOGGER.info(f"creating mock_platform for={TEST_DOMAIN}.{domain}")

        mock_platform(
            hass,
            f"{TEST_DOMAIN}.{domain}",
            MockPlatform(
                async_setup_entry=partial(async_setup_entry_platform, entities)
            ),
        )

    with mock_config_flow(TEST_DOMAIN, MockFlow):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        assert config_entry.state is ConfigEntryState.LOADED
        return config_entry

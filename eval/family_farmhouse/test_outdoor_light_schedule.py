"""Test for the outdoor light rule."""

import asyncio
from collections.abc import Callable, Generator
import datetime
from typing import NamedTuple
import zoneinfo

from freezegun import freeze_time

import pytest

from homeassistant.core import HomeAssistant, callback
from homeassistant.setup import async_setup_component
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components import sun
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

from pytest_homeassistant_custom_component.common import async_fire_time_changed


LIGHT_ENTITY = "light.porch_light"
LIGHT_TIMEOUT = datetime.timedelta(minutes=5)  # Example timeout
WAIT_TIMEOUT_SEC = 2.0


@pytest.fixture(autouse=True)
async def setup_sun_component(hass: HomeAssistant) -> None:
    """Initialize the sun component."""
    await async_setup_component(hass, sun.DOMAIN, {sun.DOMAIN: {}})


@pytest.fixture(name="light_state_change")
async def light_event_fixture(
    hass: HomeAssistant,
) -> Generator[asyncio.Event]:
    """A fixture for an event that fires when the light state changes."""
    event = asyncio.Event()

    @callback
    async def state_changed(_: datetime.datetime) -> None:
        event.set()

    unsub = async_track_state_change_event(hass, LIGHT_ENTITY, state_changed)
    yield event
    unsub()


class EntityState(NamedTuple):
    """Represents the state and attributes of an entity."""
    state: str
    attributes: dict


class EntityStateFixture:
    """Helper to bind the needed data for getting entity state."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        entity_registry: er.EntityRegistry,
    ) -> None:
        self._hass = hass
        self._config_entry = config_entry
        self._entity_registry = entity_registry

    def get_state(self) -> dict[str, EntityState]:
        """Return the entity entries."""
        results: dict[str, EntityState] = {}
        for entity_entry in er.async_entries_for_config_entry(
            self._entity_registry, self._config_entry.entry_id
        ):
            state = self._hass.states.get(entity_entry.entity_id)
            assert state
            assert state.state
            results[entity_entry.entity_id] = EntityState(
                state=state.state, attributes=dict(state.attributes or {})
            )
            assert state.state not in (
                "unavailable",
                "unknown",
            ), f"Entity id has unavailable state {entity_entry.entity_id}: {state.state}"

        return results


@pytest.fixture(name="get_state")
def get_state_fixture(
    hass: HomeAssistant,
    synthetic_home_config_entry: ConfigEntry,
    entity_registry: er.EntityRegistry,
) -> Callable[[], dict[str, str]]:
    """Fixture that can state for all synthetic home entities."""

    entity_state = EntityStateFixture(
        hass, synthetic_home_config_entry, entity_registry
    )

    def func() -> dict[str, str]:
        return {
            entity_id: state.state
            for entity_id, state in entity_state.get_state().items()
        }

    return func



@pytest.mark.eval
# @pytest.mark.eval_model_outputs(task_id="light_on_at_sunset")
async def test_light_on_at_sunset(
    hass: HomeAssistant,
    get_state: Callable[[], dict[str, str]],
    light_state_change: asyncio.Event,
) -> None:
    """Test that the light is turned on at sunset following the rulebook."""

    states = get_state()
    assert states.get(LIGHT_ENTITY) == "off"

    now = datetime.datetime(2025, 5, 22, 20, 30, tzinfo=zoneinfo.ZoneInfo("America/Chicago"))
    trigger_time = datetime.datetime(2025, 5, 22, 20, 35, tzinfo=zoneinfo.ZoneInfo("America/Chicago"))
    with freeze_time(now):
        async_fire_time_changed(hass, now)
        await hass.async_block_till_done()

        assert not light_state_change.is_set()

        async_fire_time_changed(hass, trigger_time)
        await hass.async_block_till_done()

        try:
            async with asyncio.timeout(WAIT_TIMEOUT_SEC):
                await light_state_change.wait()
        except TimeoutError as err:
            raise TimeoutError("Timeout waiting for light to turn on") from err

    expected_states = {**states, LIGHT_ENTITY: "on"}
    assert get_state() == expected_states

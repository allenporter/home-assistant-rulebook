"""Test for the outdoor light rule."""

import asyncio
from collections.abc import Callable, AsyncGenerator
import datetime
import zoneinfo

from freezegun import freeze_time

import pytest

from homeassistant.core import HomeAssistant, callback
from homeassistant.setup import async_setup_component
from homeassistant.helpers.event import (
    async_track_state_change_event,
    Event,
    EventStateChangedData,
)
from homeassistant.components import sun
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
) -> AsyncGenerator[asyncio.Event]:
    """A fixture for an event that fires when the light state changes."""
    event = asyncio.Event()

    @callback
    async def state_changed(_: Event[EventStateChangedData]) -> None:
        event.set()

    unsub = async_track_state_change_event(hass, LIGHT_ENTITY, state_changed)
    yield event
    unsub()


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.eval_model_outputs(task_id="light_on_at_sunset")
async def test_light_on_at_sunset(
    hass: HomeAssistant,
    get_state: Callable[[], dict[str, str]],
    light_state_change: asyncio.Event,
) -> None:
    """Test that the light is turned on at sunset following the rulebook."""

    states = get_state()
    assert states.get(LIGHT_ENTITY) == "off"

    now = datetime.datetime(
        2025, 5, 22, 20, 30, tzinfo=zoneinfo.ZoneInfo("America/Chicago")
    )
    trigger_time = datetime.datetime(
        2025, 5, 22, 20, 35, tzinfo=zoneinfo.ZoneInfo("America/Chicago")
    )
    with freeze_time(now):
        async_fire_time_changed(hass, now)
        await hass.async_block_till_done()

        assert not light_state_change.is_set()

        async_fire_time_changed(hass, trigger_time)
        await hass.async_block_till_done()

    expected_states = {**states, LIGHT_ENTITY: "on"}
    assert get_state() == expected_states

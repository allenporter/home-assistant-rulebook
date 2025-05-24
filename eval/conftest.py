"""Evaluation tests fixtures."""

from collections.abc import Callable
import pathlib
from importlib.metadata import version

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

from home_assistant_datasets.entity_state import EntityStateFixture

FIXTURES = "_fixtures.yaml"
DATASET_PATH = pathlib.Path(__file__).parent
MODEL_OUTPUT_PATH = DATASET_PATH.parent / "reports"

DEFAULT_MODEL_ID = "gemini-2.5-flash"

pytest_plugins = [
    "home_assistant_datasets.plugins.pytest_synthetic_home",
    "home_assistant_datasets.plugins.pytest_agent",
]


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest."""
    config.option.dataset = str(DATASET_PATH)
    config.option.models = DEFAULT_MODEL_ID

    home_assistant_version = version("homeassistant")
    if not home_assistant_version:
        raise ValueError(
            "Unable to determine home assistant version. "
            "Please specify a model output directory with --model_output_dir"
        )

    config.option.model_output_dir = str(MODEL_OUTPUT_PATH / home_assistant_version)


@pytest.fixture(name="test_path")
def test_path_fixture(request: pytest.FixtureRequest) -> pathlib.Path:
    """Fixture to get the dataset name from the currently running test."""
    return pathlib.Path(request.module.__file__).parent


@pytest.fixture
def synthetic_home_yaml(test_path: pathlib.Path) -> str:
    """Fixture to load synthetic home entities."""
    return (test_path / FIXTURES).read_text()


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

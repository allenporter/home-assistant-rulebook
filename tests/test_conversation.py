"""Tests for the conversation integration."""

from collections.abc import Generator, AsyncGenerator
from unittest.mock import AsyncMock, patch, Mock

from google.genai.errors import APIError, ClientError
from google.genai import types
import httpx
import pytest
import logging

from homeassistant.const import Platform
from homeassistant.components import conversation
from homeassistant.components.google_generative_ai_conversation.conversation import (
    ERROR_GETTING_RESPONSE,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import intent

from pytest_homeassistant_custom_component.common import MockConfigEntry


_LOGGER = logging.getLogger(__name__)

TEST_AGENT_ID = "conversation.mock_title"

API_ERROR_500 = APIError(
    500,
    Mock(
        __class__=httpx.Response,
        json=Mock(
            return_value={
                "message": "Internal Server Error",
                "status": "internal-error",
            }
        ),
    ),
)
CLIENT_ERROR_BAD_REQUEST = ClientError(
    400,
    Mock(
        __class__=httpx.Response,
        json=Mock(
            return_value={
                "message": "Bad Request",
                "status": "invalid-argument",
            }
        ),
    ),
)


@pytest.fixture(name="platforms")
def mock_platforms() -> list[Platform]:
    """Fixture for platforms loaded by the integration."""
    return [Platform.CONVERSATION]


@pytest.fixture(name="mock_send_message_stream")
def mock_send_message_stream_fixture() -> Generator[AsyncMock]:
    """Mock stream response."""

    async def mock_generator(
        stream: Generator[types.GenerateContentResponse, None],
    ) -> AsyncGenerator[types.GenerateContentResponse, None]:
        for value in stream:
            yield value

    with patch(
        "google.genai.chats.AsyncChat.send_message_stream",
        AsyncMock(),
    ) as mock_send_message_stream:
        mock_send_message_stream.side_effect = lambda **kwargs: mock_generator(
            mock_send_message_stream.return_value.pop(0)
        )

        yield mock_send_message_stream


@pytest.mark.parametrize(
    ("error"),
    [
        (API_ERROR_500,),
        (CLIENT_ERROR_BAD_REQUEST,),
    ],
)
@pytest.mark.parametrize("expected_lingering_tasks", [True])
async def test_error_handling(
    hass: HomeAssistant, config_entry: MockConfigEntry, error: Exception
) -> None:
    """Test that client errors are caught."""
    with patch(
        "google.genai.chats.AsyncChat.send_message_stream",
        new_callable=AsyncMock,
        side_effect=error,
    ):
        result = await conversation.async_converse(
            hass,
            "hello",
            None,
            Context(),
            agent_id=TEST_AGENT_ID,
        )
    assert result.response.response_type == intent.IntentResponseType.ERROR, result
    assert result.response.error_code == "unknown", result
    assert (
        result.response.as_dict()["speech"]["plain"]["speech"] == ERROR_GETTING_RESPONSE
    )


@pytest.mark.parametrize("expected_lingering_tasks", [True])
async def test_empty_response(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_send_message_stream: AsyncMock,
) -> None:
    """Test empty response."""

    messages = [
        [
            types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            parts=[],
                            role="model",
                        ),
                        finish_reason=types.FinishReason.STOP,
                    )
                ],
            ),
        ],
    ]

    mock_send_message_stream.return_value = messages

    result = await conversation.async_converse(
        hass,
        "Hello",
        None,
        Context(),
        agent_id=TEST_AGENT_ID,
    )
    assert result.response.response_type == intent.IntentResponseType.ERROR, (
        result
    )
    assert result.response.error_code == intent.IntentResponseErrorCode.UNKNOWN
    assert (
        result.response.as_dict()["speech"]["plain"]["speech"]
        == "Sorry, I had a problem getting a response from the Agent."
    )


@pytest.mark.parametrize("expected_lingering_tasks", [True])
async def test_response(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_send_message_stream: AsyncMock,
) -> None:
    """Test empty response."""

    messages = [
        [
            types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            parts=[
                                types.Part(
                                    text="Hello, how can I help you?",
                                )
                            ],
                            role="model",
                        ),
                        finish_reason=types.FinishReason.STOP,
                    )
                ],
            ),
        ],
    ]

    mock_send_message_stream.return_value = messages

    result = await conversation.async_converse(
        hass,
        "Hello",
        None,
        Context(),
        agent_id=TEST_AGENT_ID,
    )
    assert result.response.response_type == intent.IntentResponseType.ACTION_DONE, (
        result
    )
    assert result.response.error_code is None
    assert (
        result.response.as_dict()["speech"]["plain"]["speech"]
        == "Hello, how can I help you?"
    )



@pytest.mark.parametrize("expected_lingering_tasks", [True])
async def test_multiple_parts(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_send_message_stream: AsyncMock,
) -> None:
    """Test empty response."""

    messages = [
        [
            types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            parts=[
                                types.Part(
                                    text="The capital of",
                                ),
                            ],
                            role="model",
                        ),
                    )
                ],
            ),
            types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            parts=[
                                types.Part(
                                    text=" France is",
                                )
                            ],
                            role="model",
                        ),
                    )
                ],
            ),
            types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            parts=[
                                types.Part(
                                    text=" Paris.",
                                )
                            ],
                            role="model",
                        ),
                        finish_reason=types.FinishReason.STOP,
                    )
                ],
            ),
        ],
    ]

    mock_send_message_stream.return_value = messages

    result = await conversation.async_converse(
        hass,
        "What is the capital of France?",
        None,
        Context(),
        agent_id=TEST_AGENT_ID,
    )
    assert result.response.response_type == intent.IntentResponseType.ACTION_DONE, (
        result
    )
    assert result.response.error_code is None
    assert (
        result.response.as_dict()["speech"]["plain"]["speech"]
        == "The capital of France is Paris."
    )

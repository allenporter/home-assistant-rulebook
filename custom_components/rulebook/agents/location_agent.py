"""Sample agent to answer questions about the time and weather in a city.

This is just a placeholder agent to demonstrate that the framework can work.

The LLM should be able to read the location from the instance, compare it to the
currently configured one and offer user to update their location.
"""

import datetime
import zoneinfo

from google.adk.agents import Agent

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import SUMMARIZE_MODEL


def async_create_agent(hass: HomeAssistant, config_entry: ConfigEntry) -> Agent:
    """Create an agent."""

    return Agent(
        name="weather_time_agent",
        model=SUMMARIZE_MODEL,
        description=("Agent to answer questions about the time and weather in a city."),
        instruction=(
            "You are a helpful agent who can answer user questions about the time and weather in a city."
        ),
        tools=[
            get_weather,
            get_current_time,
        ],
    )


def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city for which to retrieve the weather report.

    Returns:
        dict: status and result or error msg.
    """
    if city.lower() == "new york":
        return {
            "status": "success",
            "report": (
                "The weather in New York is sunny with a temperature of 25 degrees"
                " Celsius (77 degrees Fahrenheit)."
            ),
        }
    else:
        return {
            "status": "error",
            "error_message": f"Weather information for '{city}' is not available.",
        }


def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.

    Returns:
        dict: status and result or error msg.
    """

    if city.lower() == "new york":
        tz_identifier = "America/New_York"
    else:
        return {
            "status": "error",
            "error_message": (f"Sorry, I don't have timezone information for {city}."),
        }

    tz = zoneinfo.ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = f"The current time in {city} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"
    return {"status": "success", "report": report}

"""Data models for home details for the rulebook component."""

from dataclasses import dataclass

from pydantic import BaseModel, Field, ConfigDict


@dataclass(frozen=True, kw_only=True)
class LocationDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")

    description: str | None = Field(
        default=None,
        description="Optional description of the home's location in free-form text.",
    )
    address: str | None = Field(default=None, description="Street address of the home.")
    city: str | None = Field(
        default=None, description="City where the home is located."
    )
    state: str | None = Field(
        default=None, description="State or province where the home is located."
    )
    country: str | None = Field(
        default=None, description="Country where the home is located."
    )
    timezone: str | None = Field(default=None, description="Timezone of the home.")


class BasicInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    home_name: str | None = Field(
        default=None, description="Name of the smart home, if specified."
    )
    default_language: str | None = Field(
        default=None, description="Default language for interactions, if specified."
    )


class Area(BaseModel):
    name: str = Field(description="Name of the area (e.g., 'Living Room', 'Kitchen').")
    description: str | None = Field(
        default=None, description="Optional description of the area."
    )
    floor: str | None = Field(
        default=None, description="Name of the floor this area is located on."
    )


class UtilityProvider(BaseModel):
    name: str = Field(
        description="Name of the utility provider (e.g., 'City Electric', 'Comcast')."
    )
    service_type: str = Field(
        description="Type of service provided (e.g., 'electricity', 'gas', 'internet', 'water')."
    )
    account_details: str | None = Field(
        default=None,
        description="Optional account number or other identifying details.",
    )


class ParsedSmartHomeRule(BaseModel):
    """Data model for a parsed smart home rule (simplified initial pass).

    This model captures the most basic, directly extractable components of a smart home rule
    from a natural language description. More detailed parsing is deferred.
    """

    model_config = ConfigDict(
        extra="ignore"
    )  # Changed to ignore for stricter initial parsing

    rule_raw_text: str = Field(
        description="The original, unprocessed smart home rule text snippet provided by the user."
    )
    rule_name: str | None = Field(
        None,
        description="A descriptive name or summary of the rule, if clearly identifiable in the text.",
    )
    entities_mentioned: list[str] = Field(
        default_factory=list,
        description="List of textual mentions of devices, services, people, or abstract concepts (e.g., 'kitchen light', 'front door sensor', 'sunset', 'weekday') found within the rule snippet.",
    )
    core_logic_text: str | None = Field(
        None,
        description="The core part of the rule text that seems to describe its main trigger, condition, and action logic as a single text block. This will be parsed in more detail later.",
    )

class ParsedHomeDetails(BaseModel):
    # Meta fields about the parsing process
    raw_text: str = Field(
        description="The original, unprocessed rulebook text provided by the user."
    )
    parsed_status: str = Field(
        description="Indicates the outcome of the parsing attempt (e.g., 'completed_successfully', 'failed_validation', 'failed_llm_call')."
    )
    error_message: str | None = Field(
        None, description="Detailed error message if parsing was not successful."
    )

    # Parsed content
    basic_info: BasicInfo | None = Field(
        None, description="Global information about the smart home setup."
    )
    location_details: LocationDetails | None = Field(
        default=None, description="Details about the home's location."
    )
    key_people: list[str] = Field(
        default_factory=list,
        description="Names of key people residing in the home.",
    )
    floor_mentions: list[str] = Field(
        default_factory=list,
        description="List of text mentions of floors found in the rulebook (e.g., 'Ground floor', 'upstairs'). To be structured later.",
    )
    area_mentions: list[str] = Field(
        default_factory=list,
        description="List of text mentions of areas or rooms found in the rulebook (e.g., 'living room', 'kitchen', 'master bedroom'). To be structured later.",
    )
    utility_provider_mentions: list[str] = Field(
        default_factory=list,
        description="List of text mentions of utility providers found in the rulebook (e.g., 'City Electric for power', 'Comcast for internet'). To be structured later.",
    )
    raw_smart_home_rules_text: list[str] = Field(
        default_factory=list,
        description="List of raw text snippets for individual smart home rules identified by the parser.",
    )
    smart_home_rules: list[ParsedSmartHomeRule] = Field(
        default_factory=list,
        description="List of parsed individual smart home rules.",
    )

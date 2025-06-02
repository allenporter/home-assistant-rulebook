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


class Floor(BaseModel):
    name: str = Field(
        description="Name of the floor (e.g., 'Ground floor', 'First floor', 'Basement', 'Second floor')."
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
    key_people: list[str] | None = Field(
        default_factory=list,  # type: ignore[arg-type]
        description="Names of key people residing in the home.",
    )
    floors: list[Floor] = Field(
        default_factory=list,
        description="Named list of floors that exist in the home.",
    )
    areas_and_structure: list[Area] = Field(
        default_factory=list,
        description="List of all areas, rooms, and zones in the home, including their structure and associated devices.",
    )
    utility_providers: list[UtilityProvider] = Field(
        default_factory=list,
        description="Information about utility providers (electricity, gas, internet, etc.).",
    )


class ParsedSmartHomeRule(BaseModel):
    """Data model for a parsed smart home rule.

    This model captures the structured components of a smart home rule
    extracted from a natural language description.
    It includes the rule's name, intent, description, and lists of triggers,
    conditions, and actions, along with the original raw text input.
    """

    model_config = ConfigDict(extra="allow")

    rule_raw_text: str = Field(
        description="The original, unprocessed smart home rules text provided by the user."
    )
    rule_name: str | None = Field(
        None, description="A descriptive name or summary of the rule."
    )
    intent: str | None = Field(
        None, description="The user's overall intent or goal for this rule."
    )
    description: str | None = Field(
        None,
        description="A more detailed natural language description of the rule provided by the user.",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Comprehensive list of unique textual devices and entity mentions (e.g., 'kitchen light', 'front door sensor') found across the rule's natural language description, intent, triggers, conditions, and actions.",
    )
    triggers: list[str] = Field(
        default_factory=list,
        description="List of text descriptions of triggers that initiate the rule.",
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="List of text descriptions of conditions that must be met for the actions to execute.",
    )
    actions: list[str] = Field(
        default_factory=list,
        description="List of text descriptions of actions to perform when triggers and conditions are met.",
    )

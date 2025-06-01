"""Data models for smart home rules.

These contain the rules, triggers, conditions, and actions that define the
behavior of smart home automations.
"""

from pydantic import BaseModel, Field, ConfigDict


# TODO: These rules are not currently in use yet. We may be able to use the
# existing homeassistant automation schema, but we need to ensure that it
# can handle the free-form text input and convert it into structured rules.


class Trigger(BaseModel):
    type: str = Field(
        description="Type of trigger (e.g., 'state', 'event', 'time', 'numeric_state', 'geofence')."
    )
    platform: str | None = Field(
        default=None,
        description="Platform of the trigger (e.g., 'homeassistant', 'mqtt').",
    )
    entity_id: str | None = Field(
        default=None, description="Home Assistant entity ID for state/event triggers."
    )
    event_type: str | None = Field(
        default=None, description="Event type for event triggers."
    )
    from_state: str | None = Field(
        default=None, description="Previous state for state triggers."
    )
    to_state: str | None = Field(
        default=None, description="Target state for state triggers."
    )
    at: str | None = Field(
        default=None, description="Time for time-based triggers (e.g., 'HH:MM:SS')."
    )
    # Add other relevant fields for different trigger types


class Condition(BaseModel):
    condition: str = Field(
        description="Type of condition (e.g., 'state', 'numeric_state', 'time', 'and', 'or', 'not')."
    )
    entity_id: str | None = Field(
        default=None,
        description="Home Assistant entity ID for state/numeric_state conditions.",
    )
    state: str | None = Field(
        default=None, description="Target state for state conditions."
    )
    above: float | None = Field(
        default=None, description="Threshold for numeric_state condition (above)."
    )
    below: float | None = Field(
        default=None, description="Threshold for numeric_state condition (below)."
    )
    after: str | None = Field(
        default=None, description="Time for time-based conditions (after HH:MM:SS)."
    )
    before: str | None = Field(
        default=None, description="Time for time-based conditions (before HH:MM:SS)."
    )
    weekday: list[str] | None = Field(
        default_factory=list,  # type: ignore[arg-type]
        description="Days of the week for time conditions.",
    )
    # conditions: list["Condition"] | None = Field(
    #     default_factory=list,
    #     description="For 'and', 'or', 'not' conditions, a list of sub-conditions.",
    # )
    # Add other relevant fields


class Action(BaseModel):
    action_type: str = Field(
        description="Type of action (e.g., 'call_service', 'activate_scene', 'send_notification', 'wait')."
    )
    service: str | None = Field(
        None,
        description="Service to call (e.g., 'light.turn_on', 'notify.mobile_app').",
    )
    entity_id: str | None = Field(
        None, description="Target entity/entities for the action."
    )
    # TODO: Schema cannot handle free-form dictionaries
    # data: dict[str, Any] | None = Field(default_factory=dict, description="Data payload for the service call or action.")
    scene: str | None = Field(
        None, description="Scene to activate (e.g., 'scene.movie_mode')."
    )
    message: str | None = Field(None, description="Message for notifications.")
    # Add other relevant fields


class SmartHomeRule(BaseModel):
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
    entities_referenced: list[str] = Field(
        default_factory=list,
        description="List of Home Assistant entity IDs explicitly or implicitly referenced in the rule's natural language description.",
    )
    triggers: list[Trigger] = Field(
        default_factory=list, description="List of triggers that initiate the rule."
    )
    conditions: list[Condition] = Field(
        default_factory=list,
        description="List of conditions that must be met for the actions to execute.",
    )
    actions: list[Action] = Field(
        default_factory=list,
        description="List of actions to perform when triggers and conditions are met.",
    )


class ParsedSmartHomeRules(BaseModel):
    model_config = ConfigDict(extra="allow")
    raw_text: str = Field(
        description="The original, unprocessed smart home rules text provided by the user."
    )
    smart_home_rules: list[SmartHomeRule] = Field(
        default_factory=list,
        description="List of all parsed smart home rules, automations, and scenes.",
    )

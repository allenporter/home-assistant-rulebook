<!-- filepath: /workspaces/home-assistant-rulebook/docs/DESIGN.md -->

# Rulebook Design

This describes the components in the rulebook.

## 1. Overview

The Rulebook project aims to simplify smart home management within Home Assistant. Users will create a natural language "rule book" document outlining their desired home configuration, devices, and automations. A Large Language Model (LLM) will parse this rule book and the current Home Assistant instance's state. It will then provide actionable suggestions and assistance to the user to align their smart home with the rule book, automating setup and configuration where possible.

## 2. Core Components

This section will detail the primary architectural components of the Rulebook system.

### 2.1. Rulebook Parser

The Rulebook Parser is responsible for taking the user-provided text for their rule book as input and transforming it into a structured representation that the LLM Agent(s) can understand and act upon. The primary mechanism for this parsing will be a capable Large Language Model.

**Input:** User-provided text describing their smart home configuration, preferences, and rules. This text may be free-form or loosely structured (e.g., using Markdown-like conventions, but not strictly enforced). An example is `RULEBOOK_EXAMPLE.md`.

**Output:** A structured data format (e.g., a Python dictionary or a set of data classes) representing:
_ **Basic Information:** Location, preferred units (temperature, distance), list of people.
_ **Areas and Structure:** Hierarchical representation of floors, rooms, and their connections.
_ **Utility Providers:** Information about energy, water, and gas providers.
_ **Smart Home Rules:** A list of desired automations or states, with key elements extracted (e.g., triggers, conditions, actions, entities involved, desired states).

**Processing Steps:**

1.  **Initial LLM Call(s) for Global Structure and Simpler Sections:**

    - The user-provided text is first processed to identify and extract broader sections like "Basic Information" (location, people, preferences), "Areas and Structure" (floors, rooms), and "Utility Providers."
    - This might involve one LLM call with a prompt asking it to identify these sections and return their content in a structured format (e.g., JSON). The prompt should also instruct the LLM to return the raw text block(s) corresponding to "Smart Home Rules."
    - Alternatively, if these sections are typically demarcated by common headings, preliminary text processing could isolate these blocks, which are then sent to the LLM with more targeted prompts for each block.

2.  **Dedicated LLM Call for Each Smart Home Rule:**

    - The system will iterate through each identified "Smart Home Rule" (obtained as a text snippet from the step above).
    - For each individual rule, a separate, focused LLM call (via `google.genai` client) will be made.
    - The prompt for this call will instruct the LLM to parse that single rule and extract its core components:
      - **Intent:** The primary goal of the rule.
      - **Entities:** Devices, locations, people involved.
      - **Triggers:** What causes the rule to activate.
      - **Conditions:** Circumstances that must be true for the rule to run.
      - **Actions:** What the rule should do.
      - **Desired States/Attributes:** Specific states or attributes for entities (e.g., "light should not be too bright").
    - The LLM will be prompted to return this information for the single rule in a consistent, structured format (e.g., JSON).

3.  **Aggregation and Normalization:**
    - The structured outputs from all LLM calls (for global sections and individual rules) are aggregated.
    - The aggregated data might undergo a light normalization step (e.g., standardizing date/time formats if not consistently handled by the LLM).
    - Basic validation could check for the presence of key expected fields.
    - If significant ambiguities or missing critical information are detected, the system might need to engage the user for clarification via the Conversation Interface.

**Rationale for this Approach:**

- **Manages Complexity:** Avoids an overly complex single prompt. Parsing individual rules is a distinct, complex sub-task.
- **Reliability & Error Isolation:** Prompts for individual rules can be more targeted. If parsing one rule fails, it doesn\'t necessarily invalidate the parsing of other rules or the basic info.
- **Scalability:** Handles a variable number of rules cleanly.
- **Focused Prompts:** Allows for more precise prompt engineering for different types of information.

**Potential Challenges:**
_ **Prompt Engineering:** Crafting prompts that reliably extract all necessary information accurately and in the desired structure from varied free-form text.
_ **Ambiguity in Natural Language:** LLMs can still struggle with highly ambiguous phrasing.
_ **Mapping to Home Assistant:** Ensuring the LLM's interpretation of devices, areas, and entities can be later mapped to actual Home Assistant constructs.
_ **Consistency:** Ensuring the LLM provides output in a consistent structure across different rule books and phrasings. \* **Handling Incomplete or Malformed Input:** The LLM needs to be robust enough or the surrounding logic needs to handle cases where the rule book is poorly written or incomplete.

**Tools/Technologies:**
_ Python for overall orchestration.
_ Google Generative AI (`google.genai`) as the primary engine for parsing and structuring the rule book text.

This parsed and structured representation of the rule book will then be passed to the LLM Agent(s) and the Home Assistant Interaction Layer to compare with the current state of the smart home and identify discrepancies or actions to be taken.

### 2.2. Home Assistant Interaction Layer

This layer is responsible for all direct communication with the Home Assistant instance. It will fetch current state information from Home Assistant and execute changes or actions as directed by the LLM Agent(s) based on the parsed rulebook.

**Key Responsibilities:**

1.  **Reading Home Assistant State:**

    - **Configuration Data:**
      - Current instance location (latitude, longitude, elevation, time zone).
      - Home Assistant version.
      - Loaded integrations and components.
    - **Registries:**
      - **Area Registry:** Fetch all defined areas, their names, and IDs (`homeassistant.helpers.area_registry`).
      - **Device Registry:** Fetch all registered devices, their associated areas, integrations, manufacturers, and models (`homeassistant.helpers.device_registry`).
      - **Entity Registry:** Fetch all registered entities, their unique IDs, platform, device ID, area ID, and capabilities (`homeassistant.helpers.entity_registry`).
    - **Entity States:**
      - Current states of all entities (`hass.states.async_all()`, `hass.states.async_get(entity_id)`).
      - Attributes of entities.
    - **User Information:**
      - List of persons defined in Home Assistant (`hass.states.async_all("person")` or via person component data).
    - **Automations:**
      - Read existing automation configurations. This will likely involve reading `automations.yaml` (or other included automation YAML files using `hass.config.path("automations.yaml")`) and parsing the YAML. It may also involve inspecting loaded automation data if available through `hass.data`.
    - **Services:**
      - List available services (`hass.services.async_services()`).

2.  **Executing Actions & Making Changes in Home Assistant:**
    - The decision to execute these actions can be triggered in two main ways:
      1.  **User approval via the Repairs system** (`homeassistant.helpers.issue_registry`): For system-initiated suggestions or changes the user wishes to review asynchronously.
      2.  **Direct user confirmation within an interactive chat session** via the Conversation Interface (facilitated by the LLM Agent using the ADK framework).
    - Many proposed changes, especially to configurations and automations, can be surfaced to the user via Home Assistant's **Repairs** system (`homeassistant.helpers.issue_registry`) or proposed directly during a chat conversation. This provides user visibility and control before changes are applied.
    - **Configuration Changes:**
      - **Location:** If a mismatch is detected, a Repair issue or interactive suggestion will guide the user.
      - **Areas:** Suggestions for creating/modifying areas can be presented via Repair or chat. If confirmed, use `area_registry.async_create()`, etc.
      - **Device/Entity Area Assignment:** Suggestions for changes can be presented as Repair issues or via chat.
    - **People Management:**
      - If a person in the rulebook is not a `person` entity in HA, a Repair issue or chat suggestion will guide the user.
    - **Integration Setup:**
      - If the rulebook implies a need for an unconfigured integration, a Repair issue or chat suggestion will guide the user.
    - **Automation Management (Leveraging Repairs, Interactive Chat, and a dedicated file):**
      - **Identifying Automations:** Automations will be given a unique `id` or a `rulebook_id` within their YAML structure, managed in `config/rulebook_automations.yaml`.
      - **Create Automations:**
        1.  The LLM Agent generates the proposed YAML.
        2.  A Repair issue is created or a chat suggestion is made: "Rulebook suggests new automation: [Name/Description]. View and approve?"
        3.  If approved by the user (via Repair flow or chat confirmation), the Interaction Layer adds the YAML to `config/rulebook_automations.yaml` and calls `automation.reload`.
      - **Update Automations:**
        1.  The LLM Agent generates the updated YAML.
        2.  A Repair issue or chat suggestion is made: "Rulebook suggests updating automation: [Name/Description]. View changes and approve?"
        3.  If approved (via Repair or chat), the Interaction Layer modifies the YAML and calls `automation.reload`.
      - **Delete Automations:** If a rulebook rule is removed, a Repair issue or chat suggestion can propose removing the linked automation.
      - **Documenting Existing Automations:** If an automation exists in HA but not in the rulebook, a Repair issue or chat suggestion can propose: "Found un-documented automation: [Name]. Add to Rulebook?"
      - After any YAML changes to automations, trigger the `automation.reload` service call (`hass.services.async_call("automation", "reload", {})`).
    - **Calling Services:**
      - Execute any Home Assistant service call (`hass.services.async_call(domain, service, service_data)`). This is fundamental for actions like turning lights on/off, sending notifications, etc., as dictated by automations or direct instructions.
    - **Notifications:**
      - Send notifications to the user (e.g., via `persistent_notification.create` or other notification services) to inform them of actions taken, suggestions, or errors.

**Implementation Details:**

- All interactions will be performed asynchronously using Home Assistant\'s `async` methods.
- The `hass` (HomeAssistant core object) instance, available to the integration, will be the primary entry point for all interactions.
- Error handling is crucial: gracefully handle unavailable services, incorrect entity IDs, permission issues, and provide feedback to the LLM agent/user.
- This layer will need to carefully map entities and concepts from the rulebook (e.g., "the kitchen light") to specific Home Assistant entity IDs. This mapping might involve:
  - Exact matches if the rulebook uses known entity IDs.
  - Fuzzy matching based on names and areas (potentially with LLM assistance for disambiguation).
  - User clarification via the Conversation Interface if ambiguity cannot be resolved.

**Considerations for Automation Management:**

- To avoid conflicts and ensure clarity, this integration will strongly recommend and facilitate managing its automations in a separate YAML file (e.g., `config/rulebook_automations.yaml`). The user would include this in their main `configuration.yaml` (e.g., `automation rulebook: !include rulebook_automations.yaml`).
- The Interaction Layer would then primarily read from and write to this dedicated file when creating/updating automations, often triggered via the **Repairs** system.
- The LLM agent is responsible for generating the automation YAML content based on the parsed rulebook.
- A mechanism to uniquely identify and link automations in the YAML file to their corresponding rules in the rulebook (e.g., a `rulebook_id` field in the automation YAML) is crucial for updates and deletions.

This layer acts as the "hands and eyes" of the Rulebook system within Home Assistant.

### 2.3. LLM Agent(s)

This component is the "brain" of the Rulebook system. It utilizes the Google Agent Development Kit (ADK) and Google's Generative AI models to interpret the parsed rulebook, compare it with the current Home Assistant state, make decisions, and interact with the user.

**Guiding Principles:**

The LLM Agent(s) and their interactions with the user via the Conversation Interface will adhere to the following principles:

1.  **Clarity and Transparency:** The agent will clearly communicate its understanding, intentions, and the reasoning behind its suggestions or proposed actions. Users should understand what the agent is about to do and why.
2.  **User Control and Explicit Confirmation:** The user will always have the final say. The agent must request explicit confirmation from the user before making any changes to the Home Assistant configuration, creating automations, or calling services that have an external effect. "Ask, don't just do."
3.  **Efficiency and Conciseness:** Interactions will be designed to be as efficient and to the point as possible, minimizing unnecessary dialogue while ensuring clarity.
4.  **Graceful Error Handling and Recovery:** When errors occur (e.g., inability to parse a rule, failure to execute an action), the agent will inform the user clearly and, where possible, offer suggestions for recovery or alternative actions.
5.  **Contextual Awareness:** The agent will strive to maintain and utilize the conversational context to provide relevant and coherent interactions, remembering previous turns and user preferences within a session.
6.  **Reversibility and Safety:** While not all actions can be perfectly undone, the system will favor approaches that allow for easy reversal (e.g., disabling a newly created automation, providing YAML for manual rollback). Changes will be made in a way that minimizes risk to the user's existing setup. For instance, new automations will be added to a dedicated `rulebook_automations.yaml` file.
7.  **Feedback and Progress Indication:** The user will be kept informed about the status of longer-running operations or when the agent is processing information.

**Core Structure (based on `google.adk.agents`):**

1.  **Primary Coordinator Agent (`LlmAgent`):**

    - As seen in `custom_components/rulebook/agents/__init__.py`, a central `LlmAgent` (e.g., named "Coordinator") will be instantiated.
    - This agent is responsible for the overall orchestration of tasks and may delegate specific responsibilities to sub-agents.
    - It will be configured with a primary generative model (e.g., Gemini via `google.genai.Client` initialized in `custom_components/rulebook/__init__.py`).

2.  **Specialized Sub-Agents (`Agent` or `LlmAgent`):**
    - The Coordinator agent will manage a collection of sub-agents, each potentially specialized for a domain outlined in `REQUIREMENTS.md` (e.g., location, people, utilities, areas, automations).
    - The existing `custom_components/rulebook/agents/location_agent.py` serves as a template for such sub-agents.
    - Each sub-agent will have its own description, instructions, and a set of tools relevant to its domain.

**Key Responsibilities:**

1.  **Processing Inputs:**

    - Receives the structured data from the **Rulebook Parser** (Section 2.1).
    - Receives current state information from Home Assistant via the **Home Assistant Interaction Layer** (Section 2.2) – often by invoking tools that call functions in that layer.

2.  **Decision Making & Logic:**

    - **Comparison:** Compares the desired state (from the rulebook) with the actual state (from Home Assistant).
    - **Identifying Discrepancies:** Pinpoints differences, missing configurations, or misalignments.
    - **Formulating Suggestions:** Decides on appropriate actions (e.g., suggest creating an area, updating an automation, installing an integration).
    - **Generating Content:** For tasks like creating automations, the relevant agent will generate the necessary YAML content based on the parsed rulebook rule.
    - **Prioritization:** May need to prioritize which issues or suggestions to present to the user first.

3.  **User Interaction Management (via Conversation Interface - Section 2.4):**

    - Manages the dialogue flow with the user during interactive chat sessions.
    - Presents findings, suggestions, and questions to the user.
    - Processes user responses and confirmations.
    - Uses the ADK's session management (e.g., `InMemorySessionService` as seen in `custom_components/rulebook/conversation.py`) to maintain context across conversational turns.

4.  **Action Orchestration:**

    - Decides whether to:
      - Propose an immediate action in the chat for user confirmation.
      - Create a Repair issue via the **Home Assistant Interaction Layer** for asynchronous user review.
    - Instructs the **Home Assistant Interaction Layer** to execute approved actions (e.g., write YAML to a file, call a service, create an area).

5.  **Tool Usage:**
    - Agents (Coordinator or sub-agents) will be equipped with **tools**. These are Python functions that the LLM can decide to call to get information or perform actions.
    - Examples of tools:
      - `get_home_assistant_areas()`: Calls the HA Interaction Layer.
      - `get_home_assistant_automations()`: Calls the HA Interaction Layer.
      - `generate_automation_yaml(rule_details)`: Might be an internal tool or a direct LLM capability to translate a parsed rule into HA automation YAML.
      - `create_repair_issue(title, description, issue_id)`: Calls the HA Interaction Layer.
      - `add_automation_to_file(yaml_content)`: Calls the HA Interaction Layer.
    - The `location_agent.py` with its `get_weather` and `get_current_time` tools demonstrates the pattern.

**Interaction Flow Example (Automation Suggestion):**

1.  Rulebook Parser provides a structured rule: "Turn on living room lamp at sunset."
2.  Coordinator Agent (or a dedicated Automation Sub-Agent) receives this.
3.  Agent uses a tool (e.g., `get_home_assistant_automations(entity_id='light.living_room_lamp')`) to check if a similar automation exists via the HA Interaction Layer.
4.  If no such automation exists, the Agent decides to suggest creating one.
5.  During a chat session (via Conversation Interface), the Agent asks the user: "I see a rule to turn on the living room lamp at sunset, but no automation exists. Would you like me to create it?"
6.  User confirms.
7.  Agent (possibly using another tool or its own generation capability) formulates the automation YAML.
8.  Agent uses a tool like `add_automation_to_file_and_reload(yaml_content)` which calls the HA Interaction Layer.
9.  Agent informs the user of the successful creation.

**Technologies:**

- Google Agent Development Kit (ADK): `LlmAgent`, `Agent`, session management.
- Google Generative AI: The underlying LLM accessed via `google.genai.Client`.
- Python: For defining tools and agent logic.

This agent system, leveraging the ADK, forms the core intelligence, managing the dialogue and the lifecycle of aligning the user's rulebook with their Home Assistant setup.

### 2.4. Conversation Interface

(To be detailed: How the user interacts with the system via Home Assistant's conversation and assist pipeline.)

This interface will be the primary channel for the LLM Agent(s) to communicate with the user, present findings, ask for clarifications, and request confirmations for actions. The design of this interface will strictly adhere to the Guiding Principles outlined in Section 2.3.

**Key characteristics will include:**

- **Clear Prompts:** Questions and suggestions posed to the user will be unambiguous.
- **Actionable Choices:** When presenting options or asking for confirmation, the choices available to the user will be clear (e.g., "Yes, create automation," "No, don't create," "Tell me more").
- **Reference to Rulebook:** When discussing a specific rule or configuration, the agent should be able to reference the relevant part of the user's rulebook.
- **Integration with Repairs System:** For non-interactive suggestions or issues that can be addressed asynchronously, the Conversation Interface can guide the user to check the Home Assistant Repairs system.

## 3. Data Flow

(To be detailed: Diagrams and descriptions of how data flows between components for key use cases outlined in REQUIREMENTS.md, e.g., location configuration, automation management.)

## 4. Key Design Decisions

(To be detailed: Significant architectural or technological choices, e.g., specific LLM models, error handling strategies, state management for long-running interactions.)

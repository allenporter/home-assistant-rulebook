<!-- filepath: /workspaces/home-assistant-rulebook/docs/DESIGN.md -->

# Rulebook Design

This describes the components in the rulebook.

## 1. Overview

The Rulebook project aims to simplify smart home management within Home Assistant. Users will create a natural language "rule book" document outlining their desired home configuration, devices, and automations. A Large Language Model (LLM) will parse this rule book and the current Home Assistant instance's state. It will then provide actionable suggestions and assistance to the user to align their smart home with the rule book, automating setup and configuration where possible.

## 2. Core Components

This section will detail the primary architectural components of the Rulebook system.

### 2.1. Rulebook Parsing Process

The Rulebook Parsing Process is responsible for taking the user-provided text for their rule book as input and transforming it into a structured representation that the Coordinator LLM Agent can understand and act upon. This process is orchestrated by the **Rulebook Parser Agent** (detailed in 2.1.1).

**Input:** User-provided text describing their smart home configuration, preferences, and rules. This text may be free-form or loosely structured (e.g., using Markdown-like conventions, but not strictly enforced). An example is `RULEBOOK_EXAMPLE.md`.

**Output:** A structured data format (e.g., a Python dictionary or a set of data classes) representing:
_ **Basic Information:** Location, preferred units (temperature, distance), list of people.
_ **Areas and Structure:** Hierarchical representation of floors, rooms, and their connections.
_ **Utility Providers:** Information about energy, water, and gas providers.
_ **Smart Home Rules:** A list of desired automations or states, with key elements extracted (e.g., triggers, conditions, actions, entities involved, desired states). The specific structure for these rules is defined by the `ParsedSmartHomeRule` model in `custom_components/rulebook/data/home.py`.

The core of this process involves leveraging a capable Large Language Model, accessed via the HA LLM Task and the LLM Shim, to interpret the natural language input.

### 2.1.1. Rulebook Parser Agent

This specialized agent is responsible for executing the Rulebook Parsing Process. It is managed by the Coordinator LLM Agent and is invoked when a new rulebook is provided or an existing one is updated. Its code will reside in `custom_components/rulebook/agents/rulebook_parser_agent.py`.

**Agent Type:** Likely an `Agent` from the Google ADK, as it performs a specific, well-defined task that might not require maintaining a long conversational state itself, but rather processes input and returns structured output. It could also be an `LlmAgent` if its internal logic benefits from direct LLM prompting for orchestration.

**Key Responsibilities & Processing Steps:**

1.  **Receive Rulebook Text:**

    - The agent is activated by the Coordinator Agent, which passes the raw rulebook text as input.

2.  **Initial LLM Call(s) for Global Structure and Simpler Sections:**

    - The agent formulates a prompt (or series of prompts) for the LLM (via the LLM Shim and HA LLM Task).
    - **Prompt Goal:** Identify and extract broader sections like "Basic Information" (location, people, preferences), "Areas and Structure" (floors, rooms), and "Utility Providers."
    - **LLM Interaction:** The prompt instructs the LLM to return this content in a structured format (e.g., JSON) and to also return the raw text block(s) corresponding to "Smart Home Rules."
    - Alternatively, if these sections are typically demarcated by common headings, the agent might perform preliminary text processing to isolate these blocks, then send them to the LLM with more targeted prompts for each block.

3.  **Dedicated LLM Call for Each Smart Home Rule:**

    - The agent iterates through each identified "Smart Home Rule" text snippet obtained from the previous step.
    - For each individual rule, it makes a separate, focused LLM call (via the LLM Shim and HA LLM Task).
    - **Prompt Goal:** Parse the single rule and extract its core components, aiming to populate an instance of the `ParsedSmartHomeRule` model (defined in `custom_components/rulebook/data/home.py`):
      - Intent: The primary goal of the rule.
      - Entities: Devices, locations, people involved.
      - Triggers: What causes the rule to activate.
      - Conditions: Circumstances that must be true for the rule to run.
      - Actions: What the rule should do.
      - Desired States/Attributes: Specific states or attributes for entities (e.g., "light should not be too bright").
    - **LLM Interaction:** The LLM is prompted to return this information for the single rule in a consistent, structured format (e.g., JSON).

4.  **Aggregation and Normalization:**

    - The agent aggregates the structured outputs from all LLM calls (for global sections and individual rules).
    - It may perform light normalization (e.g., standardizing date/time formats if not consistently handled by the LLM).
    - Basic validation checks for the presence of key expected fields.

5.  **Return Structured Data:**
    - The agent returns the complete, structured representation of the rulebook to the Coordinator Agent.
    - If significant ambiguities or missing critical information are detected during parsing, the Rulebook Parser Agent might flag these issues in its response, enabling the Coordinator Agent to engage the user for clarification via the Conversation Interface.

**Rationale for this Agent-based Approach:**

- **Modularity:** Encapsulates the complex parsing logic into a dedicated component, aligning with the ADK's agent-based architecture.
- **Clear Responsibility:** The Coordinator Agent delegates parsing, keeping its own logic focused on higher-level orchestration.
- **Leverages ADK Structure:** Can utilize ADK tools and conventions if beneficial, even if it's not directly conversational.
- **Consistent LLM Interaction:** Uses the same LLM Shim and HA LLM Task mechanism as other agents for all LLM communications.

**Potential Challenges for this Agent:**
_ **Prompt Engineering:** Crafting robust prompts for the LLM Shim that reliably extract all necessary information accurately and in the desired structure from varied free-form text, adaptable to different underlying LLMs.
_ **Error Handling:** Managing LLM errors or unexpected output formats gracefully.
\_ **State (if any):** While primarily a processor, complex rulebooks might require the agent to manage intermediate state during a multi-step parsing operation for a very large rulebook, though the goal is to be stateless per invocation if possible.

**Tools/Technologies Used by this Agent:**
_ Python for agent logic.
_ Google Agent Development Kit (ADK) for the agent structure (`Agent` or `LlmAgent`).
\_ The LLM Shim to communicate with the Home Assistant "LLM Task" feature.

This agent acts as the primary interpreter of the user's raw rulebook, transforming it into actionable data for the rest of the system.

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

This component is the "brain" of the Rulebook system. It utilizes the Google Agent Development Kit (ADK) to structure the agent logic. For LLM interactions, it will communicate through a custom "LLM Shim" that interfaces with Home Assistant's upcoming "LLM Task" feature, allowing use of various underlying LLMs.

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

    - As seen in `custom_components/rulebook/agents/__init__.py`, a central `LlmAgent` (e.g., named "Coordinator") will be instantiated using the Google ADK.
    - This agent is responsible for the overall orchestration of tasks and may delegate specific responsibilities to sub-agents.
    - It will interact with LLMs for generative tasks via the "LLM Shim," which routes requests to the configured Home Assistant "LLM Task."

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

- Google Agent Development Kit (ADK): `LlmAgent`, `Agent`, session management for the core agent framework.
- Home Assistant "LLM Task": The HA mechanism for invoking user-configured LLM services.
- LLM Shim: A custom Python component responsible for translating requests from the ADK-based agents to the HA LLM Task interface and processing responses.
- Python: For defining tools, agent logic, and the LLM Shim.

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

This section describes how data moves between the core components for key operational scenarios.

### 3.1. Initial Rulebook Processing and Setup

This flow describes the process from when a user provides or updates their rulebook text to when the system has parsed it and is ready to offer suggestions or make changes.

1.  **User Input:**

    - **Data:** User's rulebook text (e.g., Markdown content).
    - **Source:** User provides/edits the rulebook via a Home Assistant configuration flow or options flow.
    - **Destination:** Stored in the config entry options.

2.  **Rulebook Parsing:**

    - **Component:** Rulebook Parser.
    - **Input Data:** Raw rulebook text.
    - **Processing:**
      - The Parser uses LLM calls (as detailed in Section 2.1) to transform the text into a structured format.
      - This involves identifying sections (Basic Info, Areas, Utilities) and individual Smart Home Rules (Triggers, Conditions, Actions, Entities).
    - **Output Data:** Structured representation of the rulebook (e.g., Python dictionary/objects).
    - **Destination:** LLM Agent(s).

3.  **State Comparison and Suggestion Formulation:**

    - **Component:** LLM Agent(s), Home Assistant Interaction Layer.
    - **Input Data:**
      - Structured rulebook data (from Rulebook Parser).
      - Current Home Assistant state (fetched by LLM Agent(s) using tools that call the Home Assistant Interaction Layer). This includes entity states, area configurations, existing automations, etc.
    - **Processing:**
      - The LLM Agent(s) compare the desired state (from the rulebook) with the actual HA state.
      - Discrepancies, potential new configurations, or automations are identified.
      - The Agent formulates suggestions or plans for changes.
    - **Output Data:**
      - A set of proposed changes, suggestions, or questions for the user.
      - Data for creating Repair issues (if applicable).
    - **Destination:** Conversation Interface (for interactive suggestions) or Home Assistant Interaction Layer (to create Repair issues).

4.  **User Interaction and Confirmation:**

    - **Component:** Conversation Interface, LLM Agent(s), User.
    - **Input Data:** Proposed changes/suggestions from the LLM Agent.
    - **Processing:**
      - The Conversation Interface presents suggestions to the user (e.g., "Rulebook says your office is on the second floor, but it's not defined in HA. Create it?").
      - User provides confirmation or clarification.
    - **Output Data:** User's decision (e.g., approval, denial, modified request).
    - **Destination:** LLM Agent(s).

5.  **Action Execution:**
    - **Component:** LLM Agent(s), Home Assistant Interaction Layer.
    - **Input Data:** Approved actions from the user.
    - **Processing:**
      - The LLM Agent instructs the Home Assistant Interaction Layer to perform the confirmed actions (e.g., create an area, generate automation YAML and add it to `rulebook_automations.yaml`, call `automation.reload`).
    - **Output Data:** Status of the action (success/failure).
    - **Destination:** LLM Agent(s) (which may then inform the user via the Conversation Interface).

### 3.2. User-Initiated Conversation (e.g., "What automations control the living room lights?")

This flow describes how the system handles a direct query or command from the user via the Home Assistant conversation system.

1.  **User Query/Command:**

    - **Data:** User's natural language input.
    - **Source:** Home Assistant Assist Pipeline (voice or text).
    - **Destination:** Rulebook's Conversation Agent (registered with HA).

2.  **Intent Recognition and Processing:**

    - **Component:** Conversation Interface, LLM Agent(s) (specifically the primary coordinator agent).
    - **Input Data:** User's natural language input.
    - **Processing:**
      - The ADK framework, along with the LLM, processes the input to understand the user's intent and extract relevant entities.
      - The Coordinator LLM Agent may delegate to specialized sub-agents if the query pertains to a specific domain (e.g., a `LightingAgent` or `AutomationAgent`).
      - The Agent(s) may use tools to fetch necessary information from:
        - The structured rulebook data (if relevant to the query, e.g., "What does my rulebook say about...")
        - The Home Assistant Interaction Layer (e.g., to get current states, list automations).
    - **Output Data:** A formulated response or a proposed action.
    - **Destination:** Conversation Interface (to present to the user) or Home Assistant Interaction Layer (if an action needs to be taken after confirmation).

3.  **Response Generation and Delivery:**
    - **Component:** LLM Agent(s), Conversation Interface.
    - **Input Data:** Formulated response or action plan.
    - **Processing:**
      - The LLM Agent generates a natural language response.
      - If an action is proposed (e.g., "I found an automation. Would you like to disable it?"), the flow might merge with steps 4 & 5 of the "Initial Rulebook Processing" flow for confirmation and execution.
    - **Output Data:** Natural language response to the user.
    - **Destination:** User (via Home Assistant Assist Pipeline).

### 3.3. Data Flow for Automation Management (Creation/Update)

This flow focuses on how automations defined in the rulebook are translated into Home Assistant.

1.  **Rule Identification:**

    - **Source:** Rulebook Parser identifies a "Smart Home Rule" that implies an automation.
    - **Data:** Structured rule (trigger, conditions, actions, entities).
    - **Destination:** LLM Agent(s) (e.g., an `AutomationAgent`).

2.  **Automation YAML Generation:**

    - **Component:** LLM Agent(s).
    - **Input Data:** Structured rule.
    - **Processing:** The Agent (or a dedicated tool it uses) translates the structured rule into Home Assistant compatible automation YAML. This includes assigning a unique `rulebook_id`.
    - **Output Data:** Automation YAML string.
    - **Destination:** LLM Agent(s) (held internally, ready for proposal).

3.  **Proposal and Confirmation (via Chat or Repairs):**

    - **Scenario A: Interactive Chat**
      - **Component:** LLM Agent(s), Conversation Interface, User.
      - **Processing:** Agent proposes creating/updating the automation. User confirms.
    - **Scenario B: Repairs System**
      - **Component:** LLM Agent(s), Home Assistant Interaction Layer, User.
      - **Processing:** Agent instructs Interaction Layer to create a Repair issue with the proposed YAML. User reviews and approves via the Repairs UI.
    - **Data:** Automation YAML, user confirmation.

4.  **Saving Automation and Reloading:**
    - **Component:** Home Assistant Interaction Layer.
    - **Input Data:** Confirmed automation YAML.
    - **Processing:**
      - The Interaction Layer writes/updates the automation YAML in the dedicated `config/rulebook_automations.yaml` file.
      - It then calls the `automation.reload` service.
    - **Output Data:** Status of file write and reload.
    - **Destination:** LLM Agent(s) (for potential feedback to the user).

This provides a high-level view of data movement. Specific API calls and detailed data structures are defined by the respective components.

## 4. Key Design Decisions

This section outlines significant architectural and technological choices made during the design of the Rulebook system, along with their rationale.

1.  **LLM-First Approach for Rulebook Parsing:**

    - **Decision:** Utilize a Large Language Model (LLM) as the primary mechanism for parsing the user's natural language rulebook (Section 2.1). This involves a hybrid strategy: initial LLM call(s) for global structure and simpler sections, followed by dedicated LLM calls for each smart home rule.
    - **Rationale:** Provides maximum flexibility for users to express their rules in free-form text. Handles the inherent ambiguity and variability of natural language better than traditional parsing techniques. The hybrid approach balances complexity and reliability.
    - **Technology:** Home Assistant "LLM Task" (allowing user-selected LLMs) accessed via a custom "LLM Shim".

2.  **Dedicated Automation File (`rulebook_automations.yaml`):**

    - **Decision:** All automations generated by the Rulebook system will be stored in a dedicated YAML file (e.g., `config/rulebook_automations.yaml`), which the user includes in their main Home Assistant configuration (Section 2.2).
    - **Rationale:** Enhances safety and manageability. Isolates Rulebook-generated automations from the user's manually created ones, making it easier to review, modify, or remove them as a distinct set. Simplifies updates and reduces the risk of unintended changes to other automation files.

3.  **Google Agent Development Kit (ADK) for Agent Logic:**

    - **Decision:** Employ the Google ADK (`google.adk.agents`) for building the core LLM Agent(s) (Section 2.3).
    - **Rationale:** The ADK provides a structured framework for developing conversational agents, including managing dialogue flow, tool usage, session state (initially `InMemorySessionService`), and interaction with LLMs. This accelerates development and promotes a modular design (Coordinator Agent and specialized sub-agents).

4.  **Dual Confirmation Mechanism (Repairs System & Interactive Chat):**

    - **Decision:** Implement two primary methods for obtaining user confirmation before applying changes to Home Assistant: Home Assistant's built-in "Repairs" system for asynchronous review, and direct confirmation within an interactive chat session (Section 2.2).
    - **Rationale:** Offers flexibility to the user. Repairs are suitable for non-urgent, system-initiated suggestions. Interactive chat allows for immediate feedback and iterative refinement during active engagement with the Rulebook agent.

5.  **Adoption of Guiding Principles:**

    - **Decision:** The design of the LLM Agent(s) and the Conversation Interface will strictly adhere to A2A-inspired principles (Section 2.3).
    - **Rationale:** Prioritizes user trust, control, and transparency. Ensures that the system clearly communicates its intentions, seeks explicit user consent before acting, handles errors gracefully, and aims for safe and reversible operations.

6.  **Abstracted LLM Interaction via HA LLM Task and Shim:**
    - **Decision:** Instead of direct integration with a specific LLM provider (e.g., `google.genai`), the system will interact with LLMs through Home Assistant's upcoming "LLM Task" feature. A custom "LLM Shim" will be developed to translate requests from the ADK-based agents to the HA LLM Task interface.
    - **Rationale:** This decouples the Rulebook integration from any single LLM provider, granting users the flexibility to choose and configure their preferred LLM via Home Assistant's infrastructure. It also future-proofs the integration against changes in specific LLM APIs. The shim ensures that the ADK-based agent logic remains consistent while accommodating various LLMs.

### Open Questions & Topics for Future Exploration

While the core design is established, the following areas warrant further investigation and refinement as the project progresses:

1.  **LLM Shim Design and LLM Capabilities:**

    - How will the LLM Shim best abstract the capabilities of diverse LLMs available through the HA LLM Task? What strategies will it employ to handle variations in prompt requirements, response formats, and available functionalities (e.g., tool use, vision capabilities) across different models? How can users be guided in selecting/configuring an LLM via HA that is suitable for Rulebook's needs?

2.  **Advanced Error Handling & Ambiguity Resolution Strategies:**

    - What are the detailed recovery and clarification strategies when the LLM fails to parse a complex or ambiguous rule? How can the system most effectively guide users to rephrase or correct their rulebook text to achieve the desired outcome, minimizing user frustration?

3.  **Scalability and Performance Optimization:**

    - As a user's rulebook grows in size and complexity, what are the performance implications, particularly concerning the number and latency of LLM calls required for parsing and analysis? Are there caching strategies or batching techniques that could optimize this?

4.  **State Management for Long-Term Context and User Preferences:**

    - Beyond the ADK's in-memory session service for immediate conversational context, how will the system persist and recall long-term user preferences, interaction history, or partially completed tasks across different sessions or Home Assistant restarts? This could involve storing such data in the Home Assistant config entry or a dedicated storage mechanism.

5.  **Security and Privacy of Rulebook Data:**
    - The rulebook contains potentially sensitive information about a user's home environment, routines, and devices. What specific measures, beyond standard Home Assistant practices, are needed to ensure this data is handled securely, especially when parts of it are processed by external LLM services? This includes data in transit and at rest, as well as ensuring clarity on data usage by the LLM provider.

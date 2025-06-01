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
    *   **Basic Information:** Location, preferred units (temperature, distance), list of people.
    *   **Areas and Structure:** Hierarchical representation of floors, rooms, and their connections.
    *   **Utility Providers:** Information about energy, water, and gas providers.
    *   **Smart Home Rules:** A list of desired automations or states, with key elements extracted (e.g., triggers, conditions, actions, entities involved, desired states).

**Processing Steps:**

1.  **Initial LLM Call(s) for Global Structure and Simpler Sections:**
    *   The user-provided text is first processed to identify and extract broader sections like "Basic Information" (location, people, preferences), "Areas and Structure" (floors, rooms), and "Utility Providers."
    *   This might involve one LLM call with a prompt asking it to identify these sections and return their content in a structured format (e.g., JSON). The prompt should also instruct the LLM to return the raw text block(s) corresponding to "Smart Home Rules."
    *   Alternatively, if these sections are typically demarcated by common headings, preliminary text processing could isolate these blocks, which are then sent to the LLM with more targeted prompts for each block.

2.  **Dedicated LLM Call for Each Smart Home Rule:**
    *   The system will iterate through each identified "Smart Home Rule" (obtained as a text snippet from the step above).
    *   For each individual rule, a separate, focused LLM call (via `google.genai` client) will be made.
    *   The prompt for this call will instruct the LLM to parse that single rule and extract its core components:
        *   **Intent:** The primary goal of the rule.
        *   **Entities:** Devices, locations, people involved.
        *   **Triggers:** What causes the rule to activate.
        *   **Conditions:** Circumstances that must be true for the rule to run.
        *   **Actions:** What the rule should do.
        *   **Desired States/Attributes:** Specific states or attributes for entities (e.g., "light should not be too bright").
    *   The LLM will be prompted to return this information for the single rule in a consistent, structured format (e.g., JSON).

3.  **Aggregation and Normalization:**
    *   The structured outputs from all LLM calls (for global sections and individual rules) are aggregated.
    *   The aggregated data might undergo a light normalization step (e.g., standardizing date/time formats if not consistently handled by the LLM).
    *   Basic validation could check for the presence of key expected fields.
    *   If significant ambiguities or missing critical information are detected, the system might need to engage the user for clarification via the Conversation Interface.

**Rationale for this Approach:**
*   **Manages Complexity:** Avoids an overly complex single prompt. Parsing individual rules is a distinct, complex sub-task.
*   **Reliability & Error Isolation:** Prompts for individual rules can be more targeted. If parsing one rule fails, it doesn\'t necessarily invalidate the parsing of other rules or the basic info.
*   **Scalability:** Handles a variable number of rules cleanly.
*   **Focused Prompts:** Allows for more precise prompt engineering for different types of information.

**Potential Challenges:**
    *   **Prompt Engineering:** Crafting prompts that reliably extract all necessary information accurately and in the desired structure from varied free-form text.
    *   **Ambiguity in Natural Language:** LLMs can still struggle with highly ambiguous phrasing.
    *   **Mapping to Home Assistant:** Ensuring the LLM's interpretation of devices, areas, and entities can be later mapped to actual Home Assistant constructs.
    *   **Consistency:** Ensuring the LLM provides output in a consistent structure across different rule books and phrasings.
    *   **Handling Incomplete or Malformed Input:** The LLM needs to be robust enough or the surrounding logic needs to handle cases where the rule book is poorly written or incomplete.

**Tools/Technologies:**
    *   Python for overall orchestration.
    *   Google Generative AI (`google.genai`) as the primary engine for parsing and structuring the rule book text.

This parsed and structured representation of the rule book will then be passed to the LLM Agent(s) and the Home Assistant Interaction Layer to compare with the current state of the smart home and identify discrepancies or actions to be taken.

### 2.2. Home Assistant Interaction Layer
(To be detailed: Mechanisms for reading current HA state - entities, areas, automations, configuration - and for enacting changes - creating/updating automations, modifying configurations, etc.)

### 2.3. LLM Agent(s)
(To be detailed: The role of `google.adk` and `google.genai` based agents. How they orchestrate the process, manage conversation state, and make decisions based on the rulebook and HA state.)

### 2.4. Conversation Interface
(To be detailed: How the user interacts with the system via Home Assistant's conversation and assist pipeline.)

## 3. Data Flow
(To be detailed: Diagrams and descriptions of how data flows between components for key use cases outlined in REQUIREMENTS.md, e.g., location configuration, automation management.)

## 4. Key Design Decisions
(To be detailed: Significant architectural or technological choices, e.g., specific LLM models, error handling strategies, state management for long-running interactions.)

<!-- filepath: /workspaces/home-assistant-rulebook/docs/DESIGN.md -->
# Rulebook Design

This describes the components in the rulebook.

## 1. Overview

The Rulebook project aims to simplify smart home management within Home Assistant. Users will create a natural language "rule book" document outlining their desired home configuration, devices, and automations. A Large Language Model (LLM) will parse this rule book and the current Home Assistant instance's state. It will then provide actionable suggestions and assistance to the user to align their smart home with the rule book, automating setup and configuration where possible.

## 2. Core Components

This section will detail the primary architectural components of the Rulebook system.

### 2.1. Rulebook Parser
(To be detailed: How the natural language rule book is processed, entities and intents extracted, etc.)

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

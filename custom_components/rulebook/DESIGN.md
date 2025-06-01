# Rule book

This document was originally authored by Paulus Schoutsen.

## Goals

The idea of the rule book is as follows:

_Let people create a requirements document for their smart home and let an LLM automatically organize their smart home based on this._

See `RULEBOOK_EXAMPLE.md` for an example rule book.

The LLM will parse the rule book and the instance. Compare the data and suggest actions to the user.

## Requirements

Things that an LLM should be able to do based on the rule book:

### Configure instance location

The LLM should be able to read the location from the instance, compare it to the currently configured one and offer user to update their location.

### Configure people in the smart home

The LLM should be able to ensure that all people have accounts and are represented in the smart home.

### Offer to set up integrations for electricity, water, waste and sewage

Monitor if integrations exist for the smart home installation for their utilities and city services.

### Configure areas and device locations

Ensure all areas are present in both the instance and the rule book. Prompt for updates if necessary.

### Manage automations

Compare currently configured automations with the rule book.

- Offer to document automations in the rule book that are present in the instance
- Offer to create automations in the instance that are present in the rule book
- Offer to update automations in the instance if the rule has changed
- Advice on what devices can be acquired to achieve certain specific automations
- Suggest new automations and devices based on how the home is being used

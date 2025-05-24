# home-assistant-rulebook

A Home Assistant custom component implementing an LLM powered home rulebook.
This is an experimental project under development.

## Environment Pre-requisites

```bash
$ uv venv
$ source .venv/bin/activate
$ uv pip install -r requirements_dev.txt
```

## Running tests

```bash
$ pytest
```

## Evaluation

This is an _eval first_ project. That means that you must first write an eval
for what you're trying to accomplish, then build code to meet the goal. Evals
should be easy and run frequently. This project uses `home-assistant-datasets`
library for plugins for making it easier to run common eval tasks.

You can run the eval with this command:

```bash
# Install custom components in `/workspaces/custom_components`
$ export PYTHONPATH="/workspaces/"
$ pytest eval
```

We use a pytest based eval to leverage the great unit test infrastructure
in Home Assistant and because it has similar semantics for a pass or fail
around any particular test.

Given this is experimental, it is common for many tests to fail. Right now to
simplify we're using a single Gemini model. Most of the work to hillclimb on
is about data flow and agentic behaviors and less about the specific model.

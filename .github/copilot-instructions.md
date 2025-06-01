# Instructions for GitHub Copilot

This repository holds the core of Home Assistant Rulebook, a home Assistant
custom component implementation.

- Python code must be compatible with Python 3.13
- Use the newest Python language features if possible:
  - Pattern matching
  - Type hints
  - f-strings for string formatting over `%` or `.format()`
  - Dataclasses
  - Walrus operator
- Code quality tools:
  - Formatting: Ruff
  - Linting: Ruff
  - Type checking: MyPy
  - Testing: pytest with plain functions and fixtures
- Inline code documentation:
  - File headers should be short and concise:
    ```python
    """Integration for Peblar EV chargers."""
    ```
  - Every method and function needs a docstring:
    ```python
    async def build_kustomization(path: pathlib.Path) -> None:
        """Build the fluxtomization from the specified path."""
        ...
    ```
- All code and comments and other text are written in American English
- Follow existing code style patterns as much as possible
- See `docs/REQUIREMENTS.md` for the product requirements
- See `docs/DESIGN.md` for the detailed design
- See `docs/RULEBOOK_EXAMPLE.md` for the example rulebook
- Core locations:
  - Main code directory: `custom_components/rulebook/`
  - Tests directory: `tests/`
- All external I/O operations must be async
- Async patterns:
  - Avoid sleeping in loops
  - Avoid awaiting in loops, gather instead
  - No blocking calls
- Error handling:
  - Use specific exceptions from `custom_components.rulebook.exceptions` or create if they don't exist
  - `HomeAssistantError` should be used for user-facing errors
- Logging:
  - Message format: No periods at end
  - Be very restrictive on the use of logging info messages, use debug for
    anything which is not targeting the user.
  - Use lazy logging (no f-strings):
    ```python
    _LOGGER.debug("This is a log message with %s", variable)
    ```
- Testing:
  - Prefer fake objects over mocks
  - Use snapshots for complex data
  - Follow existing test patterns

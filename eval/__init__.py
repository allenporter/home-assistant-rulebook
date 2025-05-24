"""Evaluation module."""

import sys
import pathlib


def adjust_custom_component_python_path() -> None:
    """Ensure that the system environment is configured properly.

    We require custom components to be present in `PYTHONPATH`. We require
    multiple so its not sufficient to just include the project component with
    since it only contains rulebook.
    """
    eval_root = pathlib.Path(__file__).parent
    project_root = eval_root.parent
    try:
        sys.path.remove(str(project_root))
    except ValueError:
        pass
    try:
        sys.path.remove(".")
    except ValueError:
        pass

    try:
        import custom_components  # noqa: F401
    except ImportError:
        raise ImportError(
            "Could not import `custom_components`, check PYTHONPATH is explicitly set"
        )


adjust_custom_component_python_path()

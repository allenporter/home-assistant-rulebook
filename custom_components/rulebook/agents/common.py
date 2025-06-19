"""Agent for parsing individual smart home rules."""

import asyncio
import logging
from typing import override
from collections.abc import AsyncGenerator

from google.adk.agents import ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event


_LOGGER = logging.getLogger(__name__)


class ParallelMaxInFlightAgent(ParallelAgent):
    """An agent wrapper that limits the number of concurrent sub-agents."""

    max_in_flight: int
    """Maximum number of sub-agents that can run in parallel."""

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Initialize the MaxInFlightAgent."""
        super().__init__(*args, **kwargs)
        self._semaphore = asyncio.Semaphore(self.max_in_flight)

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        async with self._semaphore:
            async for event in super()._run_async_impl(ctx):
                yield event

    @override
    async def _run_live_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        raise NotImplementedError("This is not supported yet for MaxInFlightAgent.")
        yield  # type: ignore[unreachable]

"""
Base agent class for the CoNDA simulator.

All agents inherit from ``BaseAgent`` and implement ``observe(state)``.
The constructor signature ``(agent_id, params, rng)`` matches what the
engine's ``_create_agents`` expects.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

__all__ = ["BaseAgent"]


class BaseAgent:
    """
    Base class for all simulation agents.

    Attributes
    ----------
    agent_id : str
        Unique identifier for this agent instance.
    agent_class : str
        Class-level label used by the engine's agent registry.

    Constructor Parameters
    ----------------------
    agent_id : str
        Unique identifier.
    params : dict
        Agent-specific configuration from the scenario file.
    rng : numpy.random.Generator
        Shared seeded RNG for deterministic behaviour.
    """

    agent_class: str = "base"

    def __init__(
        self,
        agent_id: str,
        params: Dict[str, Any],
        rng: np.random.Generator,
    ) -> None:
        self.agent_id = agent_id
        self.params = dict(params)
        self._rng = rng

        # Capital / inventory bookkeeping (agent-internal estimates)
        initial_capital = float(params.get("initial_capital", 50_000.0))
        self._initial_capital = initial_capital
        self._inventory_x = float(params.get("initial_inventory_x", 0.0))
        self._inventory_y = float(params.get("initial_inventory_y", initial_capital))

    # ---- public interface ----------------------------------------------------

    def observe(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Observe the public market state and return an action.

        Parameters
        ----------
        state : dict
            Public market state with keys: t, mid_price, reserve_x,
            reserve_y, fee_bps, oracle_price, shock.

        Returns
        -------
        dict or None
            Action dict with keys (event, side, price, quantity, capital,
            pnl), or ``None`` for a no-op.
        """
        raise NotImplementedError("Subclasses must implement observe()")

    # ---- helpers for subclasses ----------------------------------------------

    def _mark_to_market(self, oracle_price: float) -> float:
        """Estimate current portfolio value using oracle price."""
        return self._inventory_x * oracle_price + self._inventory_y

    def _pnl(self, oracle_price: float) -> float:
        """Estimated profit/loss versus initial capital."""
        return self._mark_to_market(oracle_price) - self._initial_capital

    def _make_action(
        self,
        event: str,
        side: str,
        price: float,
        quantity: float,
        oracle_price: float,
    ) -> Dict[str, Any]:
        """Build a schema-compatible action dictionary."""
        return {
            "event": event,
            "side": side,
            "price": price,
            "quantity": quantity,
            "capital": self._mark_to_market(oracle_price),
            "pnl": self._pnl(oracle_price),
        }

    def _estimate_bid(self, qty_y: float, mid_price: float) -> None:
        """
        Update internal inventory for a bid (send Y, receive X).

        This is an *estimate* — the agent does not know the exact AMM
        output at action time.
        """
        if mid_price > 0 and qty_y > 0:
            estimated_x = qty_y / mid_price
            self._inventory_x += estimated_x
            self._inventory_y = max(0.0, self._inventory_y - qty_y)

    def _estimate_ask(self, qty_x: float, mid_price: float) -> None:
        """
        Update internal inventory for an ask (send X, receive Y).
        """
        if qty_x > 0:
            estimated_y = qty_x * mid_price
            self._inventory_x = max(0.0, self._inventory_x - qty_x)
            self._inventory_y += estimated_y

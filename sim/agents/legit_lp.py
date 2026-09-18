"""
Legitimate liquidity-provider (LP) agent.

Represents genuinely benign coordinated behaviour: multiple LPs that
independently maintain balanced inventory and rebalance in response to
the same public oracle signal.

Why behaviour is correlated but NOT collusive
---------------------------------------------
All LPs react to the *same* public oracle price and use similar rebalancing
thresholds, so their actions are naturally correlated.  However:

* No price markup — target equals the oracle, not above it.
* No deliberate spread widening — quotes are tight.
* No suppression of competition.
* No punishment of independent agents.
* No secret communication.

This agent serves as the false-positive control scenario.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np

from sim.agents.base import BaseAgent

logger = logging.getLogger(__name__)

__all__ = ["LegitLPAgent"]


class LegitLPAgent(BaseAgent):
    """
    Legitimate liquidity provider — benign inventory rebalancing.

    Maintains a target allocation between X (base) and Y (quote) and
    trades when the portfolio drifts too far from that target.

    Configurable parameters (via ``params`` dict)
    ----------------------------------------------
    target_x_fraction : float
        Target fraction of portfolio value held in X (mark-to-market).
        Default 0.5 (balanced).
    rebalance_threshold : float
        Rebalance when actual X fraction deviates from target by more
        than this.  Default 0.05 (5 %).
    max_trade_y : float
        Maximum Y to spend per bid.  Default 200.0.
    max_trade_x : float
        Maximum X to sell per ask.  Default 2.0.
    """

    agent_class = "legitimate_coordination"

    def __init__(
        self,
        agent_id: str,
        params: Dict[str, Any],
        rng: np.random.Generator,
    ) -> None:
        super().__init__(agent_id, params, rng)
        self._target_x_frac = float(params.get("target_x_fraction", 0.5))
        self._rebalance_threshold = float(params.get("rebalance_threshold", 0.05))
        self._max_trade_y = float(params.get("max_trade_y", 200.0))
        self._max_trade_x = float(params.get("max_trade_x", 2.0))

    def observe(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        mid = state["mid_price"]
        oracle = state["oracle_price"]

        if oracle <= 0 or mid <= 0:
            return None

        # ---- Portfolio assessment -------------------------------------------
        x_value = self._inventory_x * oracle
        total_value = x_value + self._inventory_y

        if total_value <= 0:
            return self._make_action("quote", "bid", oracle, 0.0, oracle)

        current_x_frac = x_value / total_value
        deviation = current_x_frac - self._target_x_frac

        # ---- Within tolerance → quote only -----------------------------------
        if abs(deviation) < self._rebalance_threshold:
            return self._make_action("quote", "bid", oracle, 0.0, oracle)

        # ---- Over-weight in X → sell X for Y ---------------------------------
        if deviation > 0:
            # Amount of X value to shed (in Y terms)
            excess_value = deviation * total_value
            qty_x = excess_value / oracle
            qty_x = min(qty_x, self._max_trade_x, self._inventory_x * 0.5)
            if qty_x < 0.01:
                return self._make_action("quote", "ask", oracle, 0.0, oracle)
            self._estimate_ask(qty_x, mid)
            return self._make_action("trade", "ask", mid, qty_x, oracle)

        # ---- Under-weight in X → buy X with Y --------------------------------
        deficit_value = abs(deviation) * total_value
        qty_y = min(deficit_value, self._max_trade_y, self._inventory_y * 0.5)
        if qty_y < 1.0:
            return self._make_action("quote", "bid", oracle, 0.0, oracle)
        self._estimate_bid(qty_y, mid)
        return self._make_action("trade", "bid", mid, qty_y, oracle)

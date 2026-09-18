"""
Competitive trading agent.

Acts independently — no communication or coordination with other agents.
Quotes and trades near the oracle price, arbitraging deviations between
the AMM mid-price and the oracle.

Behaviour
---------
* mid > oracle (by > threshold)  →  sell X  (pushes mid down toward oracle)
* mid < oracle (by > threshold)  →  buy X   (pushes mid up toward oracle)
* within threshold               →  quote only

This creates mean-reversion around the oracle price.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np

from sim.agents.base import BaseAgent

logger = logging.getLogger(__name__)

__all__ = ["CompetitiveAgent"]


class CompetitiveAgent(BaseAgent):
    """
    Independent competitive market participant.

    Configurable parameters (via ``params`` dict)
    ----------------------------------------------
    trade_threshold : float
        Fractional deviation from oracle required to trigger a trade.
        Default 0.002 (0.2 %).
    base_qty_y : float
        Base quote-asset quantity for bids (Y units sent to AMM).
        Default 150.0.
    base_qty_x : float
        Base base-asset quantity for asks (X units sent to AMM).
        Default 1.5.
    max_scale : float
        Maximum multiplier applied when deviation is large.
        Default 3.0.
    """

    agent_class = "competitive"

    def __init__(
        self,
        agent_id: str,
        params: Dict[str, Any],
        rng: np.random.Generator,
    ) -> None:
        super().__init__(agent_id, params, rng)
        self._threshold = float(params.get("trade_threshold", 0.002))
        self._base_qty_y = float(params.get("base_qty_y", 150.0))
        self._base_qty_x = float(params.get("base_qty_x", 1.5))
        self._max_scale = float(params.get("max_scale", 3.0))

    def observe(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        mid = state["mid_price"]
        oracle = state["oracle_price"]

        if oracle <= 0 or mid <= 0:
            return None

        # Fractional deviation: positive ⇒ mid above oracle
        dev = (mid - oracle) / oracle

        # ---- Within band → quote only ----------------------------------------
        if abs(dev) <= self._threshold:
            return self._make_action("quote", "bid", oracle, 0.0, oracle)

        # Scale trade size by how far we are from oracle (capped)
        scale = min(abs(dev) / self._threshold, self._max_scale)

        # ---- Mid above oracle → sell X (push mid down) -----------------------
        if dev > self._threshold:
            qty = self._base_qty_x * scale
            # Do not sell more X than we hold (bounded)
            qty = min(qty, self._inventory_x * 0.5)
            if qty < 0.01:
                return self._make_action("quote", "ask", oracle, 0.0, oracle)
            self._estimate_ask(qty, mid)
            return self._make_action("trade", "ask", mid, qty, oracle)

        # ---- Mid below oracle → buy X (push mid up) -------------------------
        qty = self._base_qty_y * scale
        # Do not spend more Y than we hold (bounded)
        qty = min(qty, self._inventory_y * 0.5)
        if qty < 1.0:
            return self._make_action("quote", "bid", oracle, 0.0, oracle)
        self._estimate_bid(qty, mid)
        return self._make_action("trade", "bid", mid, qty, oracle)

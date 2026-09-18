"""
Explicit cartel agent.

Represents deliberate coordination between agents that share the same
policy parameters and act in lockstep to maintain the AMM mid-price
*above* the oracle price.

Mechanism
---------
All cartel agents target:

    target_price = oracle_price × (1 + markup)

* mid < target  →  buy X aggressively  (pushes mid up toward target)
* mid ≫ target  →  sell X minimally     (takes small profit)
* otherwise     →  quote at target      (wider spread than competitive)

After a scheduled oracle shock, all cartel agents re-evaluate on the
*same tick* and respond identically (lockstep re-quote).

The asymmetry — aggressive buying, reluctant selling — creates persistent
upward pressure on the AMM mid-price compared to competitive agents.

No detector/scoring logic is implemented here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np

from sim.agents.base import BaseAgent

logger = logging.getLogger(__name__)

__all__ = ["CartelAgent"]


class CartelAgent(BaseAgent):
    """
    Explicit cartel — coordinated price elevation.

    Configurable parameters (via ``params`` dict)
    ----------------------------------------------
    markup : float
        Fractional markup above oracle for the target price.
        Default 0.03 (3 %).
    buy_threshold : float
        Buy X when mid is more than this fraction below target.
        Default 0.005 (0.5 %).
    sell_threshold : float
        Sell X only when mid exceeds target by this fraction.
        Default 0.06 (6 %).
    base_qty_y : float
        Base Y quantity for bids (aggressive).  Default 400.0.
    base_qty_x : float
        Base X quantity for asks (reluctant).  Default 0.5.
    max_scale : float
        Maximum trade-size multiplier.  Default 3.0.
    shock_boost : float
        Extra multiplier for post-shock buy quantities.  Default 2.0.
    """

    agent_class = "explicit_cartel"

    def __init__(
        self,
        agent_id: str,
        params: Dict[str, Any],
        rng: np.random.Generator,
    ) -> None:
        super().__init__(agent_id, params, rng)
        self._markup = float(params.get("markup", 0.03))
        self._buy_threshold = float(params.get("buy_threshold", 0.005))
        self._sell_threshold = float(params.get("sell_threshold", 0.06))
        self._base_qty_y = float(params.get("base_qty_y", 400.0))
        self._base_qty_x = float(params.get("base_qty_x", 0.5))
        self._max_scale = float(params.get("max_scale", 3.0))
        self._shock_boost = float(params.get("shock_boost", 2.0))

    def observe(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        mid = state["mid_price"]
        oracle = state["oracle_price"]
        shock = state["shock"]

        if oracle <= 0 or mid <= 0:
            return None

        target = oracle * (1.0 + self._markup)

        # Fractional deviation of mid from target
        dev = (mid - target) / target

        # ---- Post-shock lockstep response ------------------------------------
        # After an oracle shock, all cartel agents buy aggressively on this
        # tick to restore the target price.  Because every cartel agent runs
        # the same deterministic logic against the same state, they all
        # respond identically → lockstep.
        if shock is not None and dev < 0:
            qty = self._base_qty_y * self._shock_boost
            qty = min(qty, self._inventory_y * 0.3)
            if qty >= 1.0:
                self._estimate_bid(qty, mid)
                return self._make_action("trade", "bid", target, qty, oracle)

        # ---- Mid below target → buy X (push mid up) -------------------------
        if dev < -self._buy_threshold:
            scale = min(abs(dev) / self._buy_threshold, self._max_scale)
            qty = self._base_qty_y * scale
            qty = min(qty, self._inventory_y * 0.3)
            if qty < 1.0:
                return self._make_action("quote", "bid", target, 0.0, oracle)
            self._estimate_bid(qty, mid)
            return self._make_action("trade", "bid", target, qty, oracle)

        # ---- Mid far above target → reluctant sell ---------------------------
        if dev > self._sell_threshold:
            qty = self._base_qty_x
            qty = min(qty, self._inventory_x * 0.1)
            if qty < 0.01:
                return self._make_action("quote", "ask", target, 0.0, oracle)
            self._estimate_ask(qty, mid)
            return self._make_action("trade", "ask", target, qty, oracle)

        # ---- Within band → hold, quote at target (wider spread) --------------
        return self._make_action("quote", "bid", target, 0.0, oracle)

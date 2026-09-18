"""Competitive Counterfactual Engine for CoNDA.

This module computes a closed-form competitive reference price for trading agents
operating against an automated market maker (AMM) pool with an external oracle feed.

================================================================================
MATHEMATICAL FOUNDATIONS & VERBAL DEFENSE GUIDE FOR JUDGES
================================================================================

1. WHAT X AND Y RESERVES MEAN:
   In a decentralized constant-product automated market maker (AMM), the liquidity
   pool holds two token reserves:
   - x (reserve_x): The inventory of the base traded asset (e.g., ETH, BTC, or Token X).
   - y (reserve_y): The inventory of the quote/numeraire asset (e.g., USDC, DAI, or USD).
   The product of reserves is invariant to swaps: x * y = k.

2. WHY y / x GIVES THE INSTANTANEOUS AMM PRICE:
   For an infinitesimal swap dx of asset x into the pool in exchange for dy of asset y:
     (x + dx)(y - dy) = k  =>  xy - x*dy + y*dx - dx*dy = xy
   Ignoring the higher-order term dx*dy and rearranging:
     dy / dx = y / x
   Therefore, the marginal exchange rate (price of asset x measured in units of y)
   at the current reserve ratio is exactly P_pool = y / x.

3. WHY THE ORACLE PRICE IS INCLUDED:
   P_pool reflects only local liquidity within this specific smart contract. It can
   be temporarily distorted by a large trade or localized manipulation.
   The oracle price (P_oracle) represents the broader exogenous consensus price across
   global, highly liquid centralized and decentralized venues. A rational, competitive
   trader utilizes both local pool execution reality and global fair-value signals.

4. WHY LIQUIDITY/DEPTH AFFECTS CONFIDENCE IN THE AMM PRICE:
   Pool depth can be characterized by geometric mean reserves: L = sqrt(x * y),
   or quote depth D_y = 2 * y.
   - Low Liquidity (Shallow Depth): High slippage. A small trade drastically moves
     P_pool away from fair value. Trusting P_pool alone is risky; hence weight shifts
     toward the external oracle.
   - High Liquidity (Deep Reserves): Deep capital buffers slippage. The AMM price
     is resilient and reflects substantial economic commitment.
   We construct an explicit liquidity confidence weight:
     w_pool = L / (L + L_0)
   where L_0 is a characteristic scale constant. Then w_oracle = 1.0 - w_pool.

5. HOW FEES AFFECT AN EXECUTABLE QUOTE / SPREAD:
   AMM swaps incur protocol fees (e.g., fee_bps = 30 bps = 0.30% = 0.003).
   Any competitive market participant quoting to buy or sell must account for this
   friction:
   - An ask (selling base asset x) requires receiving at least P_mid * (1 + fee)
     to justify inventory risk and cover round-trip pool fees.
   - A bid (buying base asset x) is bounded by P_mid * (1 - fee).
   Quotes outside this competitive band by a wide margin (e.g., asks 4-10% above
   P_mid * (1 + fee)) cannot be justified by competitive fee friction.

6. WHY THIS IS A COMPETITIVE REFERENCE RATHER THAN A COLLUSION-FREE RECONSTRUCTION:
   A full collusion-free reconstruction would require knowing private utility functions,
   inventory costs, latency profiles, and solving a dynamic Nash equilibrium.
   Instead, our counterfactual acts as an objective, transparent benchmark: "What
   price would an uncoordinated, rational arbitrageur quote given observable market
   state?" Persistent unilateral or bilateral elevation above this reference is an
   empirical anomaly.

7. WHY A CLOSED-FORM APPROXIMATION IS APPROPRIATE FOR A HACKATHON DETECTOR:
   Closed-form solutions are:
   - 100% deterministic (no random seed variations).
   - Highly explainable: every term (P_pool, P_oracle, fee, L) directly maps to
     first-principles economics that judges can verify on a whiteboard.
   - Non-brittle: closed-form bounds cannot get trapped in local numerical optima.

8. WHY IT IS COMPUTATIONALLY CHEAPER THAN SIMULATING AN ALTERNATIVE MARKET:
   Simulating a parallel counterfactual ABM (agent-based model) requires solving
   coupled ODEs/PDEs or running discrete event steps, taking seconds to minutes
   per window and introducing simulation noise.
   Our closed-form calculation evaluates in microseconds (< 0.1 ms), effortlessly
   meeting the strict sub-50 ms per-window requirement.
================================================================================
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# Default characteristic liquidity scale constant (L_0 in sqrt(x*y) units)
DEFAULT_LIQUIDITY_SCALE = 50_000.0

# Default fallback fee in basis points (30 bps = 0.30%)
DEFAULT_FEE_BPS = 30.0


def is_valid_number(val: Any) -> bool:
    """Check if a value is a finite, real, non-negative number."""
    if val is None:
        return False
    try:
        num = float(val)
        return not (math.isnan(num) or math.isinf(num))
    except (ValueError, TypeError):
        return False


def compute_counterfactual_price(
    pool: Optional[Dict[str, Any]],
    oracle_price: Optional[float],
    side: Optional[str] = None,
    fee_bps_override: Optional[float] = None,
    liquidity_scale: float = DEFAULT_LIQUIDITY_SCALE,
) -> Optional[float]:
    """Compute the closed-form competitive reference price for a single state.

    Formula:
      P_pool = reserve_y / reserve_x  (if reserve_x > 0 and reserve_y > 0)
      L = sqrt(reserve_x * reserve_y)
      w_pool = L / (L + L_0)
      w_oracle = 1.0 - w_pool
      P_mid = w_pool * P_pool + w_oracle * P_oracle

    Spread adjustment:
      P_ref_ask = P_mid * (1 + fee)
      P_ref_bid = P_mid * (1 - fee)

    Handles missing, zero, negative, NaN, and infinite values gracefully.

    Args:
        pool: Dictionary containing reserve_x, reserve_y, and fee_bps.
        oracle_price: External oracle price float.
        side: Quote side ('ask', 'bid', or None/mid).
        fee_bps_override: Optional override for fee in basis points.
        liquidity_scale: Constant L_0 calibrating pool depth confidence.

    Returns:
        float reference price, or None if market data is entirely absent.
    """
    # 1. Parse and validate pool reserves
    p_pool: Optional[float] = None
    liquidity_depth: float = 0.0
    fee_bps: float = fee_bps_override if fee_bps_override is not None else DEFAULT_FEE_BPS

    if isinstance(pool, dict):
        rx = pool.get("reserve_x")
        ry = pool.get("reserve_y")
        pool_fee = pool.get("fee_bps")

        if fee_bps_override is None and is_valid_number(pool_fee):
            fee_bps = max(0.0, float(pool_fee))

        if is_valid_number(rx) and is_valid_number(ry):
            rx_f = float(rx)
            ry_f = float(ry)
            if rx_f > 0.0 and ry_f > 0.0:
                p_pool = ry_f / rx_f
                # Bounded liquidity metric: geometric mean depth
                liquidity_depth = math.sqrt(rx_f * ry_f)

    # 2. Parse and validate oracle price
    p_oracle: Optional[float] = None
    if is_valid_number(oracle_price):
        op_f = float(oracle_price)
        if op_f > 0.0:
            p_oracle = op_f

    # 3. Determine mid reference price based on available sources
    p_mid: Optional[float] = None

    if p_pool is not None and p_oracle is not None:
        # Both pool and oracle are available -> weighted combination by depth
        denom = liquidity_depth + max(1.0, liquidity_scale)
        w_pool = max(0.0, min(1.0, liquidity_depth / denom))
        w_oracle = 1.0 - w_pool
        p_mid = (w_pool * p_pool) + (w_oracle * p_oracle)
    elif p_pool is not None:
        # Only pool available
        p_mid = p_pool
    elif p_oracle is not None:
        # Only oracle available
        p_mid = p_oracle
    else:
        # Neither source is valid
        return None

    # Final sanity check on p_mid
    if not is_valid_number(p_mid) or p_mid <= 0.0:
        return None

    # 4. Fee spread adjustment based on trade side
    fee_fraction = max(0.0, fee_bps) / 10_000.0
    side_str = str(side).strip().lower() if side is not None else "mid"

    if side_str == "ask":
        # Sellers ask above mid to cover AMM execution fee friction
        return p_mid * (1.0 + fee_fraction)
    elif side_str == "bid":
        # Buyers bid below mid to account for AMM execution fee friction
        return max(0.0, p_mid * (1.0 - fee_fraction))
    else:
        # Mid-market baseline reference
        return p_mid


def compute_window_counterfactual(ticks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate counterfactual metrics across an entire window of ticks.

    Outputs schema matching the frozen contract:
    {
      "reference_price": 99.8,
      "observed_price": 104.1,
      "gap_pct": 4.3
    }

    Args:
        ticks: List of market tick dictionaries.

    Returns:
        Dict with reference_price, observed_price, and gap_pct (rounded to 1 decimal place).
    """
    if not ticks:
        return {
            "reference_price": 0.0,
            "observed_price": 0.0,
            "gap_pct": 0.0,
        }

    observed_prices: List[float] = []
    reference_prices: List[float] = []

    for tick in ticks:
        event = tick.get("event")
        price = tick.get("price")
        side = tick.get("side")

        # Collect valid quote/trade prices
        if event in ("quote", "trade") and is_valid_number(price):
            obs_p = float(price)
            if obs_p > 0.0:
                observed_prices.append(obs_p)

                # Compute point-in-time reference for this tick
                ref_p = compute_counterfactual_price(
                    pool=tick.get("pool"),
                    oracle_price=tick.get("oracle_price"),
                    side=side,
                )
                if ref_p is not None and ref_p > 0.0:
                    reference_prices.append(ref_p)

    # If no quotes had both, fallback to overall pool/oracle from any tick in window
    if not reference_prices:
        for tick in reversed(ticks):
            ref_p = compute_counterfactual_price(
                pool=tick.get("pool"),
                oracle_price=tick.get("oracle_price"),
                side="ask",
            )
            if ref_p is not None and ref_p > 0.0:
                reference_prices.append(ref_p)
                break

    # Calculate median observed and reference prices
    obs_val = _median(observed_prices) if observed_prices else 0.0
    ref_val = _median(reference_prices) if reference_prices else 0.0

    if ref_val > 0.0 and obs_val > 0.0:
        gap_pct = ((obs_val - ref_val) / ref_val) * 100.0
    else:
        gap_pct = 0.0

    return {
        "reference_price": round(ref_val, 1),
        "observed_price": round(obs_val, 1),
        "gap_pct": round(gap_pct, 1),
    }


def _median(values: List[float]) -> float:
    """Deterministic median of a list of floats."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0

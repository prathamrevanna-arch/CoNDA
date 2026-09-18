"""
Constant-product AMM (x * y = k).

Convention
----------
reserve_x : float   – base asset reserve
reserve_y : float   – quote asset reserve
mid_price  = reserve_y / reserve_x
k          = reserve_x * reserve_y
fee_bps    : int     – fee in basis points  (30 bps → 0.30 %)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class AMMError(Exception):
    """Base exception for AMM-related errors."""


class InvalidReservesError(AMMError):
    """Raised when reserves are non-positive."""


class ZeroLiquidityError(AMMError):
    """Raised on operations against a pool with zero liquidity."""


class InvalidTradeError(AMMError):
    """Raised when a trade is invalid (negative qty, too large, etc.)."""


@dataclass
class SwapResult:
    """Result of a successful swap."""

    amount_in: float
    amount_out: float
    fee_amount: float
    new_reserve_x: float
    new_reserve_y: float
    execution_price: float  # effective price paid (quote / base)


class ConstantProductAMM:
    """
    Constant-product automated market maker.

    Parameters
    ----------
    reserve_x : float
        Initial base asset reserve.  Must be > 0.
    reserve_y : float
        Initial quote asset reserve.  Must be > 0.
    fee_bps : int
        Fee in basis points.  Must be >= 0.
    """

    __slots__ = ("_reserve_x", "_reserve_y", "_fee_bps")

    def __init__(self, reserve_x: float, reserve_y: float, fee_bps: int = 30) -> None:
        if reserve_x <= 0 or reserve_y <= 0:
            raise InvalidReservesError(
                f"Reserves must be positive: reserve_x={reserve_x}, reserve_y={reserve_y}"
            )
        if fee_bps < 0 or fee_bps >= 10_000:
            raise ValueError(f"fee_bps must be >= 0 and < 10000: {fee_bps}")
        self._reserve_x = float(reserve_x)
        self._reserve_y = float(reserve_y)
        self._fee_bps = int(fee_bps)

    # ---- read-only properties ------------------------------------------------

    @property
    def reserve_x(self) -> float:
        """Base asset reserve."""
        return self._reserve_x

    @property
    def reserve_y(self) -> float:
        """Quote asset reserve."""
        return self._reserve_y

    @property
    def fee_bps(self) -> int:
        """Fee in basis points."""
        return self._fee_bps

    @property
    def k(self) -> float:
        """Pool invariant (reserve_x * reserve_y)."""
        return self._reserve_x * self._reserve_y

    # ---- price helpers -------------------------------------------------------

    def mid_price(self) -> float:
        """
        Mid-price = reserve_y / reserve_x.

        Raises ZeroLiquidityError if reserve_x is zero.
        """
        if self._reserve_x == 0:
            raise ZeroLiquidityError("Cannot compute mid_price: reserve_x is zero")
        return self._reserve_y / self._reserve_x

    def execution_price_buy_x(self, amount_x_out: float) -> float:
        """
        Effective price (in Y per X) to *buy* ``amount_x_out`` units of X from
        the pool (i.e. the trader sends Y and receives X).

        Does NOT mutate state.  Includes the fee.

        Raises InvalidTradeError if ``amount_x_out`` >= reserve_x.
        """
        self._validate_nonzero_liquidity()
        if amount_x_out <= 0:
            raise InvalidTradeError(f"amount_x_out must be positive: {amount_x_out}")
        if amount_x_out >= self._reserve_x:
            raise InvalidTradeError(
                f"amount_x_out ({amount_x_out}) must be < reserve_x ({self._reserve_x})"
            )
        fee_rate = self._fee_bps / 10_000
        fee_mult = 1 - fee_rate
        # Trader sends Y, receives X.  Fee is on the Y input.
        # effective Y used for constant-product = amount_y_in * fee_mult
        # We need: reserve_x - k / (reserve_y + effective_y_in) = amount_x_out
        # Solve for amount_y_in:
        new_x = self._reserve_x - amount_x_out
        new_y = self.k / new_x
        amount_y_needed_effective = new_y - self._reserve_y
        amount_y_in = amount_y_needed_effective / fee_mult
        return amount_y_in / amount_x_out

    def execution_price_sell_x(self, amount_x_in: float) -> float:
        """
        Effective price (in Y per X) when the trader *sells*
        ``amount_x_in`` units of X to the pool (sends X, receives Y).

        Does NOT mutate state.  Includes the fee.
        """
        self._validate_nonzero_liquidity()
        if amount_x_in <= 0:
            raise InvalidTradeError(f"amount_x_in must be positive: {amount_x_in}")
        fee_mult = 1 - self._fee_bps / 10_000
        effective_in = amount_x_in * fee_mult
        new_x = self._reserve_x + effective_in
        new_y = self.k / new_x
        amount_y_out = self._reserve_y - new_y
        if amount_y_out <= 0:
            raise InvalidTradeError(
                "Trade too large: would drain all quote reserves"
            )
        return amount_y_out / amount_x_in

    # ---- swap ----------------------------------------------------------------

    def swap_x_for_y(self, amount_x_in: float) -> SwapResult:
        """
        Trader sends X, receives Y.

        Mutates pool reserves.  Returns a SwapResult.
        """
        self._validate_nonzero_liquidity()
        if amount_x_in <= 0:
            raise InvalidTradeError(f"amount_x_in must be positive: {amount_x_in}")

        fee_rate = self._fee_bps / 10_000
        fee_amount = amount_x_in * fee_rate
        effective_in = amount_x_in * (1 - fee_rate)

        invariant = self.k
        # Use fee-adjusted input for constant-product output calculation
        calc_x = self._reserve_x + effective_in
        calc_y = invariant / calc_x
        amount_y_out = self._reserve_y - calc_y

        if amount_y_out <= 0:
            raise InvalidTradeError(
                "Trade would drain all quote reserves"
            )

        exec_price = amount_y_out / amount_x_in if amount_x_in > 0 else 0.0

        # Full input added to reserves; output subtracted
        self._reserve_x = self._reserve_x + amount_x_in
        self._reserve_y = self._reserve_y - amount_y_out

        logger.debug(
            "swap_x_for_y: in=%.6f  out=%.6f  fee=%.6f  exec_price=%.6f",
            amount_x_in, amount_y_out, fee_amount, exec_price,
        )

        return SwapResult(
            amount_in=amount_x_in,
            amount_out=amount_y_out,
            fee_amount=fee_amount,
            new_reserve_x=self._reserve_x,
            new_reserve_y=self._reserve_y,
            execution_price=exec_price,
        )

    def swap_y_for_x(self, amount_y_in: float) -> SwapResult:
        """
        Trader sends Y, receives X.

        Mutates pool reserves.  Returns a SwapResult.
        """
        self._validate_nonzero_liquidity()
        if amount_y_in <= 0:
            raise InvalidTradeError(f"amount_y_in must be positive: {amount_y_in}")

        fee_rate = self._fee_bps / 10_000
        fee_amount = amount_y_in * fee_rate
        effective_in = amount_y_in * (1 - fee_rate)

        invariant = self.k
        # Use fee-adjusted input for constant-product output calculation
        calc_y = self._reserve_y + effective_in
        calc_x = invariant / calc_y
        amount_x_out = self._reserve_x - calc_x

        if amount_x_out <= 0:
            raise InvalidTradeError(
                "Trade would drain all base reserves"
            )

        # execution_price is Y per X (how much Y per unit of X received)
        exec_price = amount_y_in / amount_x_out if amount_x_out > 0 else 0.0

        # Full input added to reserves; output subtracted
        self._reserve_x = self._reserve_x - amount_x_out
        self._reserve_y = self._reserve_y + amount_y_in

        logger.debug(
            "swap_y_for_x: in=%.6f  out=%.6f  fee=%.6f  exec_price=%.6f",
            amount_y_in, amount_x_out, fee_amount, exec_price,
        )

        return SwapResult(
            amount_in=amount_y_in,
            amount_out=amount_x_out,
            fee_amount=fee_amount,
            new_reserve_x=self._reserve_x,
            new_reserve_y=self._reserve_y,
            execution_price=exec_price,
        )

    # ---- pool snapshot for JSONL output --------------------------------------

    def pool_snapshot(self) -> dict:
        """Return a plain dict matching the frozen schema ``pool`` object."""
        return {
            "reserve_x": round(self._reserve_x, 4),
            "reserve_y": round(self._reserve_y, 4),
            "fee_bps": self._fee_bps,
        }

    # ---- internal helpers ----------------------------------------------------

    def _validate_nonzero_liquidity(self) -> None:
        if self._reserve_x <= 0 or self._reserve_y <= 0:
            raise ZeroLiquidityError(
                f"Pool has zero/negative liquidity: "
                f"reserve_x={self._reserve_x}, reserve_y={self._reserve_y}"
            )

    def __repr__(self) -> str:
        return (
            f"ConstantProductAMM(reserve_x={self._reserve_x:.4f}, "
            f"reserve_y={self._reserve_y:.4f}, fee_bps={self._fee_bps})"
        )

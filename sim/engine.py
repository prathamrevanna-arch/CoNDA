"""
Tick-based simulation engine.

Public API
----------
run_sim(scenario: str, seed: int) -> Iterator[dict]

The engine is import-clean: no side effects, no file I/O, no stdout on import.
"""

from __future__ import annotations

import json
import logging
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Protocol

from sim.amm import ConstantProductAMM

logger = logging.getLogger(__name__)

# ---- Scenario loading --------------------------------------------------------

SCENARIO_DIR = pathlib.Path(__file__).resolve().parent.parent / "scenarios"


@dataclass(frozen=True)
class ShockSpec:
    """One scheduled oracle shock."""

    t: int
    type: str  # e.g. "oracle_jump"
    magnitude: float  # multiplicative: new = old * (1 + magnitude)


@dataclass(frozen=True)
class AgentSpec:
    """Describes one agent to instantiate."""

    agent_id: str
    agent_class: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioConfig:
    """Parsed scenario file."""

    name: str
    ticks: int
    fee_bps: int
    initial_reserve_x: float
    initial_reserve_y: float
    oracle_start: float
    oracle_mu: float       # drift per tick  (GBM-style)
    oracle_sigma: float    # volatility per tick
    agents: List[AgentSpec]
    shocks: List[ShockSpec]

    @staticmethod
    def load(scenario_name: str) -> "ScenarioConfig":
        """Load a scenario JSON file by name (without extension)."""
        path = SCENARIO_DIR / f"{scenario_name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return ScenarioConfig(
            name=raw["name"],
            ticks=raw["ticks"],
            fee_bps=raw["fee_bps"],
            initial_reserve_x=raw["initial_reserve_x"],
            initial_reserve_y=raw["initial_reserve_y"],
            oracle_start=raw["oracle_start"],
            oracle_mu=raw.get("oracle_mu", 0.0),
            oracle_sigma=raw.get("oracle_sigma", 0.001),
            agents=[
                AgentSpec(
                    agent_id=a["agent_id"],
                    agent_class=a["agent_class"],
                    params=a.get("params", {}),
                )
                for a in raw["agents"]
            ],
            shocks=[
                ShockSpec(t=s["t"], type=s["type"], magnitude=s["magnitude"])
                for s in raw.get("shocks", [])
            ],
        )


# ---- Agent protocol ----------------------------------------------------------

class AgentProtocol(Protocol):
    """
    Minimal interface every agent must satisfy.

    ``observe`` receives the current public market state and returns an
    internal action representation (dict).
    """

    agent_id: str
    agent_class: str

    def observe(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return an action dict or None (no-op)."""
        ...


# ---- Public market state snapshot --------------------------------------------

def _build_market_state(
    t: int,
    amm: ConstantProductAMM,
    oracle_price: float,
    shock: Optional[ShockSpec],
) -> Dict[str, Any]:
    """Assemble the public state dict visible to agents."""
    return {
        "t": t,
        "mid_price": amm.mid_price(),
        "reserve_x": amm.reserve_x,
        "reserve_y": amm.reserve_y,
        "fee_bps": amm.fee_bps,
        "oracle_price": oracle_price,
        "shock": (
            {"type": shock.type, "magnitude": shock.magnitude}
            if shock is not None
            else None
        ),
    }


# ---- Tick record builders (frozen schema) ------------------------------------

def _tick_record(
    *,
    run_id: str,
    t: int,
    event: str,
    agent_id: Optional[str],
    side: Optional[str],
    price: Optional[float],
    quantity: Optional[float],
    capital: Optional[float],
    pnl: Optional[float],
    pool: dict,
    oracle_price: float,
    shock: Optional[dict],
) -> dict:
    """Build a single JSONL record conforming to the frozen schema."""
    return {
        "run_id": run_id,
        "t": t,
        "event": event,
        "agent_id": agent_id,
        "side": side,
        "price": price,
        "quantity": quantity,
        "capital": capital,
        "pnl": pnl,
        "pool": pool,
        "oracle_price": oracle_price,
        "shock": shock,
    }


def _shock_record(
    run_id: str,
    t: int,
    pool: dict,
    oracle_price: float,
    shock: ShockSpec,
) -> dict:
    """Build a shock event record (omits agent-specific fields)."""
    return _tick_record(
        run_id=run_id,
        t=t,
        event="shock",
        agent_id=None,
        side=None,
        price=None,
        quantity=None,
        capital=None,
        pnl=None,
        pool=pool,
        oracle_price=oracle_price,
        shock={"type": shock.type, "magnitude": shock.magnitude},
    )


def _meta_record(
    run_id: str,
    scenario_cfg: ScenarioConfig,
    seed: int,
) -> dict:
    """Build a meta event record (first record in the stream)."""
    return {
        "run_id": run_id,
        "t": 0,
        "event": "meta",
        "agent_id": None,
        "side": None,
        "price": None,
        "quantity": None,
        "capital": None,
        "pnl": None,
        "pool": {
            "reserve_x": scenario_cfg.initial_reserve_x,
            "reserve_y": scenario_cfg.initial_reserve_y,
            "fee_bps": scenario_cfg.fee_bps,
        },
        "oracle_price": scenario_cfg.oracle_start,
        "shock": None,
    }


# ---- Agent registry (will grow as agents are implemented) --------------------

_AGENT_REGISTRY: Dict[str, Any] = {}


def register_agent(name: str, cls: Any) -> None:
    """Register an agent class by name."""
    _AGENT_REGISTRY[name] = cls


def _create_agents(
    specs: List[AgentSpec],
    rng: Any,
) -> List[AgentProtocol]:
    """Instantiate agents from scenario specs."""
    if not _AGENT_REGISTRY:
        import sim.agents  # noqa: F401
    agents: List[AgentProtocol] = []
    for spec in specs:
        cls = _AGENT_REGISTRY.get(spec.agent_class)
        if cls is None:
            # Try importing sim.agents in case a new class was added
            import sim.agents  # noqa: F401
            cls = _AGENT_REGISTRY.get(spec.agent_class)
        if cls is None:
            raise ValueError(
                f"Unknown agent_class '{spec.agent_class}'. "
                f"Registered: {list(_AGENT_REGISTRY.keys())}"
            )
        agents.append(cls(agent_id=spec.agent_id, params=spec.params, rng=rng))
    return agents


# ---- Core engine -------------------------------------------------------------

def run_sim(scenario: str, seed: int) -> Iterator[dict]:
    """
    Run a deterministic simulation and yield schema-conformant dicts.

    Parameters
    ----------
    scenario : str
        Scenario name (maps to ``scenarios/<scenario>.json``).
    seed : int
        RNG seed for deterministic reproducibility.

    Yields
    ------
    dict
        Each dict is one JSONL record conforming to the frozen output schema.
    """
    import numpy as np

    # Local seeded RNG — no global state mutation.
    rng = np.random.default_rng(seed)

    cfg = ScenarioConfig.load(scenario)
    run_id = f"r_{cfg.name}_{seed:02d}"

    # Initialise AMM
    amm = ConstantProductAMM(
        reserve_x=cfg.initial_reserve_x,
        reserve_y=cfg.initial_reserve_y,
        fee_bps=cfg.fee_bps,
    )

    # Initialise oracle
    oracle_price: float = cfg.oracle_start

    # Build shock lookup:  tick -> ShockSpec
    shock_schedule: Dict[int, ShockSpec] = {s.t: s for s in cfg.shocks}

    # Instantiate agents
    agents = _create_agents(cfg.agents, rng)

    # Yield meta record
    yield _meta_record(run_id, cfg, seed)

    logger.info("Starting run %s  (scenario=%s, seed=%d, ticks=%d)",
                run_id, scenario, seed, cfg.ticks)

    for t in range(cfg.ticks):
        # ---- Oracle update (GBM step) ----------------------------------------
        if t > 0:
            dt = 1.0
            z = rng.standard_normal()
            oracle_price = oracle_price * np.exp(
                (cfg.oracle_mu - 0.5 * cfg.oracle_sigma ** 2) * dt
                + cfg.oracle_sigma * np.sqrt(dt) * z
            )
            # Ensure positive
            oracle_price = max(oracle_price, 1e-12)

        # ---- Scheduled shock -------------------------------------------------
        current_shock: Optional[ShockSpec] = shock_schedule.get(t)
        if current_shock is not None:
            oracle_price = oracle_price * (1 + current_shock.magnitude)
            oracle_price = max(oracle_price, 1e-12)
            yield _shock_record(
                run_id=run_id,
                t=t,
                pool=amm.pool_snapshot(),
                oracle_price=round(oracle_price, 6),
                shock=current_shock,
            )

        # ---- Agent actions ----------------------------------------------------
        state = _build_market_state(t, amm, oracle_price, current_shock)

        for agent in agents:
            action = agent.observe(state)
            if action is None:
                continue

            event = action.get("event", "quote")
            side = action.get("side", "bid")
            price = action.get("price", amm.mid_price())
            quantity = action.get("quantity", 0.0)
            capital = action.get("capital", 0.0)
            pnl = action.get("pnl", 0.0)

            # Optionally execute a trade against the AMM
            if event == "trade" and quantity > 0:
                try:
                    if side == "bid":
                        amm.swap_y_for_x(quantity)
                    else:
                        amm.swap_x_for_y(quantity)
                except Exception:
                    logger.warning(
                        "Agent %s trade rejected at t=%d", agent.agent_id, t
                    )
                    continue

            yield _tick_record(
                run_id=run_id,
                t=t,
                event=event,
                agent_id=agent.agent_id,
                side=side,
                price=round(price, 6) if price is not None else None,
                quantity=round(quantity, 6) if quantity is not None else None,
                capital=round(capital, 4) if capital is not None else None,
                pnl=round(pnl, 4) if pnl is not None else None,
                pool=amm.pool_snapshot(),
                oracle_price=round(oracle_price, 6),
                shock=None,
            )

    logger.info("Run %s completed — %d ticks", run_id, cfg.ticks)

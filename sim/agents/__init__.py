"""
sim.agents — Agent zoo for the CoNDA simulator.

Importing this package registers all implemented agent classes with the engine.
"""

from sim.engine import register_agent

from sim.agents.competitive import CompetitiveAgent
from sim.agents.cartel import CartelAgent
from sim.agents.legit_lp import LegitLPAgent

register_agent("competitive", CompetitiveAgent)
register_agent("explicit_cartel", CartelAgent)
register_agent("legitimate_coordination", LegitLPAgent)

__all__ = ["CompetitiveAgent", "CartelAgent", "LegitLPAgent"]

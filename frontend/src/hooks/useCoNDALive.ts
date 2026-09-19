import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../services/api";
import type {
  HealthResponse,
  ScenarioItem,
  MarketTick,
  RiskAssessment,
  CaseItem,
  ChallengeRequest,
  ChallengeResponse,
  WSMessage,
} from "../types/api";

// Vite proxies /ws/* → ws://127.0.0.1:8000/ws/* during dev
// Build relative WS URL from current page origin so it works through the Vite proxy
const WS_URL = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/live`;

export interface AgentLiveState {
  id: string;
  role: string;
  lastEvent: "quote" | "trade" | "meta" | "idle";
  side: "bid" | "ask" | null;
  price: number | null;
  quantity: number | null;
  capital: number | null;
  pnl: number | null;
  lastUpdateTick: number;
}

export interface PricePoint {
  t: number;
  oraclePrice: number;
  tradePrice?: number;
  quotePrice?: number;
  hasShock?: boolean;
}

const DEFAULT_AGENTS: Record<string, AgentLiveState> = {
  A1: { id: "A1", role: "Competitive Arbitrageur", lastEvent: "idle", side: null, price: null, quantity: null, capital: 50000, pnl: 0, lastUpdateTick: 0 },
  A2: { id: "A2", role: "Market Maker A", lastEvent: "idle", side: null, price: null, quantity: null, capital: 50000, pnl: 0, lastUpdateTick: 0 },
  A3: { id: "A3", role: "Market Maker B", lastEvent: "idle", side: null, price: null, quantity: null, capital: 50000, pnl: 0, lastUpdateTick: 0 },
  A4: { id: "A4", role: "Competitive Liquidity Provider", lastEvent: "idle", side: null, price: null, quantity: null, capital: 50000, pnl: 0, lastUpdateTick: 0 },
};

export function useCoNDALive() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isApiOnline, setIsApiOnline] = useState<boolean>(false);
  const [wsStatus, setWsStatus] = useState<"connected" | "connecting" | "disconnected">("disconnected");
  
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>("cartel_vs_competitive");
  
  const [runId, setRunId] = useState<string | null>(null);
  const [simulationState, setSimulationState] = useState<"idle" | "running" | "completed" | "error">("idle");
  const [currentTick, setCurrentTick] = useState<number>(0);
  const [totalTicks, setTotalTicks] = useState<number>(400);

  const [agents, setAgents] = useState<Record<string, AgentLiveState>>(DEFAULT_AGENTS);
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([]);
  const [recentEvents, setRecentEvents] = useState<MarketTick[]>([]);
  const [pool, setPool] = useState<MarketTick["pool"] | null>(null);

  const [latestRisk, setLatestRisk] = useState<RiskAssessment | null>(null);
  const [riskHistory, setRiskHistory] = useState<RiskAssessment[]>([]);

  const [cases, setCases] = useState<CaseItem[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const statusPollIntervalRef = useRef<number | null>(null);

  // ── 1. Poll System Health & Load Scenarios ──────────────────────────────────
  const checkHealth = useCallback(async () => {
    try {
      const h = await api.getHealth();
      setHealth(h);
      setIsApiOnline(true);
    } catch {
      setIsApiOnline(false);
      setHealth(null);
    }
  }, []);

  const loadScenarios = useCallback(async () => {
    try {
      const scList = await api.getScenarios();
      setScenarios(scList);
      if (scList.length > 0 && !scList.some((s) => s.id === selectedScenario)) {
        const preferred = scList.find((s) => s.id === "cartel_vs_competitive");
        setSelectedScenario(preferred ? preferred.id : scList[0].id);
      }
    } catch (err) {
      console.warn("Failed to fetch scenarios:", err);
    }
  }, [selectedScenario]);

  const loadCases = useCallback(async (activeRunId?: string) => {
    try {
      const caseList = await api.getCases(activeRunId);
      setCases(caseList);
    } catch (err) {
      console.warn("Failed to fetch cases:", err);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    loadScenarios();
    loadCases();

    const healthInterval = window.setInterval(checkHealth, 4000);
    return () => clearInterval(healthInterval);
  }, [checkHealth, loadScenarios, loadCases]);

  // ── 2. WebSocket Connection ────────────────────────────────────────────────
  useEffect(() => {
    let unmounted = false;

    function connectWs() {
      if (unmounted) return;
      setWsStatus("connecting");

      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          if (unmounted) return;
          setWsStatus("connected");
          console.log("[CoNDA WS] Live WebSocket connected");
        };

        ws.onmessage = (event) => {
          if (unmounted) return;
          try {
            const msg: WSMessage = JSON.parse(event.data);
            handleWsMessage(msg);
          } catch (err) {
            console.error("[CoNDA WS] Failed to parse message:", err);
          }
        };

        ws.onclose = () => {
          if (unmounted) return;
          setWsStatus("disconnected");
          reconnectTimeoutRef.current = window.setTimeout(connectWs, 3000);
        };

        ws.onerror = () => {
          if (unmounted) return;
          ws.close();
        };
      } catch (e) {
        setWsStatus("disconnected");
        reconnectTimeoutRef.current = window.setTimeout(connectWs, 3000);
      }
    }

    connectWs();

    return () => {
      unmounted = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // ── 3. Handle incoming WebSocket frames ─────────────────────────────────────
  const handleWsMessage = useCallback((msg: WSMessage) => {
    if (msg.type === "tick") {
      const tick = msg.payload;
      setCurrentTick(tick.t);

      // Update Pool
      if (tick.pool) {
        setPool(tick.pool);
      }

      // Update Price history (sample to keep chart responsive)
      setPriceHistory((prev) => {
        const point: PricePoint = {
          t: tick.t,
          oraclePrice: Number(tick.oracle_price.toFixed(3)),
          hasShock: Boolean(tick.shock),
        };
        if (tick.event === "trade" && tick.price !== null) {
          point.tradePrice = Number(tick.price.toFixed(3));
        } else if (tick.event === "quote" && tick.price !== null) {
          point.quotePrice = Number(tick.price.toFixed(3));
        }

        // Merge with existing t point or append
        const last = prev[prev.length - 1];
        if (last && last.t === tick.t) {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...last,
            tradePrice: point.tradePrice ?? last.tradePrice,
            quotePrice: point.quotePrice ?? last.quotePrice,
            hasShock: point.hasShock || last.hasShock,
          };
          return updated;
        }

        // Limit chart buffer to 150 points for smooth rendering
        const next = [...prev, point];
        return next.length > 150 ? next.slice(next.length - 150) : next;
      });

      // Update Recent Events log
      setRecentEvents((prev) => [tick, ...prev.slice(0, 19)]);

      // Update Agent state
      if (tick.agent_id && tick.agent_id in DEFAULT_AGENTS) {
        const agentId = tick.agent_id;
        setAgents((prev) => {
          const existing = prev[agentId] || DEFAULT_AGENTS[agentId];
          return {
            ...prev,
            [agentId]: {
              ...existing,
              lastEvent: tick.event,
              side: tick.side ?? existing.side,
              price: tick.price ?? existing.price,
              quantity: tick.quantity ?? existing.quantity,
              capital: tick.capital ?? existing.capital,
              pnl: tick.pnl ?? existing.pnl,
              lastUpdateTick: tick.t,
            },
          };
        });
      }
    } else if (msg.type === "risk") {
      const assessment = msg.payload;
      setLatestRisk(assessment);
      setRiskHistory((prev) => {
        // Prevent duplicate window entries
        const exists = prev.some(
          (p) =>
            p.window_start === assessment.window_start &&
            p.window_end === assessment.window_end &&
            p.group.join(",") === assessment.group.join(",")
        );
        return exists ? prev : [assessment, ...prev];
      });
    } else if (msg.type === "case") {
      const caseItem = msg.payload;
      setCases((prev) => {
        const idx = prev.findIndex((c) => c.case_id === caseItem.case_id);
        if (idx >= 0) {
          const updated = [...prev];
          updated[idx] = caseItem;
          return updated;
        }
        return [caseItem, ...prev];
      });
    }
  }, []);

  // ── 4. Start Run Action ─────────────────────────────────────────────────────
  const startSimulation = useCallback(
    async (scenarioOverride?: string) => {
      const scenario = scenarioOverride || selectedScenario;
      setErrorMessage(null);
      setSimulationState("running");
      setCurrentTick(0);
      setPriceHistory([]);
      setRecentEvents([]);
      setAgents(DEFAULT_AGENTS);
      setLatestRisk(null);
      setRiskHistory([]);

      try {
        const res = await api.startRun(scenario);
        setRunId(res.run_id);

        // Poll run status until done
        if (statusPollIntervalRef.current) clearInterval(statusPollIntervalRef.current);
        statusPollIntervalRef.current = window.setInterval(async () => {
          try {
            const status = await api.getRunStatus(res.run_id);
            setCurrentTick(status.tick);
            if (status.total > 0) setTotalTicks(status.total);

            if (status.state === "done") {
              setSimulationState("completed");
              if (statusPollIntervalRef.current) clearInterval(statusPollIntervalRef.current);
              // Fetch latest assessments and cases
              loadCases(res.run_id);
            }
          } catch (err) {
            console.error("Status poll error:", err);
          }
        }, 600);
      } catch (err: any) {
        setSimulationState("error");
        setErrorMessage(err.message || "Failed to start simulation");
      }
    },
    [selectedScenario, loadCases]
  );

  // ── 5. Challenge Case Action ────────────────────────────────────────────────
  const submitChallenge = useCallback(
    async (caseId: string, payload: ChallengeRequest): Promise<ChallengeResponse> => {
      const res = await api.challengeCase(caseId, payload);
      await loadCases(runId ?? undefined);
      return res;
    },
    [runId, loadCases]
  );

  return {
    health,
    isApiOnline,
    wsStatus,
    scenarios,
    selectedScenario,
    setSelectedScenario,
    runId,
    simulationState,
    currentTick,
    totalTicks,
    agents,
    priceHistory,
    recentEvents,
    pool,
    latestRisk,
    riskHistory,
    cases,
    errorMessage,
    startSimulation,
    submitChallenge,
    refreshCases: loadCases,
  };
}

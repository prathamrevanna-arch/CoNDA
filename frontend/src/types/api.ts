export interface HealthResponse {
  ok: boolean;
  chain: boolean;
  detector: "real" | "stub";
}

export interface ScenarioItem {
  id: string;
  label: string;
}

export interface StartRunRequest {
  scenario: string;
}

export interface StartRunResponse {
  run_id: string;
}

export interface RunStatusResponse {
  state: "running" | "done";
  tick: number;
  total: number;
}

export interface MarketPool {
  reserve_x: number;
  reserve_y: number;
  fee_bps: number;
}

export interface MarketShock {
  type: string;
  magnitude: number;
  t?: number;
}

export interface MarketTick {
  run_id?: string;
  t: number;
  event: "meta" | "quote" | "trade";
  agent_id: string | null;
  side: "bid" | "ask" | null;
  price: number | null;
  quantity: number | null;
  capital: number | null;
  pnl: number | null;
  pool: MarketPool;
  oracle_price: number;
  shock: MarketShock | null;
}

export interface SignalDetail {
  value: number;
  contribution: number;
  explanation: string;
}

export interface CounterfactualData {
  reference_price: number;
  observed_price: number;
  gap_pct: number;
}

export interface RiskAssessment {
  run_id: string;
  window_start: number;
  window_end: number;
  group: string[];
  risk_score: number;
  verdict: "LOW" | "MEDIUM" | "HIGH";
  signals: {
    counterfactual_gap?: SignalDetail;
    sync_under_shock?: SignalDetail;
    [key: string]: SignalDetail | undefined;
  };
  counterfactual: CounterfactualData;
  evidence_hash: string;
  computed_ms: number;
}

export interface CaseItem {
  case_id: string;
  run_id: string;
  group: string[];
  risk_score: number;
  evidence_hash: string;
  status: "OPEN" | "CHALLENGED" | "CLEARED" | "ESCALATED";
  opened_tx: string | null;
  challenge_tx: string | null;
  resolved_tx: string | null;
  opened_at_tick: number;
}

export interface ChallengeRequest {
  agent_id?: string;
  agent_address?: string;
  policy_commitment?: string;
  policy_hash?: string;
  policy_json?: any;
  signature?: string;
  flagged_action?: any;
  trace?: any;
}

export interface ChallengeResponse {
  valid: boolean;
  tx_hash: string | null;
  status: "CLEARED" | "ESCALATED";
  case_id: string;
  explanation: string;
  challenge_tx: string | null;
  resolved_tx: string | null;
}

export type WSMessage =
  | { type: "tick"; payload: MarketTick }
  | { type: "risk"; payload: RiskAssessment }
  | { type: "case"; payload: CaseItem };

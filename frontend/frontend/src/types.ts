export type Signal = {
  value: number;
  contribution: number;
  explanation: string;
};

export type TickPayload = {
  run_id: string;
  t: number;
  event: string;
  agent_id: string;
  side: 'bid' | 'ask';
  price: number;
  quantity: number;
  capital: number;
  pnl: number;
  pool: { reserve_x: number; reserve_y: number; fee_bps: number };
  oracle_price: number;
  shock: string | null;
};

export type RiskPayload = {
  run_id: string;
  window_start: number;
  window_end: number;
  group: string[];
  risk_score: number;
  verdict: 'LOW' | 'MEDIUM' | 'HIGH';
  signals: Record<string, Signal>;
  counterfactual: { reference_price: number; observed_price: number; gap_pct: number };
  evidence_hash: string;
  computed_ms: number;
};

export type CaseRecord = {
  case_id: number;
  run_id: string;
  group: string[];
  risk_score: number;
  evidence_hash: string;
  status: 'OPEN' | 'CHALLENGED' | 'CLEARED' | 'ESCALATED';
  opened_tx: string;
  challenge_tx: string | null;
  resolved_tx: string | null;
  opened_at_tick: number;
};

export type LiveMessage = { type: 'tick' | 'risk' | 'case'; payload: TickPayload | RiskPayload | CaseRecord };

export type AgentRow = { agent_id: string; lastPrice: number; pnl: number; risk: number; side: 'bid' | 'ask' };

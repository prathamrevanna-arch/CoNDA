import type {
  HealthResponse,
  ScenarioItem,
  StartRunResponse,
  RunStatusResponse,
  RiskAssessment,
  CaseItem,
  ChallengeRequest,
  ChallengeResponse,
} from "../types/api";

// During development: Vite proxies /api/* → http://127.0.0.1:8000/* (strips /api prefix)
// During production: set VITE_API_BASE env var or serve frontend from same origin as backend
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data && data.detail) {
        errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse<HealthResponse>(res);
  },

  async getScenarios(): Promise<ScenarioItem[]> {
    const res = await fetch(`${API_BASE}/scenarios`);
    return handleResponse<ScenarioItem[]>(res);
  },

  async startRun(scenario: string): Promise<StartRunResponse> {
    const res = await fetch(`${API_BASE}/run/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario }),
    });
    return handleResponse<StartRunResponse>(res);
  },

  async getRunStatus(runId: string): Promise<RunStatusResponse> {
    const res = await fetch(`${API_BASE}/run/${encodeURIComponent(runId)}/status`);
    return handleResponse<RunStatusResponse>(res);
  },

  async getLatestRisk(runId: string): Promise<RiskAssessment> {
    const res = await fetch(`${API_BASE}/risk/latest?run_id=${encodeURIComponent(runId)}`);
    return handleResponse<RiskAssessment>(res);
  },

  async getCases(runId?: string): Promise<CaseItem[]> {
    const url = runId
      ? `${API_BASE}/cases?run_id=${encodeURIComponent(runId)}`
      : `${API_BASE}/cases`;
    const res = await fetch(url);
    return handleResponse<CaseItem[]>(res);
  },

  async challengeCase(caseId: string, payload: ChallengeRequest): Promise<ChallengeResponse> {
    const res = await fetch(`${API_BASE}/case/${encodeURIComponent(caseId)}/challenge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return handleResponse<ChallengeResponse>(res);
  },
};

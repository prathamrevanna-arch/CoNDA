import { useCallback, useEffect, useRef, useState } from 'react';
import type { CaseRecord, LiveMessage, RiskPayload, TickPayload } from '@frontend/types';

const fallbackRisk: RiskPayload = {
  run_id: 'demo-2026-09-18', window_start: 100, window_end: 200, group: ['A2', 'A3'], risk_score: 87, verdict: 'HIGH',
  signals: { counterfactual_gap: { value: .043, contribution: 34, explanation: 'Observed prices remain 4.3% above the competitive reference despite stable oracle conditions.' }, sync_under_shock: { value: .82, contribution: 28, explanation: 'A2 and A3 posted matching asks within one tick of the market shock.' }, deviation_punishment: { value: .61, contribution: 15, explanation: 'Both agents reduced quote depth when an outlier deviated from the coordinated band.' }, economic_benefit: { value: .38, contribution: 10, explanation: 'The aligned strategy produced a measurable benefit relative to independent quoting.' } },
  counterfactual: { reference_price: 99.8, observed_price: 104.1, gap_pct: 4.3 }, evidence_hash: '0x8f2c...ab91', computed_ms: 12.4,
};
const seedTicks: TickPayload[] = Array.from({ length: 120 }, (_, t) => ({ run_id: 'demo-2026-09-18', t: t * 5, event: 'quote', agent_id: t % 2 ? 'A2' : 'A3', side: 'ask', price: 100 + Math.sin(t / 7) * .4 + t / 40, quantity: 5, capital: 50000, pnl: 820 + t * 3.4, pool: { reserve_x: 10420, reserve_y: 981100, fee_bps: 30 }, oracle_price: 100 + Math.sin(t / 15) * .12, shock: t === 36 || t === 72 ? 'oracle' : null }));

export function useLiveFeed() {
  const api = import.meta.env.VITE_API_URL as string | undefined;
  const [ticks, setTicks] = useState<TickPayload[]>(seedTicks);
  const [risk, setRisk] = useState<RiskPayload>(fallbackRisk);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [connection, setConnection] = useState<'live' | 'reconnecting' | 'demo'>('demo');
  const socket = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!api) { setConnection('demo'); return; }
    let retry: ReturnType<typeof setTimeout>;
    const connect = () => {
      setConnection('reconnecting');
      const ws = new WebSocket(`${api.replace(/^http/, 'ws')}/ws/live`);
      socket.current = ws;
      ws.onopen = () => setConnection('live');
      ws.onmessage = (event: MessageEvent<string>) => {
        const message = JSON.parse(event.data) as LiveMessage;
        if (message.type === 'tick') setTicks((previous) => [...previous.slice(-599), message.payload as TickPayload]);
        if (message.type === 'risk') setRisk(message.payload as RiskPayload);
        if (message.type === 'case') setCases((previous) => [message.payload as CaseRecord, ...previous]);
      };
      ws.onclose = () => { setConnection('reconnecting'); retry = setTimeout(connect, 1500); };
      ws.onerror = () => ws.close();
    };
    connect();
    return () => { clearTimeout(retry); socket.current?.close(); };
  }, [api]);

  useEffect(() => { if (!api) { fetch('/src/mocks/cases.json').then((response) => response.json()).then(setCases).catch(() => setCases([])); } }, [api]);

  const challenge = useCallback(async (caseId: number) => {
    if (api) { await fetch(`${api}/case/${caseId}/challenge`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ policy_commitment: 'demo-policy', signature: 'demo-signature', trace: 'demo-trace' }) }); }
    setCases((previous) => previous.map((item) => item.case_id === caseId ? { ...item, status: 'CHALLENGED' } : item));
  }, [api]);

  return { ticks, risk, cases, connection, challenge };
}

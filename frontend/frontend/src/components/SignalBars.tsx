import type { Signal } from '@frontend/types';
export function SignalBars({ signals }: { signals: Record<string, Signal> }) {
  return <div className="signal-list">{Object.entries(signals).map(([key, signal]) => <div className="signal" key={key}><div className="signal-top"><span>{key.replace(/_/g, ' ')}</span><strong>{signal.contribution}</strong></div><div className="bar"><span style={{ width: `${Math.min(signal.contribution * 2.5, 100)}%` }} /></div><p>{signal.explanation}</p></div>)}</div>;
}

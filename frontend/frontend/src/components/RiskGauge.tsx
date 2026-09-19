import type { CSSProperties } from 'react';

export function RiskGauge({ score }: { score: number }) {
  const tone = score >= 70 ? 'danger' : score >= 40 ? 'warning' : 'safe';
  return <div className="gauge-card"><div className="gauge-ring" style={{ '--score': `${score * 3.6}deg` } as CSSProperties}><div><strong>{score}</strong><span>/100</span></div></div><div className="gauge-copy"><span className={`eyebrow ${tone}`}>Coordination Risk</span><h3>{score}/100</h3><p>{score >= 70 ? 'High coordination signal' : score >= 40 ? 'Elevated coordination signal' : 'Low coordination signal'}</p></div></div>;
}

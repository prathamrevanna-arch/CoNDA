import { useEffect, useRef } from 'react';

type Token = { symbol: string; size: number; top: string; left: string; delay: number; duration: number; depth: number; color: string };

const tokens: Token[] = [
  { symbol: '$', size: 120, top: '15%', left: '8%', delay: 0, duration: 6, depth: 60, color: '#55c7a7' },
  { symbol: 'ETH', size: 80, top: '55%', left: '18%', delay: 1.5, duration: 7, depth: 40, color: '#8db7c5' },
  { symbol: '◆', size: 60, top: '20%', left: '75%', delay: 0.8, duration: 5.5, depth: 50, color: '#e4a853' },
  { symbol: '$', size: 90, top: '60%', left: '82%', delay: 2, duration: 8, depth: 30, color: '#55c7a7' },
  { symbol: 'BTC', size: 70, top: '35%', left: '50%', delay: 1, duration: 6.5, depth: 70, color: '#e4a853' },
  { symbol: '◆', size: 45, top: '70%', left: '45%', delay: 2.5, duration: 5, depth: 25, color: '#8db7c5' },
  { symbol: '$', size: 50, top: '10%', left: '40%', delay: 1.8, duration: 7.5, depth: 35, color: '#55c7a7' },
  { symbol: '◆', size: 35, top: '75%', left: '65%', delay: 0.5, duration: 6, depth: 20, color: '#e4a853' },
];

export function CurrencyAnimation() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      containerRef.current.style.setProperty('--mx', `${x * 20}px`);
      containerRef.current.style.setProperty('--my', `${y * 20}px`);
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div className="currency-hero" ref={containerRef}>
      <div className="currency-hero-bg" />
      <div className="currency-stage">
        {tokens.map((token, i) => (
          <div
            key={i}
            className="token"
            style={{
              '--size': `${token.size}px`,
              '--top': token.top,
              '--left': token.left,
              '--delay': `${token.delay}s`,
              '--duration': `${token.duration}s`,
              '--depth': `${token.depth}px`,
              '--color': token.color,
            } as React.CSSProperties}
          >
            <div className="token-inner">
              <div className="token-face front">
                <span style={{ fontSize: token.size * 0.35 }}>{token.symbol}</span>
              </div>
              <div className="token-face back">
                <span style={{ fontSize: token.size * 0.35 }}>{token.symbol}</span>
              </div>
              <div className="token-face edge top" />
              <div className="token-face edge bottom" />
              <div className="token-face edge left" />
              <div className="token-face edge right" />
            </div>
            <div className="token-glow" />
          </div>
        ))}
      </div>
      <div className="currency-hero-content">
        <span className="eyebrow">CoNDA — Counterfactual Nash-Deviation Attestation</span>
        <h1>Assessing coordination risk<br />in autonomous markets</h1>
        <p>A live coordination risk score, competitive counterfactual pricing, and contestable on-chain cases — all in one view</p>
      </div>
      <div className="currency-hero-fade" />
    </div>
  );
}

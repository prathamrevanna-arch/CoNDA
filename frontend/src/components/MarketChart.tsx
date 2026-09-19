import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { LineChart as ChartIcon, Zap, Coins, Clock } from "lucide-react";
import type { PricePoint } from "../hooks/useCoNDALive";
import type { MarketTick } from "../types/api";

interface MarketChartProps {
  priceHistory: PricePoint[];
  pool: MarketTick["pool"] | null;
  recentEvents: MarketTick[];
}

export const MarketChart: React.FC<MarketChartProps> = ({
  priceHistory,
  pool,
  recentEvents,
}) => {
  return (
    <div className="bg-[var(--navy-card)] rounded-xl border border-[var(--navy-border)] p-5 shadow-lg flex flex-col gap-5">
      {/* Title & Pool Stats Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--navy-border)]">
        <div className="flex items-center gap-2">
          <ChartIcon className="w-5 h-5 text-violet-400" />
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--ink)]">
              AMM Market Dynamics
            </h2>
            <p className="text-[11px] text-[var(--ink-muted)]">
              Real-time Constant Product Pool & Oracle Shocks
            </p>
          </div>
        </div>

        {/* Pool Reserves */}
        {pool && (
          <div className="flex items-center gap-4 text-xs font-mono bg-[var(--navy-elevated)] px-3 py-1.5 rounded-lg border border-[var(--navy-border)]">
            <div className="flex items-center gap-1.5">
              <Coins className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-[var(--ink-muted)]">Reserve X:</span>
              <span className="text-[var(--ink)] font-semibold">
                {pool.reserve_x.toFixed(2)}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[var(--ink-muted)]">Reserve Y:</span>
              <span className="text-[var(--ink)] font-semibold">
                ${Math.round(pool.reserve_y).toLocaleString()}
              </span>
            </div>
            <div className="text-[var(--ink-faint)]">
              Fee: {pool.fee_bps} bps
            </div>
          </div>
        )}
      </div>

      {/* Chart Section */}
      <div className="h-[260px] w-full">
        {priceHistory.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-xs font-mono text-[var(--ink-faint)] border border-dashed border-[var(--navy-border)] rounded-lg">
            <Zap className="w-6 h-6 mb-2 text-[var(--ink-faint)] animate-pulse" />
            <span>Awaiting simulation start to stream AMM market price data...</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={priceHistory} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.6} />
              <XAxis
                dataKey="t"
                stroke="#64748b"
                tick={{ fontSize: 10, fontFamily: "monospace" }}
                tickFormatter={(val) => `t=${val}`}
              />
              <YAxis
                stroke="#64748b"
                domain={["auto", "auto"]}
                tick={{ fontSize: 10, fontFamily: "monospace" }}
                tickFormatter={(val) => `$${val}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0e1424",
                  borderColor: "rgba(140, 160, 200, 0.2)",
                  borderRadius: "8px",
                  fontSize: "11px",
                  fontFamily: "monospace",
                }}
                labelFormatter={(label) => `Timestep t=${label}`}
              />
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ fontSize: "11px", fontFamily: "monospace", paddingBottom: "10px" }}
              />
              <Line
                type="stepAfter"
                dataKey="oraclePrice"
                name="Oracle Price (Ground Truth)"
                stroke="#22d3ee"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="tradePrice"
                name="Trade Execution Price"
                stroke="#f43f5e"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="quotePrice"
                name="Agent Quote Price"
                stroke="#f59e0b"
                strokeWidth={1}
                strokeDasharray="3 3"
                dot={false}
                isAnimationActive={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Real-time Streaming Ticker Events */}
      <div className="border-t border-[var(--navy-border)] pt-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-[var(--ink)]">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Live WebSocket Market Tick Stream</span>
          </div>
          <span className="text-[10px] font-mono text-[var(--ink-faint)]">
            Showing latest {recentEvents.length} frames
          </span>
        </div>

        <div className="max-h-[140px] overflow-y-auto font-mono text-[11px] space-y-1 pr-1 custom-scrollbar">
          {recentEvents.length === 0 ? (
            <div className="text-center py-4 text-[var(--ink-faint)]">
              No market ticks received yet. Click &quot;Launch Simulation&quot; to begin.
            </div>
          ) : (
            recentEvents.map((ev, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between px-2.5 py-1 rounded bg-[var(--navy-elevated)] border border-slate-800/60 hover:border-slate-700 transition text-[var(--ink-muted)]"
              >
                <div className="flex items-center gap-2">
                  <span className="text-cyan-400 font-bold">t={ev.t}</span>
                  <span
                    className={`px-1.5 py-0.2 rounded uppercase text-[9px] font-bold ${
                      ev.event === "trade"
                        ? "bg-rose-950/80 text-rose-300 border border-rose-700/50"
                        : ev.event === "quote"
                        ? "bg-amber-950/80 text-amber-300 border border-amber-700/50"
                        : "bg-slate-900 text-slate-400"
                    }`}
                  >
                    {ev.event}
                  </span>
                  {ev.agent_id && (
                    <span className="text-[var(--ink)] font-semibold">
                      {ev.agent_id}
                    </span>
                  )}
                  {ev.side && (
                    <span
                      className={
                        ev.side === "bid" ? "text-emerald-400" : "text-amber-400"
                      }
                    >
                      {ev.side.toUpperCase()}
                    </span>
                  )}
                  {ev.price !== null && (
                    <span className="text-[var(--ink)]">
                      @ ${ev.price.toFixed(2)}
                    </span>
                  )}
                  {ev.quantity !== null && ev.quantity > 0 && (
                    <span className="text-[var(--ink-faint)]">
                      (qty: {ev.quantity.toFixed(1)})
                    </span>
                  )}
                </div>

                {ev.shock && (
                  <span className="px-2 py-0.5 rounded bg-amber-900/60 text-amber-300 border border-amber-600/50 text-[10px] font-bold">
                    SHOCK: +{(ev.shock.magnitude * 100).toFixed(0)}% JUMP
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

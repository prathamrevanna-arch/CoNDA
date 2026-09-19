import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from 'recharts';
import type { TickPayload } from '@frontend/types';

export function PriceChart({ ticks }: { ticks: TickPayload[] }) {
  const data = ticks.map((tick) => ({ tick: tick.t, observed: tick.price, reference: tick.oracle_price + 0.1, shock: tick.shock }));
  const shocks = data.filter((point) => point.shock);
  return <div className="chart-wrap"><ResponsiveContainer width="100%" height={300}><LineChart data={data} margin={{ top: 12, right: 12, left: -18, bottom: 0 }}>
    <CartesianGrid stroke="#26323a" strokeDasharray="3 5" vertical={false} />
    <XAxis dataKey="tick" stroke="#65727a" tickLine={false} axisLine={false} tick={{ fill: '#77858d', fontSize: 11 }} />
    <YAxis domain={['auto', 'auto']} stroke="#65727a" tickLine={false} axisLine={false} tick={{ fill: '#77858d', fontSize: 11 }} tickFormatter={(value: number) => `$${value.toFixed(0)}`} />
    <Tooltip contentStyle={{ background: '#10171b', border: '1px solid #33434b', borderRadius: 8, color: '#eef3f1' }} labelStyle={{ color: '#91a0a5' }} formatter={((value: unknown, name: unknown) => [`$${Number(value).toFixed(2)}`, name === 'observed' ? 'Observed mid' : 'Counterfactual']) as never} />
    {shocks.map((point) => <ReferenceLine key={point.tick} x={point.tick} stroke="#e4a853" strokeDasharray="4 4" />)}
    <Line type="monotone" dataKey="reference" stroke="#7a8b91" strokeWidth={2} dot={false} />
    <Line type="monotone" dataKey="observed" stroke="#55c7a7" strokeWidth={2.5} dot={false} />
  </LineChart></ResponsiveContainer><div className="legend"><span><i className="dot observed" />Observed mid-price</span><span><i className="dot reference" />Counterfactual reference</span><span><i className="dash" />Shock tick</span></div></div>;
}

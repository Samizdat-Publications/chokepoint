'use client';
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

type DataPoint = {
  day: string;
  brent_price: number;
  vessel_count: number;
};

export default function PriceTransitChart({ data }: { data: DataPoint[] }) {
  const formatted = data.map((d) => ({
    ...d,
    day: new Date(d.day).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    }),
    brent_price: Number(d.brent_price?.toFixed(2)),
    vessel_count: Number(d.vessel_count),
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={formatted} margin={{ top: 8, right: 24, left: 0, bottom: 8 }}>
        <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#9ca3af' }} />
        <YAxis
          yAxisId="price"
          orientation="left"
          tick={{ fontSize: 11, fill: '#9ca3af' }}
          label={{ value: 'USD/bbl', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11 }}
        />
        <YAxis
          yAxisId="count"
          orientation="right"
          tick={{ fontSize: 11, fill: '#9ca3af' }}
          label={{ value: 'Tankers/day', angle: 90, position: 'insideRight', fill: '#6b7280', fontSize: 11 }}
        />
        <Tooltip
          contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 6 }}
          labelStyle={{ color: '#f9fafb' }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          yAxisId="price"
          type="monotone"
          dataKey="brent_price"
          name="Brent Crude (USD/bbl)"
          stroke="#f97316"
          dot={false}
          strokeWidth={2}
        />
        <Line
          yAxisId="count"
          type="monotone"
          dataKey="vessel_count"
          name="Hormuz Tankers/day"
          stroke="#3b82f6"
          dot={false}
          strokeWidth={2}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

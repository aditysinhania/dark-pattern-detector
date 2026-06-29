import {
  BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import type { PatternDistribution } from "../../types";

const COLORS = [
  "#4f6ef7", "#f59e0b", "#ef4444",
  "#22c55e", "#7c3aed", "#06b6d4",
  "#ec4899", "#84cc16",
];

interface PatternChartProps {
  data: PatternDistribution[];
}

export function PatternChart({ data }: PatternChartProps) {
  const formatted = data.map((d) => ({
    ...d,
    name: d.category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={formatted} layout="vertical" margin={{ left: 120 }}>
        <XAxis type="number" tick={{ fill: "#9ca3af", fontSize: 12 }} />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          width={120}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#111827",
            border: "1px solid #374151",
            borderRadius: "8px",
            color: "#f9fafb",
          }}
        />
        <Bar dataKey="count" radius={[0, 4, 4, 0]}>
          {formatted.map((_, index) => (
            <Cell key={index} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
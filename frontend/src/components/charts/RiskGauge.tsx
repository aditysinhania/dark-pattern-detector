import { PieChart, Pie, Cell } from "recharts";

interface RiskGaugeProps {
  score: number; // 0.0 to 1.0
  size?: number;
}

const RISK_COLORS = {
  low:      "#22c55e",
  medium:   "#f59e0b",
  high:     "#ef4444",
  critical: "#7c3aed",
};

function getRiskLevel(score: number) {
  if (score < 0.3)  return "low";
  if (score < 0.6)  return "medium";
  if (score < 0.8)  return "high";
  return "critical";
}

export function RiskGauge({ score, size = 160 }: RiskGaugeProps) {
  const level    = getRiskLevel(score);
  const color    = RISK_COLORS[level];
  const pct      = Math.round(score * 100);
  const data     = [{ value: pct }, { value: 100 - pct }];

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative">
        <PieChart width={size} height={size}>
          <Pie
            data={data}
            cx={size / 2}
            cy={size / 2}
            innerRadius={size * 0.35}
            outerRadius={size * 0.48}
            startAngle={90}
            endAngle={-270}
            dataKey="value"
            strokeWidth={0}
          >
            <Cell fill={color} />
            <Cell fill="#1f2937" />
          </Pie>
        </PieChart>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-white">{pct}</span>
          <span className="text-xs text-gray-400">/ 100</span>
        </div>
      </div>
      <span
        className="text-sm font-semibold capitalize"
        style={{ color }}
      >
        {level} Risk
      </span>
    </div>
  );
}
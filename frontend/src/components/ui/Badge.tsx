import { clsx } from "clsx";

type BadgeVariant = "low" | "medium" | "high" | "critical" | "default" | "info";

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variants: Record<BadgeVariant, string> = {
  low:      "bg-green-900/40 text-green-400 border-green-800",
  medium:   "bg-yellow-900/40 text-yellow-400 border-yellow-800",
  high:     "bg-red-900/40 text-red-400 border-red-800",
  critical: "bg-purple-900/40 text-purple-400 border-purple-800",
  default:  "bg-gray-800 text-gray-400 border-gray-700",
  info:     "bg-blue-900/40 text-blue-400 border-blue-800",
};

export function Badge({ variant = "default", children, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
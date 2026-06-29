import {
  Search, Shield, AlertTriangle, TrendingUp
} from "lucide-react";
import { Link } from "react-router-dom";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { PatternChart } from "../../components/charts/PatternChart";
import { useDashboardStats, useScanHistory } from "../../hooks/useScan";
import { useAuthStore } from "../../store/auth.store";
import { Badge } from "../../components/ui/Badge";
import type { RiskLevel } from "../../types";

function StatCard({
  label, value, icon: Icon, color,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <Card className="flex items-center gap-4">
      <div className={`p-3 rounded-xl ${color}`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{value}</p>
        <p className="text-sm text-gray-400">{label}</p>
      </div>
    </Card>
  );
}

export function DashboardPage() {
  const { user }       = useAuthStore();
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: scans, isLoading: scansLoading } = useScanHistory(1);

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Welcome back, {user?.full_name?.split(" ")[0]}
          </h1>
          <p className="text-gray-400 mt-1">
            Here's an overview of your dark pattern detections
          </p>
        </div>
        <Link to="/scanner">
          <Button size="lg">
            <Search className="w-4 h-4" />
            New Scan
          </Button>
        </Link>
      </div>

      {/* Stats */}
      {statsLoading ? (
        <div className="flex justify-center py-8">
          <LoadingSpinner />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <StatCard
            label="Total Scans"
            value={stats?.total_scans ?? 0}
            icon={Search}
            color="bg-brand-500"
          />
          <StatCard
            label="Patterns Detected"
            value={stats?.total_patterns_found ?? 0}
            icon={AlertTriangle}
            color="bg-yellow-600"
          />
          <StatCard
            label="Completed Scans"
            value={stats?.completed_scans ?? 0}
            icon={Shield}
            color="bg-green-600"
          />
          <StatCard
            label="Failed Scans"
            value={stats?.failed_scans ?? 0}
            icon={TrendingUp}
            color="bg-red-600"
          />
        </div>
      )}

      {/* Recent scans */}
      <Card title="Recent Scans" description="Your latest website analyses">
        {scansLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner />
          </div>
        ) : scans?.data.length === 0 ? (
          <div className="text-center py-12">
            <Shield className="w-12 h-12 text-gray-700 mx-auto mb-4" />
            <p className="text-gray-400">No scans yet</p>
            <Link to="/scanner" className="mt-4 inline-block">
              <Button variant="secondary" size="sm">
                Run your first scan
              </Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {scans?.data.slice(0, 5).map((scan) => (
              <Link
                key={scan.id}
                to={`/scans/${scan.id}`}
                className="flex items-center justify-between p-4 bg-gray-800 rounded-lg hover:bg-gray-750 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-100 truncate">
                    {scan.url}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {new Date(scan.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  {scan.risk_level && (
                    <Badge variant={scan.risk_level as RiskLevel}>
                      {scan.risk_level}
                    </Badge>
                  )}
                  <Badge
                    variant={
                      scan.status === "completed" ? "low" :
                      scan.status === "failed"    ? "high" : "info"
                    }
                  >
                    {scan.status}
                  </Badge>
                </div>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
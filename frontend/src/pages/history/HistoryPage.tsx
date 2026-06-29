import { useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, Search } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useScanHistory } from "../../hooks/useScan";
import type { RiskLevel } from "../../types";

export function HistoryPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useScanHistory(page);

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Scan History</h1>
        <p className="text-gray-400 mt-1">All your previous website analyses</p>
      </div>

      <Card>
        {isLoading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : data?.data.length === 0 ? (
          <div className="text-center py-12">
            <Search className="w-10 h-10 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-400">No scans yet</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b border-gray-800">
                    <th className="pb-3 font-medium text-gray-400">URL</th>
                    <th className="pb-3 font-medium text-gray-400">Status</th>
                    <th className="pb-3 font-medium text-gray-400">Risk</th>
                    <th className="pb-3 font-medium text-gray-400">Patterns</th>
                    <th className="pb-3 font-medium text-gray-400">Date</th>
                    <th className="pb-3 font-medium text-gray-400" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {data?.data.map((scan) => (
                    <tr key={scan.id} className="hover:bg-gray-800/50 transition-colors">
                      <td className="py-3 pr-4">
                        <p className="text-gray-100 truncate max-w-xs">
                          {scan.page_title || scan.url}
                        </p>
                        <p className="text-gray-500 text-xs truncate max-w-xs">
                          {scan.url}
                        </p>
                      </td>
                      <td className="py-3 pr-4">
                        <Badge
                          variant={
                            scan.status === "completed" ? "low" :
                            scan.status === "failed"    ? "high" : "info"
                          }
                        >
                          {scan.status}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4">
                        {scan.risk_level ? (
                          <Badge variant={scan.risk_level as RiskLevel}>
                            {scan.risk_level}
                          </Badge>
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className="py-3 pr-4 text-gray-300">
                        {scan.patterns_found}
                      </td>
                      <td className="py-3 pr-4 text-gray-400 whitespace-nowrap">
                        {new Date(scan.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3">
                        <Link to={`/scans/${scan.id}`}>
                          <Button variant="ghost" size="sm">
                            <ExternalLink className="w-3.5 h-3.5" />
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {data && data.total_pages > 1 && (
              <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-800">
                <p className="text-sm text-gray-400">
                  Page {data.page} of {data.total_pages} ({data.total} scans)
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page === data.total_pages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
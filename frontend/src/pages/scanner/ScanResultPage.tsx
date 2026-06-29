import { useParams, Link } from "react-router-dom";
import {
  AlertTriangle, CheckCircle, XCircle,
  Clock, ArrowLeft, ExternalLink,
} from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { RiskGauge } from "../../components/charts/RiskGauge";
import { useScanPoller } from "../../hooks/useScan";
import type { RiskLevel } from "../../types";

function StatusIcon({ status }: { status: string }) {
  if (status === "completed")  return <CheckCircle className="w-5 h-5 text-green-400" />;
  if (status === "failed")     return <XCircle className="w-5 h-5 text-red-400" />;
  return <Clock className="w-5 h-5 text-yellow-400 animate-pulse" />;
}

export function ScanResultPage() {
  const { scanId }                           = useParams<{ scanId: string }>();
  const { scan, isLoading, isPolling }       = useScanPoller(scanId ?? null);

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-96">
        <div className="text-center space-y-4">
          <LoadingSpinner size="lg" />
          <p className="text-gray-400">Loading scan...</p>
        </div>
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="p-8 text-center">
        <p className="text-gray-400">Scan not found</p>
        <Link to="/scanner">
          <Button variant="secondary" className="mt-4">
            Back to Scanner
          </Button>
        </Link>
      </div>
    );
  }

  const isProcessing = scan.status === "pending" || scan.status === "processing";

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/scanner">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <StatusIcon status={scan.status} />
            <h1 className="text-xl font-bold text-white truncate">
              {scan.page_title || scan.url}
            </h1>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <a
              href={scan.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-400 hover:text-brand-400 flex items-center gap-1"
            >
              {scan.url}
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>

      {/* Processing state */}
      {isProcessing && (
        <Card>
          <div className="flex flex-col items-center py-8 gap-4">
            <LoadingSpinner size="lg" />
            <div className="text-center">
              <p className="text-white font-medium">
                {scan.status === "pending"
                  ? "Queued for analysis..."
                  : "AI pipeline running..."}
              </p>
              <p className="text-sm text-gray-400 mt-1">
                This usually takes 15–30 seconds
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Failed state */}
      {scan.status === "failed" && (
        <Card>
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-white font-medium">Scan failed</p>
              <p className="text-sm text-gray-400 mt-1">
                {scan.error_message || "An unknown error occurred"}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Completed results */}
      {scan.status === "completed" && (
        <>
          {/* Risk overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="flex flex-col items-center justify-center py-6">
              {scan.risk_score !== null && (
                <RiskGauge score={scan.risk_score} />
              )}
            </Card>
            <Card className="md:col-span-2 space-y-4">
              <div>
                <p className="text-sm text-gray-400">URL</p>
                <p className="text-white font-medium truncate">{scan.url}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-400">Patterns found</p>
                  <p className="text-2xl font-bold text-white">
                    {scan.patterns_found}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Risk level</p>
                  {scan.risk_level && (
                    <Badge
                      variant={scan.risk_level as RiskLevel}
                      className="mt-1 text-sm"
                    >
                      {scan.risk_level.toUpperCase()}
                    </Badge>
                  )}
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-400">Scanned</p>
                <p className="text-white text-sm">
                  {new Date(scan.created_at).toLocaleString()}
                </p>
              </div>
            </Card>
          </div>

          {/* Detected patterns */}
          {scan.detected_patterns?.length > 0 && (
            <Card
              title="Detected Dark Patterns"
              description="Each pattern is explained with confidence scores and improvement suggestions"
            >
              <div className="space-y-4 mt-2">
                {scan.detected_patterns.map((pattern) => (
                  <div
                    key={pattern.id}
                    className="border border-gray-800 rounded-lg p-4 space-y-3"
                  >
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-yellow-400" />
                        <span className="font-medium text-white capitalize">
                          {pattern.category.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="default">
                          {pattern.detection_method.replace(/_/g, " ")}
                        </Badge>
                        <Badge
                          variant={
                            pattern.confidence_score > 0.8 ? "high" :
                            pattern.confidence_score > 0.6 ? "medium" : "low"
                          }
                        >
                          {Math.round(pattern.confidence_score * 100)}% confidence
                        </Badge>
                      </div>
                    </div>

                    <p className="text-sm text-gray-300">
                      {pattern.explanation}
                    </p>

                    {pattern.flagged_text && (
                      <div className="bg-red-900/20 border border-red-800/50 rounded-lg px-3 py-2">
                        <p className="text-xs text-gray-400 mb-1">Flagged text</p>
                        <p className="text-sm text-red-300 italic">
                          "{pattern.flagged_text}"
                        </p>
                      </div>
                    )}

                    {pattern.suggestion && (
                      <div className="bg-green-900/20 border border-green-800/50 rounded-lg px-3 py-2">
                        <p className="text-xs text-gray-400 mb-1">Suggestion</p>
                        <p className="text-sm text-green-300">
                          {pattern.suggestion}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {scan.patterns_found === 0 && (
            <Card>
              <div className="flex flex-col items-center py-8 gap-3">
                <CheckCircle className="w-12 h-12 text-green-400" />
                <p className="text-white font-medium text-lg">
                  No dark patterns detected
                </p>
                <p className="text-gray-400 text-sm text-center max-w-sm">
                  This website appears to follow ethical UX practices.
                  No manipulative patterns were found.
                </p>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Shield, AlertTriangle, Globe } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { useSubmitScan } from "../../hooks/useScan";

export function ScannerPage() {
  const [url, setUrl]     = useState("");
  const submitScan        = useSubmitScan();
  const navigate          = useNavigate();

  const handleScan = async () => {
    if (!url.trim()) return;
    const scan = await submitScan.mutateAsync(url.trim());
    navigate(`/scans/${scan.id}`);
  };

  const exampleSites = [
    "https://www.booking.com",
    "https://www.amazon.com",
    "https://www.linkedin.com",
  ];

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Website Scanner</h1>
        <p className="text-gray-400 mt-1">
          Enter any website URL to detect dark patterns using AI
        </p>
      </div>

      {/* Scanner input */}
      <Card>
        <div className="space-y-4">
          <div className="flex gap-3">
            <div className="flex-1">
              <Input
                placeholder="https://example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleScan()}
              />
            </div>
            <Button
              onClick={handleScan}
              isLoading={submitScan.isPending}
              size="md"
              className="shrink-0"
            >
              <Search className="w-4 h-4" />
              Analyze
            </Button>
          </div>

          {/* Quick examples */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-500">Try:</span>
            {exampleSites.map((site) => (
              <button
                key={site}
                onClick={() => setUrl(site)}
                className="text-xs text-brand-400 hover:underline"
              >
                {site.replace("https://www.", "")}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* What we detect */}
      <Card title="What we detect" description="AI-powered detection across 13 dark pattern categories">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
          {[
            "Confirm Shaming",
            "Fake Urgency",
            "Hidden Costs",
            "Scarcity Messages",
            "Subscription Traps",
            "Privacy Zuckering",
            "Roach Motel",
            "Sneak into Basket",
            "Forced Continuity",
            "Fake Countdown Timers",
            "Interface Interference",
            "Obstruction",
            "Misdirection",
          ].map((pattern) => (
            <div
              key={pattern}
              className="flex items-center gap-2 text-sm text-gray-400"
            >
              <Shield className="w-3.5 h-3.5 text-brand-500 shrink-0" />
              {pattern}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
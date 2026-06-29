import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { scanService } from "../services/scan.service";
import type { ScanDetail } from "../types";

export function useSubmitScan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (url: string) => scanService.submitScan(url),
    onSuccess: () => {
      // Invalidate scan history so it refreshes
      queryClient.invalidateQueries({ queryKey: ["scans"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}

/**
 * Polls a scan until it completes or fails.
 *
 * Why polling instead of WebSockets?
 * WebSockets add significant complexity (connection management,
 * reconnection logic, server-side broadcast). For scan results
 * that take 10-30 seconds, polling every 3 seconds is simpler
 * and perfectly adequate. The user experience is identical.
 *
 * In a future phase, WebSockets could replace this for
 * real-time progress updates (e.g. "Extracting DOM... Running NLP...")
 */
export function useScanPoller(scanId: string | null) {
  const [isPolling, setIsPolling] = useState(true);

  const query = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => scanService.getScan(scanId!),
    enabled: !!scanId && isPolling,
    refetchInterval: (data) => {
      // Stop polling when scan is done
      if (
        data?.state?.data?.status === "completed" ||
        data?.state?.data?.status === "failed"
      ) {
        setIsPolling(false);
        return false;
      }
      return 3000; // Poll every 3 seconds
    },
  });

  return {
    scan: query.data,
    isLoading: query.isLoading,
    isPolling,
    isComplete: query.data?.status === "completed",
    isFailed: query.data?.status === "failed",
  };
}

export function useScanHistory(page = 1) {
  return useQuery({
    queryKey: ["scans", page],
    queryFn: () => scanService.listScans(page),
  });
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: scanService.getDashboardStats,
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  });
}
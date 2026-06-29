import api from "./api";
import type {
  ApiResponse,
  PaginatedResponse,
  Scan,
  ScanDetail,
  DashboardStats,
  PatternDistribution,
} from "../types";

export const scanService = {
  async submitScan(url: string): Promise<Scan> {
    const res = await api.post<ApiResponse<Scan>>("/scans/", { url });
    return res.data.data;
  },

  async getScan(scanId: string): Promise<ScanDetail> {
    const res = await api.get<ApiResponse<ScanDetail>>(`/scans/${scanId}`);
    return res.data.data;
  },

  async listScans(page = 1, pageSize = 20): Promise<PaginatedResponse<Scan>> {
    const res = await api.get<PaginatedResponse<Scan>>("/scans/", {
      params: { page, page_size: pageSize },
    });
    return res.data;
  },

  async getDashboardStats(): Promise<DashboardStats> {
    const res = await api.get<ApiResponse<DashboardStats>>(
      "/scans/dashboard/stats"
    );
    return res.data.data;
  },
};
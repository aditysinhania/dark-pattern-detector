// ── Auth ─────────────────────────────────────────────────────────────────────

export type UserRole = "user" | "admin" | "moderator";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface UserProfile extends User {
  total_scans: number;
  total_patterns_found: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface RegisterResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ── Scans ────────────────────────────────────────────────────────────────────

export type ScanStatus = "pending" | "processing" | "completed" | "failed";
export type RiskLevel  = "low" | "medium" | "high" | "critical";

export interface DetectedPattern {
  id: string;
  category: string;
  detection_method: string;
  confidence_score: number;
  explanation: string;
  flagged_text: string | null;
  suggestion: string | null;
}

export interface Scan {
  id: string;
  url: string;
  status: ScanStatus;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  patterns_found: number;
  page_title: string | null;
  screenshot_path: string | null;
  task_id: string | null;
  error_message: string | null;
  created_at: string;
}

export interface ScanDetail extends Scan {
  detected_patterns: DetectedPattern[];
}

// ── Reports ──────────────────────────────────────────────────────────────────

export interface Report {
  id: string;
  scan_id: string;
  total_patterns: number;
  risk_score: number;
  summary: string | null;
  report_data: ReportData | null;
  is_saved: boolean;
  created_at: string;
}

export interface ReportData {
  url: string;
  page_title: string;
  risk_score: number;
  risk_level: string;
  patterns_found: number;
  detections: DetectedPattern[];
  recommendations: Recommendation[];
}

export interface Recommendation {
  priority: number;
  pattern: string;
  action: string;
  confidence: number;
}

// ── API responses ─────────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface PaginatedResponse<T> {
  success: boolean;
  message: string;
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface DashboardStats {
  total_scans: number;
  total_patterns_found: number;
  completed_scans: number;
  failed_scans: number;
}

export interface PatternDistribution {
  category: string;
  count: number;
}
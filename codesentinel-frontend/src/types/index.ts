export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'clean';

export interface CWEEstimate {
  cwe_id: string;
  score: number;
}

export interface LineAttribution {
  line: number;
  score: number;
  snippet: string;
}

export interface ScoreFileResult {
  is_vulnerable: boolean;
  confidence: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  predicted_cwe: CWEEstimate[];
  line_attributions: LineAttribution[];
  model_version: string;
}

export interface ScoreFileRequest {
  code_snippet: string;
  language?: string;
}

export interface ScoreFileResponse {
  request_id: string;
  timestamp: string;
  result: ScoreFileResult;
}

export interface Finding {
  file_path: string;
  line_number: number;
  cwe_id: string | null;
  severity: string;
  confidence: number;
  snippet: string;
  model_version: string;
}

export interface AnalyzePRRequest {
  repo: string;
  pr_number: number;
  diff?: string;
  commit_sha?: string;
  github_repo_id?: number;
  installation_id?: number;
}

export interface AnalyzePRResponse {
  scan_id: string;
  status: string;
  severity: string | null;
  findings: Finding[];
}

export interface HistoryItem {
  scan_id: string;
  repo: string;
  pr_number: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  severity: string | null;
}

export interface HistoryResponse {
  items: HistoryItem[];
  page: number;
  page_size: number;
  total: number;
}

export interface HistoryFilters {
  repo?: string;
  severity?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface SystemHealth {
  status: 'online' | 'offline' | 'checking';
  latencyMs?: number;
  timestamp?: string;
  error?: string;
}

export interface CWEInfo {
  id: string;
  name: string;
  description: string;
  owaspTop10?: string;
  remediation: string;
}

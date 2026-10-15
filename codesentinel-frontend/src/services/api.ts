import axios, { AxiosError, AxiosInstance } from 'axios';
import {
  AnalyzePRRequest,
  AnalyzePRResponse,
  HistoryFilters,
  HistoryResponse,
  ScoreFileRequest,
  ScoreFileResponse,
  SystemHealth
} from '../types';

export const getApiBaseUrl = (): string => {
  const customUrl = localStorage.getItem('codesentinel_api_url');
  if (customUrl && customUrl.trim()) {
    return customUrl.trim().replace(/\/+$/, '');
  }
  return (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
};

export const setCustomApiBaseUrl = (url: string | null): void => {
  if (url && url.trim()) {
    localStorage.setItem('codesentinel_api_url', url.trim());
  } else {
    localStorage.removeItem('codesentinel_api_url');
  }
};

export const getAuthToken = (): string | null => {
  return localStorage.getItem('codesentinel_jwt_token');
};

export const setAuthToken = (token: string | null): void => {
  if (token && token.trim()) {
    localStorage.setItem('codesentinel_jwt_token', token.trim());
  } else {
    localStorage.removeItem('codesentinel_jwt_token');
  }
};

const createApiClient = (): AxiosInstance => {
  const instance = axios.create({
    baseURL: getApiBaseUrl(),
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  });

  instance.interceptors.request.use((config) => {
    // Dynamically update baseURL in case user changed it in Settings
    config.baseURL = getApiBaseUrl();
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  return instance;
};

const apiClient = createApiClient();

export function formatApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<{ detail?: any; message?: string }>;
    
    if (!axiosErr.response) {
      return `Cannot reach CodeSentinel backend at ${getApiBaseUrl()}. Please verify the FastAPI server is running.`;
    }

    const { status, data } = axiosErr.response;

    if (data?.detail) {
      if (typeof data.detail === 'string') {
        return data.detail;
      }
      if (Array.isArray(data.detail)) {
        // FastAPI / Pydantic validation error array
        return data.detail
          .map((item: any) => `${item.loc ? item.loc.join('.') + ': ' : ''}${item.msg || 'Invalid field'}`)
          .join(', ');
      }
      return JSON.stringify(data.detail);
    }

    if (status === 401) return 'Authentication required. Check your JWT token in Settings.';
    if (status === 403) return 'Access forbidden. You do not have permissions for this resource.';
    if (status === 404) return 'Requested resource or scan was not found.';
    if (status === 422) return 'Validation error: The submitted data does not meet schema requirements.';
    if (status >= 500) return `Backend Server Error (${status}): Internal analysis error in model or database.`;

    return axiosErr.message || `Request failed with status ${status}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred during API communication.';
}

export const CodeSentinelApi = {
  /**
   * Check FastAPI backend health and ping latency
   */
  async checkHealth(): Promise<SystemHealth> {
    const startTime = performance.now();
    try {
      const response = await apiClient.get('/health', { timeout: 5000 });
      const latencyMs = Math.round(performance.now() - startTime);
      return {
        status: response.data?.status === 'ok' ? 'online' : 'offline',
        latencyMs,
        timestamp: new Date().toISOString(),
      };
    } catch (err) {
      return {
        status: 'offline',
        error: formatApiError(err),
        timestamp: new Date().toISOString(),
      };
    }
  },

  /**
   * Score a source code snippet for security vulnerabilities
   * POST /score-file
   */
  async scoreFile(request: ScoreFileRequest): Promise<ScoreFileResponse> {
    if (!request.code_snippet || !request.code_snippet.trim()) {
      throw new Error('Code snippet cannot be empty');
    }
    const payload = {
      code_snippet: request.code_snippet,
      language: request.language || 'auto',
    };
    const response = await apiClient.post<ScoreFileResponse>('/score-file', payload);
    return response.data;
  },

  /**
   * Trigger pull request vulnerability analysis
   * POST /analyze-pr
   */
  async analyzePR(data: AnalyzePRRequest): Promise<AnalyzePRResponse> {
    if (!data.repo || !data.repo.includes('/')) {
      throw new Error('Repository must be formatted as "owner/repository"');
    }
    if (!data.pr_number || data.pr_number <= 0) {
      throw new Error('Pull Request number must be a positive integer');
    }

    const payload: Record<string, any> = {
      repo: data.repo.trim(),
      pr_number: Number(data.pr_number),
    };

    if (data.diff) payload.diff = data.diff;
    if (data.commit_sha) payload.commit_sha = data.commit_sha.trim();
    if (data.github_repo_id) payload.github_repo_id = Number(data.github_repo_id);
    if (data.installation_id) payload.installation_id = Number(data.installation_id);

    const response = await apiClient.post<AnalyzePRResponse>('/analyze-pr', payload);
    return response.data;
  },

  /**
   * Fetch scan history with optional filters and pagination
   * GET /history
   */
  async getHistory(filters: HistoryFilters = {}): Promise<HistoryResponse> {
    const params: Record<string, any> = {};
    if (filters.repo && filters.repo.trim()) {
      const cleanRepo = filters.repo.trim();
      if (cleanRepo.includes('/')) {
        params.repo = cleanRepo;
      }
    }
    if (filters.severity) {
      const sev = filters.severity.toLowerCase().trim();
      if (['low', 'medium', 'high', 'critical'].includes(sev)) {
        params.severity = sev;
      }
    }
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;
    if (filters.page) params.page = Number(filters.page);
    if (filters.page_size) params.page_size = Number(filters.page_size);

    const response = await apiClient.get<HistoryResponse>('/history', { params });
    return response.data;
  },

  /**
   * Fetch specific scan details and findings
   * GET /scans/{scan_id}
   */
  async getScanDetails(scanId: string): Promise<AnalyzePRResponse> {
    const response = await apiClient.get<AnalyzePRResponse>(`/scans/${scanId}`);
    return response.data;
  }
};

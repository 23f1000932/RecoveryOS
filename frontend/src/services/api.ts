/**
 * RecoveryOS — API Client
 *
 * All HTTP calls to the backend.
 * Never make fetch() calls from components or pages directly.
 * Use this client everywhere.
 *
 * Financial values come back as strings — do not parseFloat() them
 * for display; format them for INR display using formatINR().
 */

import type {
  ApprovalResponse,
  AuditLogResponse,
  DashboardSummary,
  ExecuteResponse,
  HealthResponse,
  PolicyView,
  RecoveryCaseDetail,
  RecoveryCaseListResponse,
  SimulatorResult,
  SimulatorRunRequest,
  SimulatorRunResponse,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// ── Utilities ─────────────────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new ApiClientError(res.status, body?.error?.message ?? res.statusText, body?.error?.code);
  }

  return res.json() as Promise<T>;
}

export class ApiClientError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code?: string,
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}

// ── Format Utilities ──────────────────────────────────────────────────────────

/**
 * Format a numeric string (from backend) as INR currency.
 * E.g. "12500.00" → "₹12,500"
 */
export function formatINR(value: string | null | undefined): string {
  if (value == null || value === '') return '₹0';
  const num = parseFloat(value);
  if (isNaN(num)) return '₹0';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(num);
}

/**
 * Format a recovery rate [0, 1] as a percentage string.
 * E.g. 0.745 → "74.5%"
 */
export function formatPercent(rate: number, decimals = 1): string {
  return `${(rate * 100).toFixed(decimals)}%`;
}

/**
 * Format an action type as a human-readable label.
 */
export function formatAction(action: string | null | undefined): string {
  if (!action) return '—';
  return action
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

// ── API Endpoints ─────────────────────────────────────────────────────────────

export const api = {
  // Health
  health: (): Promise<HealthResponse> =>
    request('/health'),

  // Dashboard
  getDashboardSummary: (): Promise<DashboardSummary> =>
    request('/api/dashboard/summary'),

  // Recovery Cases
  listCases: (params?: { status?: string; page?: number; page_size?: number }): Promise<RecoveryCaseListResponse> => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set('status', params.status);
    if (params?.page) qs.set('page', String(params.page));
    if (params?.page_size) qs.set('page_size', String(params.page_size));
    const query = qs.toString();
    return request(`/api/recovery-cases${query ? `?${query}` : ''}`);
  },

  getCase: (caseId: string): Promise<RecoveryCaseDetail> =>
    request(`/api/recovery-cases/${caseId}`),

  analyzeCase: (caseId: string): Promise<unknown> =>
    request(`/api/recovery-cases/${caseId}/analyze`, { method: 'POST' }),

  approveCase: (caseId: string, actor = 'merchant'): Promise<ApprovalResponse> =>
    request(`/api/recovery-cases/${caseId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ actor }),
    }),

  rejectCase: (caseId: string, actor = 'merchant', reason?: string): Promise<ApprovalResponse> =>
    request(`/api/recovery-cases/${caseId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ actor, reason }),
    }),

  executeCase: (caseId: string, actor = 'merchant'): Promise<ExecuteResponse> =>
    request(`/api/recovery-cases/${caseId}/execute`, {
      method: 'POST',
      body: JSON.stringify({ actor }),
    }),

  stopCase: (caseId: string): Promise<{ case_id: string; case_status: string; message: string }> =>
    request(`/api/recovery-cases/${caseId}/stop`, { method: 'POST' }),

  getCaseAudit: (caseId: string): Promise<AuditLogResponse> =>
    request(`/api/recovery-cases/${caseId}/audit`),

  // Simulator
  runSimulation: (params: SimulatorRunRequest): Promise<SimulatorRunResponse> =>
    request('/api/simulator/run', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  getExperiment: (experimentId: string): Promise<SimulatorResult> =>
    request(`/api/simulator/${experimentId}`),

  // Policies
  getPolicy: (): Promise<PolicyView> =>
    request('/api/policies'),
};

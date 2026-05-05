import axios from 'axios';
import type { CompanyValuationInput, ValuationResponse } from '../types/valuation';

const api = axios.create({ baseURL: '/api' });

// ---------------------------------------------------------------------------
// Admin token — stored in localStorage. When set, every request carries it
// in the X-Admin-Token header so admin endpoints succeed; all other endpoints
// ignore it.
// ---------------------------------------------------------------------------

const ADMIN_TOKEN_KEY = 'ad_cc_admin_token';

export function getAdminToken(): string | null {
  try {
    return localStorage.getItem(ADMIN_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAdminToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(ADMIN_TOKEN_KEY, token);
    else localStorage.removeItem(ADMIN_TOKEN_KEY);
  } catch {
    /* localStorage unavailable */
  }
}

api.interceptors.request.use((config) => {
  const token = getAdminToken();
  if (token) {
    config.headers = config.headers ?? {};
    (config.headers as Record<string, string>)['X-Admin-Token'] = token;
  }
  return config;
});

export interface SearchResult {
  exchange_ticker: string;
  company_name: string;
  country: string;
  industry: string;
  exchange: string;
  symbol: string;
  region: string;
}

export async function searchCompanies(query: string): Promise<SearchResult[]> {
  const { data } = await api.get('/search', { params: { q: query, max_results: 20 } });
  return data.results;
}

export async function fetchByTicker(
  ticker: string,
  region = 'US',
  riskFreeRate = 0.0425,
  signal?: AbortSignal,
): Promise<ValuationResponse> {
  const { data } = await api.post('/valuation/fetch', {
    ticker,
    region,
    risk_free_rate: riskFreeRate,
  }, { signal });
  return data;
}

export async function createValuation(inputs: CompanyValuationInput): Promise<ValuationResponse> {
  const { data } = await api.post('/valuation', { inputs });
  return data;
}

export async function getValuation(id: string): Promise<ValuationResponse> {
  const { data } = await api.get(`/valuation/${id}`);
  return data;
}

export type PatchValue = number | string | boolean | null | object | unknown[];

export async function patchValuation(
  id: string,
  overrides: Record<string, PatchValue>,
): Promise<ValuationResponse> {
  const { data } = await api.patch(`/valuation/${id}`, { overrides });
  return data;
}

export async function fetchSensitivity(
  id: string,
  signal?: AbortSignal,
): Promise<import('../components/sensitivity/types').SensitivityResponse> {
  const { data } = await api.post(`/valuation/${id}/sensitivity`, null, { signal });
  return data;
}

export async function downloadTemplate(ticker: string = 'NVDA'): Promise<void> {
  const response = await api.post('/valuation/generate-template', null, {
    params: { ticker },
    responseType: 'blob',
  });
  // Extract filename from Content-Disposition so the browser saves the file
  // under the server-generated name (CIQ_Fetch_Template_<Company>_<YYMMDD>.xlsx).
  // Without this, the <a download=...> attribute below overrides the header
  // and every download collapses to the same generic name.
  let filename = 'CIQ_Fetch_Template.xlsx';
  const cd: string | undefined = response.headers?.['content-disposition'];
  if (cd) {
    // Accept both filename="X" and filename=X forms.
    const match = /filename\*?=(?:UTF-8''|")?([^";]+)"?/i.exec(cd);
    if (match && match[1]) {
      filename = decodeURIComponent(match[1].trim());
    }
  }
  const url = window.URL.createObjectURL(response.data);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}

export async function downloadFullWorkbook(sessionId: string, ticker: string = 'valuation'): Promise<void> {
  const { data } = await api.get(`/valuation/${sessionId}/export/full-workbook`, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(data);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${ticker}_valuation.xlsx`;
  a.click();
  window.URL.revokeObjectURL(url);
}

export async function fetchFromFile(
  file: File,
  region = 'US',
  riskFreeRate = 0.0425,
): Promise<ValuationResponse> {
  const form = new FormData();
  form.append('file', file);
  form.append('region', region);
  form.append('risk_free_rate', String(riskFreeRate));
  const { data } = await api.post('/valuation/fetch-from-file', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

// ---------------------------------------------------------------------------
// Public database endpoints
// ---------------------------------------------------------------------------

export interface DatabaseSearchResult {
  ticker: string;
  company_name: string;
  exchange_code: string | null;
  region: string | null;
  filing_currency: string | null;
  listing_currency: string | null;
  period_date_annual: string | null;
  match_rank: number;
}

export async function searchDatabase(query: string, limit = 20): Promise<DatabaseSearchResult[]> {
  if (!query.trim()) return [];
  const { data } = await api.get('/database/search', { params: { q: query, limit } });
  return data.results;
}

export async function companyExists(ticker: string): Promise<{ ticker: string; in_database: boolean; data_as_of: string | null }> {
  const { data } = await api.get(`/database/company-exists/${encodeURIComponent(ticker)}`);
  return data;
}

export async function valueFromDatabase(ticker: string, riskFreeRate = 0.0425): Promise<ValuationResponse> {
  const { data } = await api.post('/valuation/from-database', {
    ticker,
    risk_free_rate: riskFreeRate,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Admin endpoints
// ---------------------------------------------------------------------------

export interface AdminWhoami {
  admin: boolean;
  configured: boolean;
}

export async function adminWhoami(): Promise<AdminWhoami> {
  try {
    const { data } = await api.get('/admin/whoami');
    return data;
  } catch {
    return { admin: false, configured: false };
  }
}

export interface FileManifestEntry {
  name: string;
  size_bytes: number;
  size_human: string;
  mtime: string;
}

export interface DatasetStatus {
  markets_dataset: { folder: string; files: FileManifestEntry[] };
  knowledge_base_damodaran: { folder: string; files: FileManifestEntry[] };
  industry_lookup: { folder: string; files: FileManifestEntry[] };
  database: {
    path: string;
    exists: boolean;
    is_seed: boolean;               // true = we're serving the shipped seed
    size_bytes?: number;
    size_human?: string;
    company_count: number;
    error?: string;
    // Seed (shipped, committed)
    seed_path?: string;
    seed_exists?: boolean;
    seed_size_human?: string;
    seed_mtime?: string;
    // Admin DB (private, gitignored)
    admin_db_path?: string;
    admin_db_exists?: boolean;
    admin_db_size_human?: string;
    admin_db_mtime?: string;
  };
  last_ingest: null | {
    timestamp_utc: string;
    n_companies: number;
    n_rejected: number;
    n_files: number;
    unmapped_columns: string[];
    unmapped_exchanges: string[];
    warnings: string[];
    duration_ms: number;
  };
}

export async function adminDatasetStatus(): Promise<DatasetStatus> {
  const { data } = await api.get('/admin/dataset-status');
  return data;
}

export async function adminUploadFile(
  kind: 'markets-dataset' | 'damodaran' | 'industry-lookup',
  file: File,
): Promise<{ saved: string; filename: string; size_bytes: number; next_step: string }> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post(`/admin/upload/${kind}`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export interface RefreshReport {
  status: string;
  n_companies?: number;
  n_rejected?: number;
  unmapped_columns?: string[];
  unmapped_exchanges?: string[];
  warnings?: string[];
  duration_seconds?: number;
  file_manifest?: unknown[];
  [key: string]: unknown;
}

export async function adminRefreshDatabase(): Promise<RefreshReport> {
  const { data } = await api.post('/admin/refresh-database');
  return data;
}

export async function adminClearSection(
  section: 'markets-dataset' | 'damodaran' | 'industry-lookup',
): Promise<{ status: string; removed: string[]; count: number; next_step: string }> {
  const { data } = await api.post(`/admin/clear/${section}`);
  return data;
}

export async function adminDeleteFile(
  section: 'markets-dataset' | 'damodaran' | 'industry-lookup',
  filename: string,
): Promise<{ status: string; removed: string; next_step: string }> {
  const { data } = await api.delete(`/admin/file/${section}/${encodeURIComponent(filename)}`);
  return data;
}

export async function adminRefreshKnowledgeBase(): Promise<RefreshReport> {
  const { data } = await api.post('/admin/refresh-knowledge-base');
  return data;
}

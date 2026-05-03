import axios from 'axios';
import type { CompanyValuationInput, ValuationResponse } from '../types/valuation';

const api = axios.create({ baseURL: '/api' });

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
  const { data } = await api.post('/valuation/generate-template', null, {
    params: { ticker },
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(data);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'CIQ_Fetch_Template.xlsx';
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

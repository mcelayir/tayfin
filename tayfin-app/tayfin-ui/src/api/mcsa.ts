/**
 * BFF API client — typed fetch wrappers for MCSA endpoints.
 *
 * All requests go to the BFF (`/api/*`) — the UI MUST NOT call
 * upstream context APIs directly (ARCHITECTURE_RULES §2.2).
 */

import type { McsaDashboardResponse, McsaResult } from '../types/mcsa';

const BASE = '/api';

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE}${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '') url.searchParams.set(k, v);
    });
  }

  const resp = await fetch(url.toString());

  if (!resp.ok) {
    throw new ApiError(resp.status, await resp.text());
  }

  return resp.json() as Promise<T>;
}

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(`API ${status}: ${body}`);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

/** GET /api/mcsa/dashboard — all tickers, latest per ticker */
export async function fetchMcsaDashboard(
  params?: Record<string, string>,
): Promise<McsaDashboardResponse> {
  return get<McsaDashboardResponse>('/mcsa/dashboard', params);
}

/** GET /api/mcsa/:ticker — single ticker result */
export async function fetchMcsaTicker(ticker: string): Promise<McsaResult> {
  return get<McsaResult>(`/mcsa/${ticker}`);
}

/** GET /api/mcsa/range — date range for a ticker */
export async function fetchMcsaRange(
  ticker: string,
  from: string,
  to: string,
): Promise<McsaDashboardResponse> {
  return get<McsaDashboardResponse>('/mcsa/range', { ticker, from, to });
}

/**
 * Shared test fixtures for MCSA UI components.
 */

import type { McsaResult } from '../types/mcsa';

/** Minimal MCSA result factory with sensible defaults. */
export function makeMcsaResult(overrides: Partial<McsaResult> = {}): McsaResult {
  return {
    ticker: 'AAPL',
    instrument_id: 'inst-1',
    as_of_date: '2026-03-07',
    mcsa_score: 55.0,
    mcsa_band: 'neutral',
    trend_score: 20.0,
    vcp_component: 15.0,
    volume_score: 10.0,
    fundamental_score: 10.0,
    evidence: {
      trend: { score: 20 },
      vcp: { score: 15 },
      volume: { score: 10 },
      fundamentals: { score: 10 },
    },
    missing_fields: [],
    ...overrides,
  };
}

/** Sample dataset with mixed bands for testing. */
export const SAMPLE_ITEMS: McsaResult[] = [
  makeMcsaResult({ ticker: 'BKR',  mcsa_score: 69.85, mcsa_band: 'neutral',   trend_score: 30, vcp_component: 24.85, volume_score: 15, fundamental_score: 0, missing_fields: ['revenue_growth_yoy', 'earnings_growth_yoy'] }),
  makeMcsaResult({ ticker: 'WMT',  mcsa_score: 65.90, mcsa_band: 'neutral',   trend_score: 28, vcp_component: 22.9,  volume_score: 15, fundamental_score: 0 }),
  makeMcsaResult({ ticker: 'PEP',  mcsa_score: 63.45, mcsa_band: 'neutral',   trend_score: 25, vcp_component: 20.45, volume_score: 13, fundamental_score: 5 }),
  makeMcsaResult({ ticker: 'MSFT', mcsa_score: 42.10, mcsa_band: 'weak',      trend_score: 18, vcp_component: 12.1,  volume_score: 7,  fundamental_score: 5 }),
  makeMcsaResult({ ticker: 'GOOG', mcsa_score: 35.50, mcsa_band: 'weak',      trend_score: 15, vcp_component: 10.5,  volume_score: 5,  fundamental_score: 5 }),
  makeMcsaResult({ ticker: 'AMZN', mcsa_score: 88.00, mcsa_band: 'strong',    trend_score: 30, vcp_component: 33.0,  volume_score: 15, fundamental_score: 10 }),
  makeMcsaResult({ ticker: 'META', mcsa_score: 72.30, mcsa_band: 'watchlist',  trend_score: 28, vcp_component: 25.3,  volume_score: 12, fundamental_score: 7 }),
];

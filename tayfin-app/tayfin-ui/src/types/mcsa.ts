/**
 * TypeScript interfaces for MCSA API responses.
 * Must match the Screener API / BFF response contract.
 * See: ADR-01 (MCSA Algorithm), docs/ui/DESIGN_SPEC §9.
 */

/** Evidence sub-types per component */

export interface TrendEvidence {
  score: number;
  price_above_sma50?: boolean;
  sma50_above_sma150?: boolean;
  sma150_above_sma200?: boolean;
  sma200_rising?: boolean;
  near_52w_high?: boolean;
  near_52w_high_pct?: number;
  above_52w_low_pct?: number;
}

export interface VcpEvidence {
  score: number;
  pattern_detected?: boolean;
  vcp_score?: number;
  contraction_count?: number;
  depth_pct?: number;
}

export interface VolumeEvidence {
  score: number;
  pullback_below_avg?: boolean;
  volume_dry_up?: boolean;
  no_abnormal_selling?: boolean;
}

export interface FundamentalsEvidence {
  score: number;
  revenue_growth_yoy?: number | null;
  earnings_growth_yoy?: number | null;
  roe?: number | null;
  net_margin?: number | null;
  debt_equity?: number | null;
}

export interface McsaEvidence {
  trend: TrendEvidence;
  vcp: VcpEvidence;
  volume: VolumeEvidence;
  fundamentals: FundamentalsEvidence;
  total_score?: number;
  band?: string;
}

/** Main MCSA result for one ticker on one date */
export interface McsaResult {
  ticker: string;
  instrument_id: string | null;
  as_of_date: string;
  mcsa_score: number;
  mcsa_band: McsaBand;
  trend_score: number;
  vcp_component: number;
  volume_score: number;
  fundamental_score: number;
  evidence: McsaEvidence;
  missing_fields: string[];
}

export type McsaBand = 'strong' | 'watchlist' | 'neutral' | 'weak';

/** API list response wrapper */
export interface McsaDashboardResponse {
  items: McsaResult[];
}

/** Band metadata for display */
export const BAND_CONFIG: Record<McsaBand, { label: string; min: number }> = {
  strong:    { label: 'Strong',    min: 85 },
  watchlist: { label: 'Watchlist', min: 70 },
  neutral:   { label: 'Neutral',   min: 50 },
  weak:      { label: 'Weak',      min: 0  },
};

/** Component weight caps (per ADR-01) */
export const COMPONENT_WEIGHTS = {
  trend: 30,
  vcp: 35,
  volume: 15,
  fundamentals: 20,
} as const;

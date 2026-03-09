/**
 * useFilters — client-side filter state with URL query-param sync.
 *
 * Manages band filter, min-score slider, and ticker search.
 * All filtering is done client-side on the ≤101-item dataset.
 *
 * See: DESIGN_SPEC §3.2, §8 (Filtering)
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router';
import type { McsaResult, McsaBand } from '../types/mcsa';

const ALL_BANDS: McsaBand[] = ['strong', 'watchlist', 'neutral', 'weak'];

export interface FilterState {
  bands: Set<McsaBand>;
  minScore: number;
  tickerSearch: string;
}

export interface UseFiltersReturn {
  filters: FilterState;
  filtered: McsaResult[];
  setBands: (bands: Set<McsaBand>) => void;
  toggleBand: (band: McsaBand) => void;
  setMinScore: (score: number) => void;
  setTickerSearch: (query: string) => void;
  resetFilters: () => void;
  hasActiveFilters: boolean;
}

/** Parse band query param → Set<McsaBand> */
function parseBands(raw: string | null): Set<McsaBand> {
  if (!raw) return new Set(ALL_BANDS);
  const parsed = raw
    .split(',')
    .filter((b): b is McsaBand => ALL_BANDS.includes(b as McsaBand));
  return parsed.length > 0 ? new Set(parsed) : new Set(ALL_BANDS);
}

export function useFilters(items: McsaResult[]): UseFiltersReturn {
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize from URL
  const [bands, setBandsState] = useState<Set<McsaBand>>(
    () => parseBands(searchParams.get('band')),
  );
  const [minScore, setMinScoreState] = useState<number>(
    () => {
      const raw = searchParams.get('min_score');
      const n = raw ? parseInt(raw, 10) : 0;
      return Number.isNaN(n) ? 0 : Math.max(0, Math.min(100, n));
    },
  );
  const [tickerSearch, setTickerSearchState] = useState<string>(
    () => searchParams.get('search') ?? '',
  );

  // Debounce ref for ticker search URL sync
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync state → URL params
  useEffect(() => {
    const params = new URLSearchParams();

    // Only write band param if not "all"
    if (bands.size < ALL_BANDS.length && bands.size > 0) {
      params.set('band', [...bands].join(','));
    }

    if (minScore > 0) {
      params.set('min_score', String(minScore));
    }

    if (tickerSearch.trim()) {
      params.set('search', tickerSearch.trim());
    }

    setSearchParams(params, { replace: true });
  }, [bands, minScore, tickerSearch, setSearchParams]);

  // Setters
  const setBands = useCallback((next: Set<McsaBand>) => {
    setBandsState(next);
  }, []);

  const toggleBand = useCallback((band: McsaBand) => {
    setBandsState((prev) => {
      const next = new Set(prev);
      if (next.has(band)) {
        next.delete(band);
      } else {
        next.add(band);
      }
      // If nothing selected, revert to all
      return next.size === 0 ? new Set(ALL_BANDS) : next;
    });
  }, []);

  const setMinScore = useCallback((score: number) => {
    setMinScoreState(Math.max(0, Math.min(100, score)));
  }, []);

  const setTickerSearch = useCallback((query: string) => {
    // Debounce the state update for 300ms
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setTickerSearchState(query);
    }, 300);
  }, []);

  const resetFilters = useCallback(() => {
    setBandsState(new Set(ALL_BANDS));
    setMinScoreState(0);
    setTickerSearchState('');
  }, []);

  // Compute filtered items
  const filtered = useMemo(() => {
    const searchLower = tickerSearch.trim().toLowerCase();
    return items.filter((item) => {
      if (!bands.has(item.mcsa_band)) return false;
      if (item.mcsa_score < minScore) return false;
      if (searchLower && !item.ticker.toLowerCase().includes(searchLower)) return false;
      return true;
    });
  }, [items, bands, minScore, tickerSearch]);

  const hasActiveFilters =
    bands.size < ALL_BANDS.length || minScore > 0 || tickerSearch.trim() !== '';

  return {
    filters: { bands, minScore, tickerSearch },
    filtered,
    setBands,
    toggleBand,
    setMinScore,
    setTickerSearch,
    resetFilters,
    hasActiveFilters,
  };
}

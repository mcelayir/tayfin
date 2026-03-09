/**
 * FilterBar — client-side filter controls for MCSA dashboard.
 *
 * Band multi-select, min score slider, ticker search.
 * All filtering is applied client-side on the loaded dataset (≤101 items).
 *
 * See: DESIGN_SPEC §3.2 (Filter Bar), §8 (Interaction Model)
 */

import { useState, useRef, useEffect } from 'react';
import type { McsaBand } from '../../types/mcsa';
import { BAND_CONFIG } from '../../types/mcsa';
import styles from './FilterBar.module.css';

interface FilterBarProps {
  bands: Set<McsaBand>;
  minScore: number;
  tickerSearch: string;
  totalCount: number;
  filteredCount: number;
  hasActiveFilters: boolean;
  onToggleBand: (band: McsaBand) => void;
  onMinScoreChange: (score: number) => void;
  onTickerSearchChange: (query: string) => void;
  onReset: () => void;
}

const BAND_KEYS: McsaBand[] = ['strong', 'watchlist', 'neutral', 'weak'];

export function FilterBar({
  bands,
  minScore,
  tickerSearch,
  totalCount,
  filteredCount,
  hasActiveFilters,
  onToggleBand,
  onMinScoreChange,
  onTickerSearchChange,
  onReset,
}: FilterBarProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [localSearch, setLocalSearch] = useState(tickerSearch);

  // Sync localSearch when parent resets tickerSearch
  useEffect(() => {
    setLocalSearch(tickerSearch);
  }, [tickerSearch]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [dropdownOpen]);

  // Sync local search → parent with debounce (parent handles debounce)
  function handleSearchInput(value: string) {
    setLocalSearch(value);
    onTickerSearchChange(value);
  }

  // Band dropdown label
  const bandLabel =
    bands.size === BAND_KEYS.length
      ? 'All Bands'
      : bands.size === 0
        ? 'All Bands'
        : [...bands].map((b) => BAND_CONFIG[b].label).join(', ');

  return (
    <div className={styles.filterBar} role="toolbar" aria-label="Filter controls">
      {/* ── Band multi-select dropdown ── */}
      <div className={styles.filterBar__group} ref={dropdownRef}>
        <label className={styles.filterBar__label} id="band-filter-label">Band</label>
        <button
          type="button"
          className={styles.filterBar__dropdown}
          aria-haspopup="listbox"
          aria-expanded={dropdownOpen}
          aria-labelledby="band-filter-label"
          onClick={() => setDropdownOpen((prev) => !prev)}
        >
          <span className={styles.filterBar__dropdownText}>{bandLabel}</span>
          <span className={styles.filterBar__chevron} aria-hidden="true">
            {dropdownOpen ? '▲' : '▼'}
          </span>
        </button>

        {dropdownOpen && (
          <div className={styles.filterBar__menu} role="listbox" aria-multiselectable="true">
            {BAND_KEYS.map((band) => (
              <label key={band} className={styles.filterBar__option}>
                <input
                  type="checkbox"
                  checked={bands.has(band)}
                  onChange={() => onToggleBand(band)}
                />
                <span
                  className={styles.filterBar__bandDot}
                  style={{ backgroundColor: `var(--band-${band}-accent)` }}
                />
                {BAND_CONFIG[band].label}
              </label>
            ))}
          </div>
        )}
      </div>

      {/* ── Min score slider ── */}
      <div className={styles.filterBar__group}>
        <label className={styles.filterBar__label} htmlFor="min-score-slider">
          Min Score: <span className={styles.filterBar__value}>{minScore}</span>
        </label>
        <input
          id="min-score-slider"
          type="range"
          min={0}
          max={100}
          step={1}
          value={minScore}
          onChange={(e) => onMinScoreChange(Number(e.target.value))}
          className={styles.filterBar__slider}
        />
      </div>

      {/* ── Ticker search ── */}
      <div className={styles.filterBar__group}>
        <label className={styles.filterBar__label} htmlFor="ticker-search">Search</label>
        <input
          id="ticker-search"
          type="text"
          placeholder="Search ticker…"
          value={localSearch}
          onChange={(e) => handleSearchInput(e.target.value)}
          className={styles.filterBar__input}
          autoComplete="off"
          spellCheck={false}
        />
      </div>

      {/* ── Result count + Reset ── */}
      <div className={styles.filterBar__meta}>
        <span className={styles.filterBar__count}>
          {filteredCount} / {totalCount}
        </span>
        {hasActiveFilters && (
          <button
            type="button"
            className={styles.filterBar__reset}
            onClick={onReset}
          >
            Reset
          </button>
        )}
      </div>
    </div>
  );
}

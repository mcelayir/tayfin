import { useState } from 'react';
import { useMcsaData } from '../hooks/useMcsaData';
import { useFilters } from '../hooks/useFilters';
import { ScoreTable } from '../components/ScoreTable';
import { FilterBar } from '../components/FilterBar';
import { SummaryBar } from '../components/SummaryBar';
import styles from './Dashboard.module.css';

export function Dashboard() {
  const { items, state, error, reload } = useMcsaData();
  const {
    filters,
    filtered,
    toggleBand,
    setMinScore,
    setTickerSearch,
    resetFilters,
    hasActiveFilters,
  } = useFilters(items);
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);

  const latestDate = items.length > 0 ? items[0].as_of_date : '—';

  const handleRowClick = (ticker: string) => {
    setExpandedTicker((prev) => (prev === ticker ? null : ticker));
  };

  return (
    <div className={styles.dashboard}>
      <header className={styles.dashboard__header}>
        <h1 className={styles.dashboard__title}>MCSA Score Dashboard</h1>
        <p className={styles.dashboard__subtitle}>
          NASDAQ-100 • Last scored: {latestDate} • {items.length} tickers
        </p>
      </header>

      {state === 'error' && (
        <div className={styles.dashboard__error} role="alert">
          <span>{error}</span>
          <button type="button" onClick={reload}>Retry</button>
        </div>
      )}

      {state === 'loading' && (
        <div className={styles.dashboard__loading}>Loading MCSA data…</div>
      )}

      {state === 'success' && (
        <>
          <SummaryBar items={items} />

          <FilterBar
            bands={filters.bands}
            minScore={filters.minScore}
            tickerSearch={filters.tickerSearch}
            totalCount={items.length}
            filteredCount={filtered.length}
            hasActiveFilters={hasActiveFilters}
            onToggleBand={toggleBand}
            onMinScoreChange={setMinScore}
            onTickerSearchChange={setTickerSearch}
            onReset={resetFilters}
          />

          <ScoreTable
            items={filtered}
            expandedTicker={expandedTicker}
            onRowClick={handleRowClick}
          />
        </>
      )}
    </div>
  );
}

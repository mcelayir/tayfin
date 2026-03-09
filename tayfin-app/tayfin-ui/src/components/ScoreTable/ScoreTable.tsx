/**
 * ScoreTable — primary MCSA data table.
 *
 * Renders all NDX tickers with sortable columns, band badges,
 * and mini progress bars for component scores.
 *
 * See: DESIGN_SPEC §3.3 (Score Table)
 */

import { useState, useMemo, Fragment } from 'react';
import type { McsaResult, McsaBand } from '../../types/mcsa';
import { COMPONENT_WEIGHTS } from '../../types/mcsa';
import { BandBadge } from '../common/BandBadge';
import { ProgressBar } from '../common/ProgressBar';
import { DetailPanel } from '../DetailPanel';
import styles from './ScoreTable.module.css';

// ── Sort types ─────────────────────────────────────────────

type SortKey =
  | 'ticker'
  | 'mcsa_score'
  | 'mcsa_band'
  | 'trend_score'
  | 'vcp_component'
  | 'volume_score'
  | 'fundamental_score';

type SortDir = 'asc' | 'desc';

interface Column {
  key: SortKey;
  label: string;
  align: 'left' | 'center' | 'right';
  sortable: boolean;
}

const COLUMNS: Column[] = [
  { key: 'ticker',            label: 'Ticker',       align: 'left',   sortable: true },
  { key: 'mcsa_score',        label: 'Score',        align: 'right',  sortable: true },
  { key: 'mcsa_band',         label: 'Band',         align: 'center', sortable: true },
  { key: 'trend_score',       label: 'Trend',        align: 'center', sortable: true },
  { key: 'vcp_component',     label: 'VCP',          align: 'center', sortable: true },
  { key: 'volume_score',      label: 'Volume',       align: 'center', sortable: true },
  { key: 'fundamental_score', label: 'Fundamentals', align: 'center', sortable: true },
];

// Band sort order: strong > watchlist > neutral > weak
const BAND_ORDER: Record<McsaBand, number> = {
  strong: 4,
  watchlist: 3,
  neutral: 2,
  weak: 1,
};

const COMPONENT_COLORS: Record<string, string> = {
  trend_score: 'var(--component-trend)',
  vcp_component: 'var(--component-vcp)',
  volume_score: 'var(--component-volume)',
  fundamental_score: 'var(--component-fundamentals)',
};

const COMPONENT_MAX: Record<string, number> = {
  trend_score: COMPONENT_WEIGHTS.trend,
  vcp_component: COMPONENT_WEIGHTS.vcp,
  volume_score: COMPONENT_WEIGHTS.volume,
  fundamental_score: COMPONENT_WEIGHTS.fundamentals,
};

// ── Props ──────────────────────────────────────────────────

interface ScoreTableProps {
  items: McsaResult[];
  expandedTicker: string | null;
  onRowClick: (ticker: string) => void;
}

// ── Component ──────────────────────────────────────────────

export function ScoreTable({ items, expandedTicker, onRowClick }: ScoreTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('mcsa_score');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const sortedItems = useMemo(() => {
    const sorted = [...items].sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'mcsa_band') {
        cmp = BAND_ORDER[a.mcsa_band] - BAND_ORDER[b.mcsa_band];
      } else if (sortKey === 'ticker') {
        cmp = a.ticker.localeCompare(b.ticker);
      } else {
        cmp = (a[sortKey] as number) - (b[sortKey] as number);
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return sorted;
  }, [items, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, ticker: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onRowClick(ticker);
    }
    if (e.key === 'Escape' && expandedTicker) {
      onRowClick(expandedTicker); // collapse
    }
  };

  if (items.length === 0) {
    return (
      <div className={styles.emptyState}>
        <p>No MCSA results match your filters.</p>
      </div>
    );
  }

  return (
    <table className={styles.scoreTable} role="grid">
      <thead>
        <tr>
          <th className={styles.alignRight} scope="col" aria-label="Rank">#</th>
          {COLUMNS.map((col) => (
            <th
              key={col.key}
              scope="col"
              className={styles[`align${capitalize(col.align)}`]}
              data-sortable={col.sortable}
              onClick={() => col.sortable && handleSort(col.key)}
              aria-sort={
                sortKey === col.key
                  ? sortDir === 'asc' ? 'ascending' : 'descending'
                  : undefined
              }
            >
              <span className={styles.thContent}>
                {col.label}
                {sortKey === col.key && (
                  <span className={`${styles.sortIcon} ${styles['sortIcon--active']}`}>
                    {sortDir === 'asc' ? '▲' : '▼'}
                  </span>
                )}
              </span>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sortedItems.map((item, idx) => {
          const isExpanded = expandedTicker === item.ticker;
          const hasMissing = item.missing_fields.length > 0;

          return (
            <Fragment key={item.ticker}>
            <tr
              className={`${isExpanded ? `${styles['row--expanded']} ${styles[`row--${item.mcsa_band}`]}` : ''}`}
              onClick={() => onRowClick(item.ticker)}
              onKeyDown={(e) => handleKeyDown(e, item.ticker)}
              tabIndex={0}
              role="row"
              aria-expanded={isExpanded}
            >
              {/* Rank */}
              <td className={`${styles.cellRank} ${styles.alignRight}`}>
                {idx + 1}
              </td>

              {/* Ticker */}
              <td className={styles.cellTicker}>
                {item.ticker}
                {hasMissing && (
                  <span
                    className={styles.cellMissing}
                    title={`Missing: ${item.missing_fields.join(', ')}`}
                  >
                    {' ⚠'}
                  </span>
                )}
              </td>

              {/* Score */}
              <td className={`${styles.cellScore} ${styles.alignRight} ${styles[`score--${item.mcsa_band}`]}`}>
                {item.mcsa_score.toFixed(1)}
              </td>

              {/* Band */}
              <td className={`${styles.cellBand} ${styles.alignCenter}`}>
                <BandBadge band={item.mcsa_band} />
              </td>

              {/* Component columns */}
              {(['trend_score', 'vcp_component', 'volume_score', 'fundamental_score'] as const).map(
                (key) => (
                  <td key={key} className={`${styles.cellComponent} ${styles.alignCenter}`}>
                    <div className={styles.componentCell}>
                      <ProgressBar
                        value={item[key]}
                        max={COMPONENT_MAX[key]}
                        color={COMPONENT_COLORS[key]}
                        title={`${key}: ${item[key].toFixed(1)} / ${COMPONENT_MAX[key]}`}
                      />
                      <span className={styles.componentValue}>
                        {item[key].toFixed(1)}
                      </span>
                    </div>
                  </td>
                ),
              )}
            </tr>
            {isExpanded && (
              <tr className={styles['row--expanded']}>
                <td colSpan={8} style={{ padding: 0 }}>
                  <DetailPanel item={item} />
                </td>
              </tr>
            )}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

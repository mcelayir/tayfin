import { useMcsaData } from '../hooks/useMcsaData';
import styles from './Dashboard.module.css';

export function Dashboard() {
  const { items, state, error, reload } = useMcsaData();

  const latestDate = items.length > 0 ? items[0].as_of_date : '—';

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
        <p style={{ color: 'var(--text-secondary)' }}>
          {items.length} results loaded. Score Table coming in Task 6.
        </p>
      )}
    </div>
  );
}

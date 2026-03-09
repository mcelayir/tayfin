/**
 * BandDistribution — horizontal bar chart showing count per band.
 *
 * See: DESIGN_SPEC §3.1 (Band Distribution Card)
 */

import type { McsaResult, McsaBand } from '../../types/mcsa';
import { BAND_CONFIG } from '../../types/mcsa';
import styles from './SummaryBar.module.css';

interface BandDistributionProps {
  items: McsaResult[];
}

const BAND_KEYS: McsaBand[] = ['strong', 'watchlist', 'neutral', 'weak'];

export function BandDistribution({ items }: BandDistributionProps) {
  const counts: Record<McsaBand, number> = {
    strong: 0,
    watchlist: 0,
    neutral: 0,
    weak: 0,
  };

  for (const item of items) {
    counts[item.mcsa_band]++;
  }

  const maxCount = Math.max(...Object.values(counts), 1);

  return (
    <div className={styles.card}>
      <h3 className={styles.card__title}>Band Distribution</h3>
      <div className={styles.card__body} role="img" aria-label="Band distribution chart">
        {BAND_KEYS.map((band) => (
          <div key={band} className={styles.barRow}>
            <span className={styles.barRow__label}>
              <span
                className={styles.barRow__dot}
                style={{ backgroundColor: `var(--band-${band}-accent)` }}
              />
              {BAND_CONFIG[band].label}
            </span>
            <div className={styles.barRow__track}>
              <div
                className={styles.barRow__fill}
                style={{
                  width: `${(counts[band] / maxCount) * 100}%`,
                  backgroundColor: `var(--band-${band}-accent)`,
                }}
              />
            </div>
            <span className={styles.barRow__value}>{counts[band]}</span>
          </div>
        ))}
      </div>
      <p className={styles.card__footer}>Total: {items.length} tickers</p>
    </div>
  );
}

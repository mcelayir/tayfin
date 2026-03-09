/**
 * ScoreHistogram — horizontal bucket bar chart for score distribution.
 *
 * 10 buckets: 0-10, 10-20, …, 90-100.
 *
 * See: DESIGN_SPEC §3.1 (Score Histogram Card)
 */

import type { McsaResult } from '../../types/mcsa';
import styles from './SummaryBar.module.css';

interface ScoreHistogramProps {
  items: McsaResult[];
}

const BUCKETS = [
  { label: '90-100', min: 90, max: 100 },
  { label: '80-90',  min: 80, max: 90 },
  { label: '70-80',  min: 70, max: 80 },
  { label: '60-70',  min: 60, max: 70 },
  { label: '50-60',  min: 50, max: 60 },
  { label: '40-50',  min: 40, max: 50 },
  { label: '30-40',  min: 30, max: 40 },
  { label: '20-30',  min: 20, max: 30 },
  { label: '10-20',  min: 10, max: 20 },
  { label: '0-10',   min: 0,  max: 10 },
];

export function ScoreHistogram({ items }: ScoreHistogramProps) {
  const counts = BUCKETS.map((bucket) => {
    const count = items.filter(
      (item) => item.mcsa_score >= bucket.min && item.mcsa_score < bucket.max,
    ).length;
    return { ...bucket, count };
  });

  // Special case: include score === 100 in the 90-100 bucket
  const perfect = items.filter((item) => item.mcsa_score === 100).length;
  if (perfect > 0) {
    counts[0].count += perfect;
  }

  const maxCount = Math.max(...counts.map((c) => c.count), 1);

  return (
    <div className={styles.card}>
      <h3 className={styles.card__title}>Score Distribution</h3>
      <div className={styles.card__body}>
        {counts.map((bucket) => (
          <div key={bucket.label} className={styles.barRow}>
            <span className={styles.barRow__label}>{bucket.label}</span>
            <div className={styles.barRow__track}>
              <div
                className={styles.barRow__fill}
                style={{
                  width: `${(bucket.count / maxCount) * 100}%`,
                  backgroundColor: 'var(--info)',
                }}
              />
            </div>
            <span className={styles.barRow__value}>
              {bucket.count > 0 ? bucket.count : ''}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

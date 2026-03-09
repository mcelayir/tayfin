/**
 * SummaryBar — at-a-glance distribution overview above the score table.
 *
 * 4 cards: Band Distribution, Score Histogram, Component Averages, Total Count.
 * Responsive: 4-col desktop, 2-col tablet, stacked mobile.
 *
 * See: DESIGN_SPEC §3.1 (Summary Bar)
 */

import type { McsaResult } from '../../types/mcsa';
import { BandDistribution } from './BandDistribution';
import { ScoreHistogram } from './ScoreHistogram';
import { ComponentAverages } from './ComponentAverages';
import styles from './SummaryBar.module.css';

interface SummaryBarProps {
  items: McsaResult[];
}

export function SummaryBar({ items }: SummaryBarProps) {
  return (
    <div className={styles.summaryBar}>
      <BandDistribution items={items} />
      <ScoreHistogram items={items} />
      <ComponentAverages items={items} />

      {/* Total count card */}
      <div className={styles.card}>
        <h3 className={styles.card__title}>Total</h3>
        <div className={styles.totalCard}>
          <span className={styles.totalCard__number}>{items.length}</span>
          <span className={styles.totalCard__label}>tickers scored</span>
        </div>
      </div>
    </div>
  );
}

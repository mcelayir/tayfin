/**
 * DetailPanel — inline expansion below a table row showing
 * component donut chart + evidence breakdown cards.
 *
 * See: DESIGN_SPEC §3.4 (Score Detail Panel)
 */

import type { McsaResult } from '../../types/mcsa';
import { BAND_CONFIG } from '../../types/mcsa';
import { DonutChart, getSegments } from './DonutChart';
import { EvidenceCards } from './EvidenceCards';
import styles from './DetailPanel.module.css';

interface DetailPanelProps {
  item: McsaResult;
}

const SEGMENT_COLORS: Record<string, string> = {
  Trend: 'var(--component-trend)',
  VCP: 'var(--component-vcp)',
  Volume: 'var(--component-volume)',
  Fundamentals: 'var(--component-fundamentals)',
};

export function DetailPanel({ item }: DetailPanelProps) {
  const segments = getSegments(item);
  const bandLabel = BAND_CONFIG[item.mcsa_band].label;

  return (
    <div className={styles.detailPanel} role="region" aria-label={`Detail for ${item.ticker}`}>
      {/* Header */}
      <div className={styles.detailHeader}>
        <span className={styles.detailTicker}>{item.ticker}</span>
        <span className={styles.detailScore}>
          {item.mcsa_score.toFixed(1)} / 100 ({bandLabel})
        </span>
        <span className={styles.detailDate}>
          as of {item.as_of_date}
        </span>
      </div>

      {/* Body: donut + evidence */}
      <div className={styles.detailBody}>
        {/* Left column — donut chart */}
        <div className={styles.donutContainer}>
          <DonutChart item={item} />
          <div className={styles.donutLegend}>
            {segments.map((seg) => (
              <div key={seg.label} className={styles.legendItem}>
                <span
                  className={styles.legendDot}
                  style={{ backgroundColor: SEGMENT_COLORS[seg.label] }}
                />
                <span>{seg.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right column — evidence cards */}
        <EvidenceCards item={item} />
      </div>
    </div>
  );
}

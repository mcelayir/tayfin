/**
 * ComponentAverages — average scores per MCSA component.
 *
 * Shows Trend/30, VCP/35, Volume/15, Fundamentals/20 as labeled bars.
 *
 * See: DESIGN_SPEC §3.1 (Component Averages Card)
 */

import type { McsaResult } from '../../types/mcsa';
import { COMPONENT_WEIGHTS } from '../../types/mcsa';
import styles from './SummaryBar.module.css';

interface ComponentAveragesProps {
  items: McsaResult[];
}

interface ComponentDef {
  key: keyof typeof COMPONENT_WEIGHTS;
  label: string;
  accessor: (item: McsaResult) => number;
  max: number;
  color: string;
}

const COMPONENTS: ComponentDef[] = [
  {
    key: 'trend',
    label: 'Trend',
    accessor: (item) => item.trend_score,
    max: COMPONENT_WEIGHTS.trend,
    color: 'var(--component-trend)',
  },
  {
    key: 'vcp',
    label: 'VCP',
    accessor: (item) => item.vcp_component,
    max: COMPONENT_WEIGHTS.vcp,
    color: 'var(--component-vcp)',
  },
  {
    key: 'volume',
    label: 'Volume',
    accessor: (item) => item.volume_score,
    max: COMPONENT_WEIGHTS.volume,
    color: 'var(--component-volume)',
  },
  {
    key: 'fundamentals',
    label: 'Fund',
    accessor: (item) => item.fundamental_score,
    max: COMPONENT_WEIGHTS.fundamentals,
    color: 'var(--component-fundamentals)',
  },
];

export function ComponentAverages({ items }: ComponentAveragesProps) {
  const n = items.length || 1;

  return (
    <div className={styles.card}>
      <h3 className={styles.card__title}>Avg Component Scores</h3>
      <div className={styles.card__body} role="img" aria-label="Average component scores chart">
        {COMPONENTS.map((comp) => {
          const avg =
            items.reduce((sum, item) => sum + comp.accessor(item), 0) / n;

          return (
            <div key={comp.key} className={styles.barRow}>
              <span className={styles.barRow__label}>{comp.label}</span>
              <div className={styles.barRow__track}>
                <div
                  className={styles.barRow__fill}
                  style={{
                    width: `${(avg / comp.max) * 100}%`,
                    backgroundColor: comp.color,
                  }}
                />
              </div>
              <span className={styles.barRow__value}>
                {avg.toFixed(1)} / {comp.max}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

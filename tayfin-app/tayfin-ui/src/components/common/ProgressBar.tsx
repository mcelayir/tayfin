import styles from './ProgressBar.module.css';

interface ProgressBarProps {
  value: number;
  max: number;
  color: string;
  title?: string;
}

/** Mini horizontal bar for component scores (DESIGN_SPEC §3.3, THEME §9). */
export function ProgressBar({ value, max, color, title }: ProgressBarProps) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;

  return (
    <div
      className={styles.progressBar}
      role="meter"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-label={title ?? `${value.toFixed(1)} / ${max}`}
      title={title ?? `${value.toFixed(1)} / ${max}`}
    >
      <div
        className={styles.progressBar__fill}
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

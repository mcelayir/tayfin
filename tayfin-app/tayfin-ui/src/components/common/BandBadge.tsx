import type { McsaBand } from '../../types/mcsa';
import { BAND_CONFIG } from '../../types/mcsa';
import styles from './BandBadge.module.css';

const BAND_STYLES: Record<McsaBand, { bg: string; text: string }> = {
  strong:    { bg: 'var(--band-strong-bg)',    text: 'var(--band-strong-text)' },
  watchlist: { bg: 'var(--band-watchlist-bg)',  text: 'var(--band-watchlist-text)' },
  neutral:   { bg: 'var(--band-neutral-bg)',    text: 'var(--band-neutral-text)' },
  weak:      { bg: 'var(--band-weak-bg)',       text: 'var(--band-weak-text)' },
};

interface BandBadgeProps {
  band: McsaBand;
}

/** Colored pill badge for MCSA score bands (DESIGN_SPEC §3.3). */
export function BandBadge({ band }: BandBadgeProps) {
  const { bg, text } = BAND_STYLES[band];
  return (
    <span
      className={styles.badge}
      style={{ backgroundColor: bg, color: text }}
    >
      {BAND_CONFIG[band].label}
    </span>
  );
}

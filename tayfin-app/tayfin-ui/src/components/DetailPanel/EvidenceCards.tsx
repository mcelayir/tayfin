/**
 * EvidenceCards — 4 stacked cards showing per-component evidence.
 *
 * Each card shows: component icon, score, and boolean/numeric evidence fields.
 * Missing data shown with ⚠ indicators.
 * See: DESIGN_SPEC §3.4 (Evidence Breakdown)
 */

import type { McsaResult, TrendEvidence, VcpEvidence, VolumeEvidence, FundamentalsEvidence } from '../../types/mcsa';
import { COMPONENT_WEIGHTS } from '../../types/mcsa';
import styles from './DetailPanel.module.css';

interface EvidenceCardsProps {
  item: McsaResult;
}

export function EvidenceCards({ item }: EvidenceCardsProps) {
  const { evidence, missing_fields } = item;

  return (
    <div className={styles.evidenceCards}>
      <TrendCard evidence={evidence.trend} max={COMPONENT_WEIGHTS.trend} />
      <VcpCard evidence={evidence.vcp} max={COMPONENT_WEIGHTS.vcp} />
      <VolumeCard evidence={evidence.volume} max={COMPONENT_WEIGHTS.volume} />
      <FundamentalsCard
        evidence={evidence.fundamentals}
        max={COMPONENT_WEIGHTS.fundamentals}
        missingFields={missing_fields}
      />
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────

function BoolRow({ label, value }: { label: string; value?: boolean }) {
  if (value === undefined || value === null) {
    return (
      <div className={styles.evidenceRow}>
        <span className={styles.evidenceIcon}>⚠</span>
        <span className={styles.evidenceLabel}>{label}</span>
        <span className={styles.evidenceValue} style={{ color: 'var(--warning)' }}>
          No data
        </span>
      </div>
    );
  }
  return (
    <div className={styles.evidenceRow}>
      <span className={styles.evidenceIcon}>{value ? '✅' : '❌'}</span>
      <span className={styles.evidenceLabel}>{label}</span>
    </div>
  );
}

function NumRow({ label, value, suffix }: { label: string; value?: number | null; suffix?: string }) {
  if (value === undefined || value === null) {
    return (
      <div className={styles.evidenceRow}>
        <span className={styles.evidenceIcon}>⚠</span>
        <span className={styles.evidenceLabel}>{label}</span>
        <span className={styles.evidenceValue} style={{ color: 'var(--warning)' }}>
          No data
        </span>
      </div>
    );
  }
  return (
    <div className={styles.evidenceRow}>
      <span className={styles.evidenceIcon}>📊</span>
      <span className={styles.evidenceLabel}>{label}</span>
      <span className={styles.evidenceValue}>
        {typeof value === 'number' ? value.toFixed(2) : value}
        {suffix ?? ''}
      </span>
    </div>
  );
}

// ── Per-component cards ─────────────────────────────────────

function TrendCard({ evidence, max }: { evidence: TrendEvidence; max: number }) {
  return (
    <div className={styles.evidenceCard}>
      <div className={styles.evidenceCardHeader}>
        <span className={styles.evidenceCardTitle}>
          <span>📈</span> Trend Structure
        </span>
        <span className={styles.evidenceCardScore} style={{ color: 'var(--component-trend)' }}>
          {evidence.score.toFixed(1)} / {max}
        </span>
      </div>
      <BoolRow label="Price > SMA50" value={evidence.price_above_sma50} />
      <BoolRow label="SMA50 > SMA150" value={evidence.sma50_above_sma150} />
      <BoolRow label="SMA150 > SMA200" value={evidence.sma150_above_sma200} />
      <BoolRow label="SMA200 Rising" value={evidence.sma200_rising} />
      <BoolRow label="Near 52w High" value={evidence.near_52w_high} />
      {evidence.near_52w_high_pct !== undefined && evidence.near_52w_high_pct !== null && (
        <NumRow label="Distance to 52w High" value={evidence.near_52w_high_pct} suffix="%" />
      )}
    </div>
  );
}

function VcpCard({ evidence, max }: { evidence: VcpEvidence; max: number }) {
  return (
    <div className={styles.evidenceCard}>
      <div className={styles.evidenceCardHeader}>
        <span className={styles.evidenceCardTitle}>
          <span>🔄</span> VCP Quality
        </span>
        <span className={styles.evidenceCardScore} style={{ color: 'var(--component-vcp)' }}>
          {evidence.score.toFixed(1)} / {max}
        </span>
      </div>
      <BoolRow label="Pattern Detected" value={evidence.pattern_detected} />
      {evidence.vcp_score !== undefined && evidence.vcp_score !== null && (
        <NumRow label="VCP Score" value={evidence.vcp_score} suffix=" / 100" />
      )}
      {evidence.contraction_count !== undefined && evidence.contraction_count !== null && (
        <NumRow label="Contraction Count" value={evidence.contraction_count} />
      )}
      {evidence.depth_pct !== undefined && evidence.depth_pct !== null && (
        <NumRow label="Max Depth" value={evidence.depth_pct} suffix="%" />
      )}
    </div>
  );
}

function VolumeCard({ evidence, max }: { evidence: VolumeEvidence; max: number }) {
  return (
    <div className={styles.evidenceCard}>
      <div className={styles.evidenceCardHeader}>
        <span className={styles.evidenceCardTitle}>
          <span>📊</span> Volume Quality
        </span>
        <span className={styles.evidenceCardScore} style={{ color: 'var(--component-volume)' }}>
          {evidence.score.toFixed(1)} / {max}
        </span>
      </div>
      {/* Accept either backend naming or legacy UI naming for robustness */}
      <BoolRow
        label="Pullback below volume SMA"
        value={
          // backend: pullback_below_sma | UI older: pullback_below_avg
          (evidence as any).pullback_below_avg ?? (evidence as any).pullback_below_sma
        }
      />
      <BoolRow
        label="Volume dry-up detected"
        value={
          // backend: volume_dryup | UI older: volume_dry_up
          (evidence as any).volume_dry_up ?? (evidence as any).volume_dryup
        }
      />
      <BoolRow
        label="No abnormal selling spikes"
        value={
          // backend: no_heavy_selling | UI older: no_abnormal_selling
          (evidence as any).no_abnormal_selling ?? (evidence as any).no_heavy_selling
        }
      />
    </div>
  );
}

function FundamentalsCard({
  evidence,
  max,
  missingFields,
}: {
  evidence: FundamentalsEvidence;
  max: number;
  missingFields: string[];
}) {
  // Match prefixed (fundamentals.*, fund*) and un-prefixed fundamentals keys
  const FUND_KEYS = ['revenue_growth_yoy', 'earnings_growth_yoy', 'roe', 'net_margin', 'debt_equity'];
  const fundMissing = missingFields.filter(
    (f) => f.startsWith('fundamentals.') || f.startsWith('fund') || FUND_KEYS.includes(f),
  );

  return (
    <div className={styles.evidenceCard}>
      <div className={styles.evidenceCardHeader}>
        <span className={styles.evidenceCardTitle}>
          <span>💰</span> Fundamentals
        </span>
        <span className={styles.evidenceCardScore} style={{ color: 'var(--component-fundamentals)' }}>
          {evidence.score.toFixed(1)} / {max}
        </span>
      </div>
      <NumRow label="Revenue Growth YoY" value={evidence.revenue_growth_yoy} suffix="%" />
      <NumRow label="Earnings Growth YoY" value={evidence.earnings_growth_yoy} suffix="%" />
      <NumRow label="ROE" value={evidence.roe} suffix="%" />
      <NumRow label="Net Margin" value={evidence.net_margin} suffix="%" />
      <NumRow label="Debt/Equity" value={evidence.debt_equity} />
      {fundMissing.length > 0 && (
        <div className={styles.missingWarning}>
          ⚠ Missing fields: {fundMissing.length}
        </div>
      )}
    </div>
  );
}

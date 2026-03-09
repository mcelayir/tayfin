/**
 * DonutChart — SVG donut showing the 4 MCSA component scores.
 *
 * Segments sized by actual score (not weight cap).
 * Center text shows total score + band.
 * See: DESIGN_SPEC §3.4 (Donut Chart)
 */

import type { McsaResult } from '../../types/mcsa';
import { COMPONENT_WEIGHTS } from '../../types/mcsa';

const SIZE = 160;
const STROKE = 24;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

interface Segment {
  label: string;
  value: number;
  max: number;
  color: string;
}

function getSegments(item: McsaResult): Segment[] {
  return [
    { label: 'Trend',        value: item.trend_score,       max: COMPONENT_WEIGHTS.trend,        color: 'var(--component-trend)' },
    { label: 'VCP',          value: item.vcp_component,     max: COMPONENT_WEIGHTS.vcp,          color: 'var(--component-vcp)' },
    { label: 'Volume',       value: item.volume_score,      max: COMPONENT_WEIGHTS.volume,       color: 'var(--component-volume)' },
    { label: 'Fundamentals', value: item.fundamental_score, max: COMPONENT_WEIGHTS.fundamentals, color: 'var(--component-fundamentals)' },
  ];
}

interface DonutChartProps {
  item: McsaResult;
}

export function DonutChart({ item }: DonutChartProps) {
  const segments = getSegments(item);
  const total = segments.reduce((s, seg) => s + seg.value, 0);
  const maxTotal = segments.reduce((s, seg) => s + seg.max, 0);

  // Calculate stroke-dasharray offsets for each segment
  let offset = 0;
  const arcs = segments.map((seg) => {
    const pct = maxTotal > 0 ? seg.value / maxTotal : 0;
    const dashLen = pct * CIRCUMFERENCE;
    const dashGap = CIRCUMFERENCE - dashLen;
    const arc = {
      ...seg,
      dasharray: `${dashLen} ${dashGap}`,
      dashoffset: -offset,
    };
    offset += dashLen;
    return arc;
  });

  return (
    <svg
      width={SIZE}
      height={SIZE}
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      style={{ transform: 'rotate(-90deg)' }}
      aria-label={`Score donut: ${total.toFixed(1)} / ${maxTotal}`}
    >
      {/* Background ring */}
      <circle
        cx={SIZE / 2}
        cy={SIZE / 2}
        r={RADIUS}
        fill="none"
        stroke="var(--bg-overlay)"
        strokeWidth={STROKE}
      />

      {/* Segments */}
      {arcs.map((arc) => (
        <circle
          key={arc.label}
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke={arc.color}
          strokeWidth={STROKE}
          strokeDasharray={arc.dasharray}
          strokeDashoffset={arc.dashoffset}
          strokeLinecap="butt"
        >
          <title>{`${arc.label}: ${arc.value.toFixed(1)} / ${arc.max}`}</title>
        </circle>
      ))}

      {/* Center text */}
      <text
        x={SIZE / 2}
        y={SIZE / 2 - 6}
        style={{
          transform: 'rotate(90deg)',
          transformOrigin: 'center',
          textAnchor: 'middle',
          dominantBaseline: 'central',
          fontFamily: 'var(--font-mono)',
          fontSize: '18px',
          fontWeight: 700,
          fill: 'var(--text-primary)',
        }}
      >
        {item.mcsa_score.toFixed(1)}
      </text>
      <text
        x={SIZE / 2}
        y={SIZE / 2 + 14}
        style={{
          transform: 'rotate(90deg)',
          transformOrigin: 'center',
          textAnchor: 'middle',
          dominantBaseline: 'central',
          fontFamily: 'var(--font-ui)',
          fontSize: '11px',
          fontWeight: 600,
          fill: 'var(--text-secondary)',
          textTransform: 'capitalize',
        }}
      >
        {item.mcsa_band}
      </text>
    </svg>
  );
}

export { getSegments };
export type { Segment };

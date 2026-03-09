/**
 * DetailPanel component tests.
 *
 * Covers: donut chart rendering, evidence cards, missing data warnings.
 */

import { render, screen } from '@testing-library/react';
import { DetailPanel } from './index';
import { makeMcsaResult } from '../../test/fixtures';

describe('DetailPanel', () => {
  const item = makeMcsaResult({
    ticker: 'BKR',
    mcsa_score: 69.85,
    mcsa_band: 'neutral',
    trend_score: 30,
    vcp_component: 24.85,
    volume_score: 15,
    fundamental_score: 0,
    evidence: {
      trend: {
        score: 30,
        price_above_sma50: true,
        sma50_above_sma150: true,
        sma150_above_sma200: true,
        sma200_rising: true,
        near_52w_high: true,
        near_52w_high_pct: 8.35,
      },
      vcp: {
        score: 24.85,
        pattern_detected: true,
        vcp_score: 71.0,
        contraction_count: 3,
        depth_pct: 15.2,
      },
      volume: {
        score: 15,
        pullback_below_avg: true,
        volume_dry_up: true,
        no_abnormal_selling: true,
      },
      fundamentals: {
        score: 0,
        revenue_growth_yoy: null,
        earnings_growth_yoy: null,
        roe: null,
        net_margin: null,
        debt_equity: null,
      },
    },
    missing_fields: ['fundamentals.revenue_growth_yoy', 'fundamentals.earnings_growth_yoy', 'fundamentals.roe', 'fundamentals.net_margin', 'fundamentals.debt_equity'],
  });

  it('renders ticker and score in header', () => {
    render(<DetailPanel item={item} />);

    expect(screen.getByText('BKR')).toBeInTheDocument();
    // Score displayed as 1 decimal place: 69.85 → 69.8
    expect(screen.getByText(/69\.8 \/ 100/)).toBeInTheDocument();
  });

  it('renders donut chart SVG', () => {
    const { container } = render(<DetailPanel item={item} />);

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders all four evidence card sections', () => {
    render(<DetailPanel item={item} />);

    expect(screen.getByText(/Trend Structure/)).toBeInTheDocument();
    expect(screen.getByText(/VCP Quality/)).toBeInTheDocument();
    expect(screen.getByText(/Volume Quality/)).toBeInTheDocument();
    // 'Fundamentals' appears multiple times (legend + card title), use getAllByText
    expect(screen.getAllByText(/Fundamentals/).length).toBeGreaterThanOrEqual(1);
  });

  it('shows trend evidence boolean flags', () => {
    render(<DetailPanel item={item} />);

    expect(screen.getByText(/Price > SMA50/)).toBeInTheDocument();
    expect(screen.getByText(/SMA50 > SMA150/)).toBeInTheDocument();
  });

  it('shows VCP evidence details', () => {
    render(<DetailPanel item={item} />);

    expect(screen.getByText(/Pattern Detected/)).toBeInTheDocument();
    expect(screen.getByText(/71\.0/)).toBeInTheDocument();
  });

  it('shows volume evidence checks', () => {
    render(<DetailPanel item={item} />);

    expect(screen.getByText(/Pullback below volume SMA/)).toBeInTheDocument();
    expect(screen.getByText(/Volume dry-up/)).toBeInTheDocument();
  });

  it('shows missing field count for fundamentals', () => {
    render(<DetailPanel item={item} />);

    expect(screen.getByText(/Missing fields: 5/)).toBeInTheDocument();
  });

  it('renders without evidence details gracefully', () => {
    const minimal = makeMcsaResult({
      ticker: 'TEST',
      mcsa_score: 30,
      mcsa_band: 'weak',
    });

    render(<DetailPanel item={minimal} />);
    expect(screen.getByText(/TEST/)).toBeInTheDocument();
  });
});

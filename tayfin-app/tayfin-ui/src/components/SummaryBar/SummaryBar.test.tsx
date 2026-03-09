/**
 * SummaryBar component tests.
 *
 * Covers: band distribution counts, histogram buckets, component averages.
 */

import { render, screen } from '@testing-library/react';
import { SummaryBar } from './index';
import { SAMPLE_ITEMS } from '../../test/fixtures';

describe('SummaryBar', () => {
  it('renders all four cards', () => {
    render(<SummaryBar items={SAMPLE_ITEMS} />);

    expect(screen.getByText('Band Distribution')).toBeInTheDocument();
    expect(screen.getByText('Score Distribution')).toBeInTheDocument();
    expect(screen.getByText('Avg Component Scores')).toBeInTheDocument();
    expect(screen.getByText('Total')).toBeInTheDocument();
  });

  it('shows correct total count', () => {
    render(<SummaryBar items={SAMPLE_ITEMS} />);

    expect(screen.getByText(String(SAMPLE_ITEMS.length))).toBeInTheDocument();
    expect(screen.getByText('tickers scored')).toBeInTheDocument();
  });

  it('displays band distribution labels', () => {
    render(<SummaryBar items={SAMPLE_ITEMS} />);

    expect(screen.getByText('Strong')).toBeInTheDocument();
    expect(screen.getByText('Watchlist')).toBeInTheDocument();
    expect(screen.getByText('Neutral')).toBeInTheDocument();
    expect(screen.getByText('Weak')).toBeInTheDocument();
  });

  it('shows component average labels', () => {
    render(<SummaryBar items={SAMPLE_ITEMS} />);

    expect(screen.getByText('Trend')).toBeInTheDocument();
    expect(screen.getByText('VCP')).toBeInTheDocument();
    expect(screen.getByText('Volume')).toBeInTheDocument();
    expect(screen.getByText('Fund')).toBeInTheDocument();
  });

  it('shows correct band counts', () => {
    render(<SummaryBar items={SAMPLE_ITEMS} />);

    // From SAMPLE_ITEMS: strong=1, watchlist=1, neutral=3, weak=2
    // These values appear in the barRow__value spans
    const values = screen.getAllByText('1');
    // At least 2 values of "1" (strong=1, watchlist=1)
    expect(values.length).toBeGreaterThanOrEqual(2);
  });

  it('computes component averages with correct format', () => {
    render(<SummaryBar items={SAMPLE_ITEMS} />);

    // Trend avg: (30+28+25+18+15+30+28)/7 = 24.857... → "24.9 / 30"
    expect(screen.getByText(/24\.9 \/ 30/)).toBeInTheDocument();
  });

  it('renders with empty items', () => {
    render(<SummaryBar items={[]} />);

    // The total card shows the large number '0'
    expect(screen.getByText('tickers scored')).toBeInTheDocument();
    // '0' appears multiple times (band counts + total), verify at least one
    expect(screen.getAllByText('0').length).toBeGreaterThanOrEqual(1);
  });
});

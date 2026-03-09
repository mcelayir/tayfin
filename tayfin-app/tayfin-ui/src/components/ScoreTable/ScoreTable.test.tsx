/**
 * ScoreTable component tests.
 *
 * Covers: rendering, sorting, row expansion, empty state, missing fields.
 */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ScoreTable } from './index';
import { SAMPLE_ITEMS } from '../../test/fixtures';

// ── Rendering ──

describe('ScoreTable', () => {
  it('renders all tickers', () => {
    render(
      <ScoreTable items={SAMPLE_ITEMS} expandedTicker={null} onRowClick={() => {}} />,
    );

    for (const item of SAMPLE_ITEMS) {
      expect(screen.getByText(item.ticker)).toBeInTheDocument();
    }
  });

  it('renders empty state when items is empty', () => {
    render(
      <ScoreTable items={[]} expandedTicker={null} onRowClick={() => {}} />,
    );

    expect(screen.getByText(/No MCSA results match your filters/)).toBeInTheDocument();
  });

  it('shows warning icon for tickers with missing fields', () => {
    render(
      <ScoreTable items={SAMPLE_ITEMS} expandedTicker={null} onRowClick={() => {}} />,
    );

    // BKR has missing_fields
    const bkrRow = screen.getByText('BKR').closest('tr')!;
    expect(within(bkrRow).getByText('⚠', { exact: false })).toBeInTheDocument();
  });

  // ── Sorting ──

  it('sorts by score descending by default', () => {
    render(
      <ScoreTable items={SAMPLE_ITEMS} expandedTicker={null} onRowClick={() => {}} />,
    );

    const rows = screen.getAllByRole('row').filter((r) => r.querySelector('td'));
    const firstTicker = within(rows[0]).getByText('AMZN');
    expect(firstTicker).toBeInTheDocument();
  });

  it('toggles sort direction on column header click', async () => {
    const user = userEvent.setup();
    render(
      <ScoreTable items={SAMPLE_ITEMS} expandedTicker={null} onRowClick={() => {}} />,
    );

    // Click Score header to switch to ascending
    const scoreHeader = screen.getByText('Score');
    await user.click(scoreHeader);

    const rows = screen.getAllByRole('row').filter((r) => r.querySelector('td'));
    const firstTicker = within(rows[0]).getByText('GOOG');
    expect(firstTicker).toBeInTheDocument();
  });

  it('sorts by ticker when clicking Ticker header', async () => {
    const user = userEvent.setup();
    render(
      <ScoreTable items={SAMPLE_ITEMS} expandedTicker={null} onRowClick={() => {}} />,
    );

    const tickerHeader = screen.getByText('Ticker');
    await user.click(tickerHeader); // descending first
    await user.click(tickerHeader); // ascending

    const rows = screen.getAllByRole('row').filter((r) => r.querySelector('td'));
    const firstTicker = within(rows[0]).getByText('AMZN');
    expect(firstTicker).toBeInTheDocument();
  });

  // ── Row expansion ──

  it('calls onRowClick with the ticker when a row is clicked', async () => {
    const user = userEvent.setup();
    const onRowClick = vi.fn();

    render(
      <ScoreTable items={SAMPLE_ITEMS} expandedTicker={null} onRowClick={onRowClick} />,
    );

    const bkrCell = screen.getByText('BKR');
    await user.click(bkrCell.closest('tr')!);
    expect(onRowClick).toHaveBeenCalledWith('BKR');
  });

  it('renders detail panel for expanded ticker', () => {
    render(
      <ScoreTable items={SAMPLE_ITEMS} expandedTicker="BKR" onRowClick={() => {}} />,
    );

    // Detail panel renders the region for BKR
    expect(screen.getByRole('region', { name: /Detail for BKR/ })).toBeInTheDocument();
  });

  // ── Keyboard navigation ──

  it('supports Enter key to trigger row click', async () => {
    const user = userEvent.setup();
    const onRowClick = vi.fn();

    render(
      <ScoreTable items={SAMPLE_ITEMS} expandedTicker={null} onRowClick={onRowClick} />,
    );

    const rows = screen.getAllByRole('row').filter((r) => r.getAttribute('tabindex') === '0');
    rows[0].focus();
    await user.keyboard('{Enter}');
    expect(onRowClick).toHaveBeenCalled();
  });

  // ── Score display ──

  it('displays scores with one decimal place', () => {
    render(
      <ScoreTable items={SAMPLE_ITEMS} expandedTicker={null} onRowClick={() => {}} />,
    );

    // 69.85.toFixed(1) = '69.8', 88.0.toFixed(1) = '88.0'
    const scoreTexts = screen.getAllByText(/^\d+\.\d$/);
    const values = scoreTexts.map((el) => el.textContent);
    expect(values).toContain('69.8');
    expect(values).toContain('88.0');
  });
});

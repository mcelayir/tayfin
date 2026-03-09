/**
 * FilterBar component tests.
 *
 * Covers: band dropdown, min score slider, ticker search, reset.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FilterBar } from './index';
import type { McsaBand } from '../../types/mcsa';

function renderFilterBar(overrides: Partial<Parameters<typeof FilterBar>[0]> = {}) {
  const defaultProps = {
    bands: new Set<McsaBand>(['strong', 'watchlist', 'neutral', 'weak']),
    minScore: 0,
    tickerSearch: '',
    totalCount: 101,
    filteredCount: 101,
    hasActiveFilters: false,
    onToggleBand: vi.fn(),
    onMinScoreChange: vi.fn(),
    onTickerSearchChange: vi.fn(),
    onReset: vi.fn(),
    ...overrides,
  };

  return { ...render(<FilterBar {...defaultProps} />), props: defaultProps };
}

describe('FilterBar', () => {
  it('renders all controls', () => {
    renderFilterBar();

    expect(screen.getByText('Band')).toBeInTheDocument();
    expect(screen.getByText('All Bands')).toBeInTheDocument();
    expect(screen.getByLabelText(/Min Score/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search ticker…')).toBeInTheDocument();
    expect(screen.getByText('101 / 101')).toBeInTheDocument();
  });

  it('shows filtered count', () => {
    renderFilterBar({ filteredCount: 14, hasActiveFilters: true });

    expect(screen.getByText('14 / 101')).toBeInTheDocument();
    expect(screen.getByText('Reset')).toBeInTheDocument();
  });

  it('opens band dropdown on click', async () => {
    const user = userEvent.setup();
    renderFilterBar();

    await user.click(screen.getByText('All Bands'));
    expect(screen.getByText('Strong')).toBeInTheDocument();
    expect(screen.getByText('Watchlist')).toBeInTheDocument();
    expect(screen.getByText('Neutral')).toBeInTheDocument();
    expect(screen.getByText('Weak')).toBeInTheDocument();
  });

  it('calls onToggleBand when a band option is clicked', async () => {
    const user = userEvent.setup();
    const { props } = renderFilterBar();

    await user.click(screen.getByText('All Bands'));
    await user.click(screen.getByText('Strong'));
    expect(props.onToggleBand).toHaveBeenCalledWith('strong');
  });

  it('renders slider with correct initial value', () => {
    renderFilterBar({ minScore: 25 });

    const slider = screen.getByLabelText(/Min Score/) as HTMLInputElement;
    expect(slider.value).toBe('25');
    expect(slider.type).toBe('range');
    expect(slider.min).toBe('0');
    expect(slider.max).toBe('100');
  });

  it('calls onTickerSearchChange when typing in search', async () => {
    const user = userEvent.setup();
    const { props } = renderFilterBar();

    const searchInput = screen.getByPlaceholderText('Search ticker…');
    await user.type(searchInput, 'A');
    expect(props.onTickerSearchChange).toHaveBeenCalled();
  });

  it('calls onReset when Reset button is clicked', async () => {
    const user = userEvent.setup();
    const { props } = renderFilterBar({ hasActiveFilters: true });

    await user.click(screen.getByText('Reset'));
    expect(props.onReset).toHaveBeenCalled();
  });

  it('does not show Reset when no active filters', () => {
    renderFilterBar({ hasActiveFilters: false });

    expect(screen.queryByText('Reset')).not.toBeInTheDocument();
  });

  it('shows custom band label when not all bands selected', () => {
    renderFilterBar({
      bands: new Set<McsaBand>(['strong', 'neutral']),
    });

    expect(screen.getByText('Strong, Neutral')).toBeInTheDocument();
  });
});

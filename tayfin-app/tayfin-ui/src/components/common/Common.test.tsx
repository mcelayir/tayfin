/**
 * Common component tests: BandBadge, ProgressBar.
 */

import { render, screen } from '@testing-library/react';
import { BandBadge } from './BandBadge';
import { ProgressBar } from './ProgressBar';

describe('BandBadge', () => {
  it('renders the band label', () => {
    render(<BandBadge band="strong" />);
    expect(screen.getByText('Strong')).toBeInTheDocument();
  });

  it('renders all band types', () => {
    const bands = ['strong', 'watchlist', 'neutral', 'weak'] as const;
    for (const band of bands) {
      const { unmount } = render(<BandBadge band={band} />);
      expect(screen.getByText(new RegExp(band, 'i'))).toBeInTheDocument();
      unmount();
    }
  });
});

describe('ProgressBar', () => {
  it('renders with role=meter', () => {
    render(<ProgressBar value={15} max={30} color="#2dd4bf" />);
    const meter = screen.getByRole('meter');
    expect(meter).toBeInTheDocument();
  });

  it('sets correct aria attributes', () => {
    render(<ProgressBar value={15} max={30} color="#2dd4bf" />);
    const meter = screen.getByRole('meter');
    expect(meter).toHaveAttribute('aria-valuenow', '15');
    expect(meter).toHaveAttribute('aria-valuemax', '30');
  });

  it('handles zero value without error', () => {
    render(<ProgressBar value={0} max={30} color="#2dd4bf" />);
    const meter = screen.getByRole('meter');
    expect(meter).toHaveAttribute('aria-valuenow', '0');
  });
});

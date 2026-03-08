/**
 * Custom hook for loading MCSA dashboard data.
 */

import { useEffect, useState, useCallback } from 'react';
import type { McsaResult } from '../types/mcsa';
import { fetchMcsaDashboard, ApiError } from '../api/mcsa';

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

interface UseMcsaDataReturn {
  items: McsaResult[];
  state: LoadingState;
  error: string | null;
  reload: () => void;
}

export function useMcsaData(): UseMcsaDataReturn {
  const [items, setItems] = useState<McsaResult[]>([]);
  const [state, setState] = useState<LoadingState>('idle');
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState('loading');
    setError(null);
    try {
      const resp = await fetchMcsaDashboard();
      setItems(resp.items);
      setState('success');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`API error ${err.status}: ${err.body}`);
      } else {
        setError('Unable to load MCSA data. Screener API unreachable.');
      }
      setState('error');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { items, state, error, reload: load };
}

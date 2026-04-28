import { useState, useEffect } from 'react';
import { loadVRM, getExpressionNames, getMorphTargetNames, VRM } from '@/lib/vrm/loader';

interface UseVRMResult {
  vrm: VRM | null;
  expressionNames: string[];
  morphTargetNames: string[];
  isLoading: boolean;
  error: string | null;
}

export function useVRM(url: string): UseVRMResult {
  const [vrm, setVrm] = useState<VRM | null>(null);
  const [expressionNames, setExpressionNames] = useState<string[]>([]);
  const [morphTargetNames, setMorphTargetNames] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const loadedVrm = await loadVRM(url);

        if (cancelled) return;

        setVrm(loadedVrm);
        setExpressionNames(getExpressionNames(loadedVrm));
        setMorphTargetNames(getMorphTargetNames(loadedVrm));
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load VRM');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [url]);

  return { vrm, expressionNames, morphTargetNames, isLoading, error };
}

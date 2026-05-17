import { useEffect, useState } from 'react';
import { api } from '@/lib/api-client';
import { transformQuantitativeBenchmark, type QuantitativeBenchmark } from '@/lib/adapters/benchmark';
import { StructuralVerdictExplainer } from './StructuralVerdictExplainer';

/**
 * Thin loader wrapping StructuralVerdictExplainer so it self-fetches the
 * quantitative payload without coupling to the parent panel's lifecycle.
 * Re-fetches when `reloadToken` changes (driven by a completed live run).
 */
export function StructuralVerdictExplainerLoader({ reloadToken = 0 }: { reloadToken?: number }) {
  const [data, setData] = useState<QuantitativeBenchmark | null>(null);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const raw = await api.getQuantitativeBenchmark();
        if (!cancelled) setData(transformQuantitativeBenchmark(raw));
      } catch {
        if (!cancelled) setData(null);
      }
    })();
    return () => { cancelled = true; };
  }, [reloadToken]);
  if (!data) return null;
  return <StructuralVerdictExplainer data={data} />;
}

import { useEffect, useRef, useState } from 'react';
import { AlertCircle, Compass, Network, Sparkles } from 'lucide-react';
import { api, type BackendIntent } from '@/lib/api-client';
import { cn } from '@/lib/utils';

/**
 * IntentChip — debounced live preview of which investigation workflow
 * the analyst's typed query maps to. Calls POST /orchestrator/intent.
 *
 * Hard contracts:
 *   • Pure preview — never triggers a real investigation.
 *   • If intent is 'unknown', expand into suggested operational workflows
 *     (NOT chatbot fallback prose) — clicking a suggestion swaps the input.
 *   • Sub-millisecond on the backend; we still debounce 200ms to coalesce
 *     keystrokes.
 *   • Silent failure if backend is unreachable (returns null).
 */
export function IntentChip({
  query,
  onPickSuggestion,
}: {
  query: string;
  /** Called when the analyst clicks a suggested workflow chip — the parent
   *  swaps the input text. We do NOT mutate the input directly. */
  onPickSuggestion?: (suggestionText: string) => void;
}) {
  const [intent, setIntent] = useState<BackendIntent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lastQueryRef = useRef<string>('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const trimmed = (query || '').trim();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    abortRef.current?.abort();

    if (!trimmed) {
      setIntent(null);
      setError(null);
      lastQueryRef.current = '';
      return;
    }
    if (trimmed === lastQueryRef.current) return;

    debounceRef.current = setTimeout(async () => {
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const result = await api.classifyIntent(trimmed, controller.signal);
        lastQueryRef.current = trimmed;
        setIntent(result);
        setError(null);
      } catch (e) {
        if ((e as { name?: string })?.name === 'AbortError') return;
        setError(e instanceof Error ? e.message : String(e));
        setIntent(null);
      }
    }, 200);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  if (!intent && !error) return null;
  if (error) return null;
  if (!intent) return null;

  const isUnknown = intent.kind === 'unknown';
  const isWeak = !isUnknown && intent.confidence < 0.6;
  const color = isUnknown
    ? 'var(--color-amber-400)'
    : isWeak
    ? 'var(--color-amber-300)'
    : 'var(--color-emerald-400)';
  const Icon = isUnknown ? AlertCircle : isWeak ? Compass : Sparkles;

  return (
    <div className="space-y-1.5">
      <div
        className="inline-flex items-center gap-2 h-6 px-2 rounded-sm border font-mono text-[9.5px] tracking-[0.22em] uppercase"
        style={{ color, borderColor: `${color}55`, background: `${color}0d` }}
        title={intent.description}
      >
        <Icon className="w-3 h-3" />
        <span>workflow</span>
        <span className="text-[var(--color-text-ghost)]">·</span>
        <span style={{ color }}>{intent.display_name}</span>
        {!isUnknown && (
          <>
            <span className="text-[var(--color-text-ghost)]">·</span>
            <span>{Math.round(intent.confidence * 100)}%</span>
          </>
        )}
        {intent.matched_entity_ids.length > 0 && (
          <>
            <span className="text-[var(--color-text-ghost)]">·</span>
            <Network className="w-2.5 h-2.5" />
            <span>{intent.matched_entity_ids.slice(0, 3).join(' · ')}</span>
            {intent.matched_entity_ids.length > 3 && (
              <span>+{intent.matched_entity_ids.length - 3}</span>
            )}
          </>
        )}
      </div>

      {isUnknown && intent.suggested_workflows.length > 0 && (
        <div className="space-y-1">
          {intent.operational_hint && (
            <div className="font-mono text-[9.5px] text-[var(--color-text-muted)] leading-snug max-w-[600px]">
              {intent.operational_hint}
            </div>
          )}
          <div className="flex flex-wrap gap-1">
            {intent.suggested_workflows.map((wf) => (
              <button
                key={wf.kind}
                onClick={() => onPickSuggestion?.(_seedQueryForWorkflow(wf.kind))}
                className={cn(
                  'chip text-[9px] inline-flex items-center gap-1',
                  'hover:bg-[rgba(34,211,238,0.06)] hover:border-[rgba(34,211,238,0.32)] hover:text-[var(--color-ice-400)]',
                )}
                title={wf.description}
              >
                <span className="text-[var(--color-text-muted)]">↻</span>
                <span>{wf.display_name}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Seed query text per workflow — clicking a suggestion replaces the user's
 * typed query with a concrete starter sentence so they can run it directly.
 */
function _seedQueryForWorkflow(kind: string): string {
  switch (kind) {
    case 'rank_suspects':         return 'who is the most suspected';
    case 'find_ring':             return 'show hidden fraud rings';
    case 'trace_money':           return 'trace laundering paths';
    case 'ownership_chain':       return 'who owns the most suspicious companies';
    case 'shared_infrastructure': return 'find shared device clusters';
    case 'hidden_relationships':  return 'uncover hidden relationships';
    case 'entity_dossier':        return 'show me the dossier for P-005027';
    case 'neighborhood_expansion':return 'what is connected to FR-001';
    default:                      return '';
  }
}

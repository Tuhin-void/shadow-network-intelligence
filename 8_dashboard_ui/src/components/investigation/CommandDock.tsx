import { useEffect, useMemo, useState } from 'react';
import { useIntelStore } from '@/store/intel-store';
import {
  queriesForPreset,
  runQuery,
  type InvestigationQuery,
} from '@/lib/queries';
import {
  ChevronUp,
  CircleDot,
  CornerDownLeft,
  Crosshair,
  GitBranch,
  Layers,
  Network,
  Rewind,
  Route,
  Spline,
  Terminal,
  Wallet,
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { cn, entityGlyph, tierColor } from '@/lib/utils';

const QUERY_ICON: Record<InvestigationQuery['kind'], typeof Network> = {
  isolate_ring: CircleDot,
  show_hidden_to: Spline,
  trace_ownership_from: Route,
  shortest_path: GitBranch,
  follow_money_exit: Wallet,
  expand_offshore: Layers,
  find_shared_infra: Network,
  reverse_edge_from_terminal: Rewind,
};

/**
 * CommandDock — persistent floating intelligence command interface.
 *
 * Bottom-center, ~720 px wide, surface-floating. Always available on
 * graph-bearing routes. Hosts:
 *   • TARGET fuzzy search (entities / presets / signals)
 *   • Quick-query buttons (chips) — each one is a graph transformation
 *   • Expand affordance reveals the full QueryRail
 *
 * NOT a chatbot. Every action mutates store → mutates graph.
 */
export function CommandDock() {
  const {
    active,
    presets,
    selectPreset,
    selectEntity,
    startStream,
    applyQuery,
    narration,
    focusModeOn,
  } = useIntelStore();

  const [q, setQ] = useState('');
  const [expanded, setExpanded] = useState(false);
  const queries = useMemo(() => queriesForPreset(active), [active]);

  // ESC clears query OR collapses the expanded queries panel
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      if (expanded) {
        setExpanded(false);
        e.preventDefault();
      } else if (q) {
        setQ('');
        e.preventDefault();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [expanded, q]);

  // Fuzzy suggestions across entities/presets/signals
  const suggestions = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return [];
    const out: Array<{
      type: 'entity' | 'preset' | 'signal';
      id: string;
      label: string;
      hint: string;
      tier?: string;
      kind?: string;
    }> = [];
    presets.forEach((p) => {
      if (
        [p.label, p.id, ...p.tags, p.description]
          .join(' ')
          .toLowerCase()
          .includes(term)
      ) {
        out.push({
          type: 'preset',
          id: p.id,
          label: p.label,
          hint: `preset · ${p.tags.join(' · ')}`,
        });
      }
    });
    active.graph.entities.forEach((e) => {
      const text = `${e.label} ${e.id} ${e.kind} ${(e.flags ?? []).join(' ')}`.toLowerCase();
      if (text.includes(term)) {
        out.push({
          type: 'entity',
          id: e.id,
          label: e.label,
          hint: `${e.kind.replace('_', ' ')} · risk ${e.risk}`,
          tier: e.tier,
          kind: e.kind,
        });
      }
    });
    active.report.structuralSignals.forEach((s) => {
      if (
        s.name.toLowerCase().includes(term) ||
        s.description.toLowerCase().includes(term)
      ) {
        out.push({
          type: 'signal',
          id: s.id,
          label: s.name,
          hint: `signal · intensity ${s.intensity.toFixed(2)}`,
        });
      }
    });
    return out.slice(0, 8);
  }, [q, active, presets]);

  const apply = (s: (typeof suggestions)[number]) => {
    if (s.type === 'preset') {
      selectPreset(s.id);
      setTimeout(() => startStream(), 80);
    }
    if (s.type === 'entity') selectEntity(s.id);
    setQ('');
  };

  if (focusModeOn) return null;

  return (
    <div className="absolute bottom-[176px] left-1/2 -translate-x-1/2 z-40 pointer-events-none w-[760px] max-w-[92vw]">
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            className="surface-floating mb-2 pointer-events-auto overflow-hidden"
          >
            <div className="px-3 h-7 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
              <Terminal className="w-3 h-3 text-[var(--color-ice-400)]" />
              <span className="heading-tactical">Investigation queries</span>
              <span className="chip ml-auto text-[9px]">{queries.length}</span>
            </div>
            <div className="p-2 grid grid-cols-2 gap-1.5 max-h-[280px] overflow-y-auto scroll-tactical">
              {queries.map((qu) => {
                const Icon = QUERY_ICON[qu.kind];
                return (
                  <button
                    key={qu.id}
                    onClick={() => {
                      applyQuery(runQuery(active, qu));
                      setExpanded(false);
                    }}
                    className="text-left rounded-sm border border-transparent px-2.5 py-2 hover:border-[rgba(34,211,238,0.32)] hover:bg-[rgba(34,211,238,0.04)]"
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-sm border border-[var(--color-line)] text-[var(--color-ice-400)]">
                        <Icon className="w-3 h-3" strokeWidth={1.4} />
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-[12px] text-[var(--color-text-bright)] truncate">
                          {qu.label}
                        </div>
                        <div className="font-mono text-[9.5px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] truncate">
                          {qu.hint}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="surface-floating pointer-events-auto overflow-hidden">
        {/* Suggestion popover above input */}
        {suggestions.length > 0 && (
          <div className="border-b border-[var(--color-line-soft)] max-h-[260px] overflow-y-auto scroll-tactical">
            {suggestions.map((s, i) => (
              <button
                key={`${s.type}_${s.id}`}
                onClick={() => apply(s)}
                className={cn(
                  'w-full text-left flex items-center gap-2 px-3 h-8',
                  'hover:bg-[rgba(34,211,238,0.05)]',
                  i === 0 && 'bg-[rgba(34,211,238,0.04)]'
                )}
              >
                {s.type === 'entity' && s.kind && s.tier ? (
                  <span
                    className="inline-flex items-center justify-center w-5 h-5 rounded-sm border text-[10px]"
                    style={{
                      borderColor: tierColor(s.tier as 'critical'),
                      color: tierColor(s.tier as 'critical'),
                    }}
                  >
                    {entityGlyph(s.kind as 'person')}
                  </span>
                ) : (
                  <span className="w-5 h-5 inline-flex items-center justify-center text-[var(--color-text-muted)]">
                    <Terminal className="w-3 h-3" />
                  </span>
                )}
                <span className="font-mono text-[9.5px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] w-14">
                  {s.type}
                </span>
                <span className="text-[11px] text-[var(--color-text-primary)] truncate">
                  {s.label}
                </span>
                <span className="ml-auto font-mono text-[9px] text-[var(--color-text-muted)] truncate">
                  {s.hint}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Input row */}
        <div className="flex items-center gap-2 px-3 h-10">
          <Crosshair className="w-3.5 h-3.5 text-[var(--color-ice-400)] shrink-0" />
          <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] shrink-0">
            target
          </span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && suggestions[0]) apply(suggestions[0]);
              if (e.key === 'Escape') setQ('');
            }}
            placeholder="search entity, preset, or signal · ⌘K"
            className="flex-1 min-w-0 bg-transparent outline-none text-[13px] text-[var(--color-text-bright)] placeholder:text-[var(--color-text-faint)]"
          />
          {q && (
            <span className="kbd hidden md:inline-flex">
              <CornerDownLeft className="w-2.5 h-2.5" /> ENTER
            </span>
          )}
          {narration && !q && (
            <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-violet-300)] truncate max-w-[280px]">
              → {narration}
            </span>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            className={cn(
              'h-7 px-2.5 inline-flex items-center gap-1.5 rounded-sm border font-mono text-[9.5px] tracking-[0.22em] uppercase transition-colors',
              expanded
                ? 'border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)]'
                : 'border-[var(--color-line)] text-[var(--color-text-secondary)] hover:text-[var(--color-ice-400)] hover:border-[rgba(34,211,238,0.4)]'
            )}
          >
            <Terminal className="w-3 h-3" />
            queries
            <ChevronUp
              className={cn('w-3 h-3 transition-transform', !expanded && 'rotate-180')}
            />
          </button>
        </div>

        {/* Quick chips — most-used queries always visible */}
        <div className="px-3 pb-2 flex items-center gap-1.5 flex-wrap">
          {queries.slice(0, 4).map((qu) => {
            const Icon = QUERY_ICON[qu.kind];
            return (
              <button
                key={qu.id}
                onClick={() => applyQuery(runQuery(active, qu))}
                className="h-6 px-2 inline-flex items-center gap-1.5 rounded-sm border border-[var(--color-line-soft)] hover:border-[rgba(34,211,238,0.32)] hover:bg-[rgba(34,211,238,0.04)] transition-colors font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-secondary)] hover:text-[var(--color-ice-400)]"
              >
                <Icon className="w-3 h-3" />
                {qu.label.toLowerCase()}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

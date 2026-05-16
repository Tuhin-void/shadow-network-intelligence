import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ArrowRight,
  CircleDot,
  CornerDownLeft,
  FileText,
  GitBranch,
  Network,
  Power,
  Search,
  Spline,
  Sparkles,
  Wallet,
  X,
} from 'lucide-react';
import { useIntelStore } from '@/store/intel-store';
import { entityGlyph, tierColor } from '@/lib/utils';

/**
 * GlobalSearch — ⌘/Ctrl+K intelligence search.
 *
 * Always dismissable: ESC, X button, click outside. Search across:
 *   • entities (people / shells / accounts / wallets / devices …)
 *   • cases (presets)
 *   • rings
 *   • paths
 *   • signals
 *   • reports / dossiers
 */
type Hit =
  | { kind: 'entity';   id: string; presetId: string; label: string; sub: string; tier: string; ekind: string }
  | { kind: 'preset';   id: string; label: string; sub: string }
  | { kind: 'ring';     id: string; presetId: string; label: string; sub: string }
  | { kind: 'path';     id: string; presetId: string; label: string; sub: string }
  | { kind: 'signal';   id: string; presetId: string; label: string; sub: string }
  | { kind: 'report';   id: string; label: string; sub: string }
  | { kind: 'action';   id: string; label: string; sub: string; action: 'replay-awakening' };

const HIT_META: Record<Hit['kind'], { label: string; icon: typeof Network; color: string }> = {
  entity:  { label: 'entity',  icon: Network,    color: 'var(--color-ice-400)' },
  preset:  { label: 'case',    icon: Search,     color: 'var(--color-text-secondary)' },
  ring:    { label: 'ring',    icon: CircleDot,  color: 'var(--color-rose-400)' },
  path:    { label: 'path',    icon: GitBranch,  color: 'var(--color-amber-400)' },
  signal:  { label: 'signal',  icon: Sparkles,   color: 'var(--color-ice-400)' },
  report:  { label: 'report',  icon: FileText,   color: 'var(--color-emerald-400)' },
  action:  { label: 'action',  icon: Power,      color: 'var(--color-violet-400)' },
};

// Operational system actions — discoverable through the same palette the
// analyst uses for everything else. Keyed by a few intent phrases so the
// hit surfaces on related queries without polluting the default landing.
const SYSTEM_ACTIONS: Array<{
  id: string;
  label: string;
  sub: string;
  action: 'replay-awakening';
  match: string[];
}> = [
  {
    id: 'awakening',
    label: 'replay operational awakening',
    sub: 'restart the boot sequence · ⌘⇧B',
    action: 'replay-awakening',
    match: ['replay', 'boot', 'awaken', 'wake', 'awakening', 'restart', 'reset session'],
  },
];

export function GlobalSearch({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const { presets, selectPreset } = useIntelStore();
  const [q, setQ] = useState('');
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQ('');
      setSelected(0);
      // focus after mount
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const hits: Hit[] = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) {
      // Curated default landing — recent / pinned-ish suggestions
      return presets.slice(0, 4).flatMap((p): Hit[] => [
        { kind: 'preset', id: p.id, label: p.label, sub: p.tags.join(' · ') },
      ]);
    }

    const out: Hit[] = [];

    presets.forEach((p) => {
      if (
        [p.label, p.id, p.description, ...p.tags].join(' ').toLowerCase().includes(term)
      ) {
        out.push({
          kind: 'preset',
          id: p.id,
          label: p.label,
          sub: p.tags.join(' · '),
        });
        out.push({
          kind: 'report',
          id: p.id,
          label: `${p.label} dossier`,
          sub: 'classified report',
        });
      }
      p.graph.entities.forEach((e) => {
        const text = `${e.label} ${e.id} ${e.kind} ${(e.flags ?? []).join(' ')}`.toLowerCase();
        if (text.includes(term)) {
          out.push({
            kind: 'entity',
            id: e.id,
            presetId: p.id,
            label: e.label,
            sub: `${e.kind.replace('_', ' ')} · risk ${e.risk} · ${p.label}`,
            tier: e.tier,
            ekind: e.kind,
          });
        }
      });
      p.rings.forEach((r) => {
        if (r.name.toLowerCase().includes(term) || r.id.toLowerCase().includes(term)) {
          out.push({
            kind: 'ring',
            id: r.id,
            presetId: p.id,
            label: r.name,
            sub: `${r.members.length} members · cohesion ${r.cohesion.toFixed(2)} · ${p.label}`,
          });
        }
      });
      p.paths.forEach((path) => {
        if (path.label.toLowerCase().includes(term) || path.intent.includes(term)) {
          out.push({
            kind: 'path',
            id: path.id,
            presetId: p.id,
            label: path.label,
            sub: `${path.hops} hops · ${path.intent.replace('_', ' ')} · ${p.label}`,
          });
        }
      });
      p.report.structuralSignals.forEach((s) => {
        if (
          s.name.toLowerCase().includes(term) ||
          s.description.toLowerCase().includes(term)
        ) {
          out.push({
            kind: 'signal',
            id: s.id,
            presetId: p.id,
            label: s.name,
            sub: `${s.description.slice(0, 60)} · ${p.label}`,
          });
        }
      });
    });

    // System actions — surface only when the query intent matches
    SYSTEM_ACTIONS.forEach((a) => {
      if (a.match.some((m) => m.includes(term) || term.includes(m))) {
        out.push({ kind: 'action', id: a.id, label: a.label, sub: a.sub, action: a.action });
      }
    });

    return out.slice(0, 16);
  }, [q, presets]);

  // keep selection in range
  useEffect(() => {
    if (selected >= hits.length) setSelected(0);
  }, [hits.length, selected]);

  const choose = (h: Hit) => {
    switch (h.kind) {
      case 'entity':
        selectPreset(h.presetId);
        navigate(`/entity/${h.id}`);
        break;
      case 'preset':
        selectPreset(h.id);
        navigate('/investigate');
        break;
      case 'ring':
        selectPreset(h.presetId);
        navigate('/rings');
        break;
      case 'path':
        selectPreset(h.presetId);
        navigate('/investigate');
        break;
      case 'signal':
        selectPreset(h.presetId);
        navigate('/investigate');
        break;
      case 'report':
        navigate(`/reports/${h.id}`);
        break;
      case 'action':
        if (h.action === 'replay-awakening') {
          try {
            sessionStorage.removeItem('shadow:booted');
          } catch {
            /* sessionStorage disabled */
          }
          navigate('/?boot=1');
        }
        break;
    }
    onClose();
  };

  // Global key handlers (also wired for the trigger ⌘K outside)
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelected((i) => Math.min(hits.length - 1, i + 1));
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelected((i) => Math.max(0, i - 1));
      }
      if (e.key === 'Enter' && hits[selected]) {
        e.preventDefault();
        choose(hits[selected]);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, hits, selected]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          className="fixed inset-0 z-[80] flex items-start justify-center pt-[12vh]"
          // click outside dismisses
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) onClose();
          }}
        >
          {/* Backdrop — semi-transparent, never fully obscures graph */}
          <div
            className="absolute inset-0 bg-[rgba(0,0,3,0.55)] backdrop-blur-sm"
            aria-hidden
          />
          <motion.div
            initial={{ y: 14, opacity: 0, scale: 0.98 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 6, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="surface-floating relative w-[640px] max-w-[92vw] overflow-hidden z-10"
          >
            {/* Input */}
            <div className="flex items-center gap-2 px-3.5 h-12 border-b border-[var(--color-line-soft)]">
              <Search className="w-3.5 h-3.5 text-[var(--color-ice-400)] shrink-0" />
              <input
                ref={inputRef}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="search entities, cases, rings, paths, signals, reports…"
                className="flex-1 bg-transparent outline-none text-[14px] text-[var(--color-text-bright)] placeholder:text-[var(--color-text-faint)]"
              />
              <span className="kbd text-[9px]">ESC</span>
              <button
                onClick={onClose}
                className="ml-1 w-6 h-6 inline-flex items-center justify-center rounded-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[rgba(148,163,184,0.06)]"
                aria-label="close"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Results */}
            <div className="max-h-[60vh] overflow-y-auto scroll-tactical">
              {hits.length === 0 ? (
                <div className="px-4 py-8 text-center font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
                  no results · try entity name, case, ring, or signal
                </div>
              ) : (
                hits.map((h, i) => {
                  const meta = HIT_META[h.kind];
                  const Icon = meta.icon;
                  const isSel = i === selected;
                  return (
                    <button
                      key={`${h.kind}_${h.id}_${i}`}
                      onMouseEnter={() => setSelected(i)}
                      onClick={() => choose(h)}
                      className={`w-full text-left flex items-center gap-3 px-3.5 h-11 border-b border-[var(--color-line-soft)] last:border-b-0 ${
                        isSel ? 'bg-[rgba(34,211,238,0.06)]' : 'hover:bg-[rgba(34,211,238,0.04)]'
                      }`}
                    >
                      {h.kind === 'entity' ? (
                        <span
                          className="inline-flex items-center justify-center w-6 h-6 rounded-sm border text-[12px] shrink-0"
                          style={{
                            borderColor: tierColor(h.tier as 'critical'),
                            color: tierColor(h.tier as 'critical'),
                            background: `${tierColor(h.tier as 'critical')}10`,
                          }}
                        >
                          {entityGlyph(h.ekind as 'person')}
                        </span>
                      ) : (
                        <span
                          className="inline-flex items-center justify-center w-6 h-6 rounded-sm border"
                          style={{ borderColor: meta.color, color: meta.color }}
                        >
                          <Icon className="w-3 h-3" strokeWidth={1.4} />
                        </span>
                      )}
                      <span
                        className="font-mono text-[9.5px] tracking-[0.22em] uppercase w-14 shrink-0"
                        style={{ color: meta.color }}
                      >
                        {meta.label}
                      </span>
                      <span className="text-[12px] text-[var(--color-text-bright)] truncate shrink-0 max-w-[40%]">
                        {h.label}
                      </span>
                      <span className="text-[10.5px] text-[var(--color-text-secondary)] truncate flex-1">
                        {h.sub}
                      </span>
                      {isSel && (
                        <span className="kbd text-[9px] shrink-0 flex items-center gap-1">
                          <CornerDownLeft className="w-2.5 h-2.5" />
                          go
                        </span>
                      )}
                      <ArrowRight className="w-3 h-3 text-[var(--color-text-faint)] shrink-0" />
                    </button>
                  );
                })
              )}
            </div>

            {/* Footer hint strip */}
            <div className="px-3.5 h-7 flex items-center gap-3 border-t border-[var(--color-line-soft)] font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              <span className="flex items-center gap-1">
                <span className="kbd text-[8.5px]">↑</span>
                <span className="kbd text-[8.5px]">↓</span>
                navigate
              </span>
              <span className="flex items-center gap-1">
                <span className="kbd text-[8.5px]">↵</span>
                open
              </span>
              <span className="flex items-center gap-1">
                <span className="kbd text-[8.5px]">ESC</span>
                close
              </span>
              <span className="ml-auto">{hits.length} result{hits.length === 1 ? '' : 's'}</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

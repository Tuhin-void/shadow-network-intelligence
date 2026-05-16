import { useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  AlertOctagon,
  CheckCheck,
  CircleDot,
  Eye,
  Sparkles,
  Spline,
  TrendingUp,
  Waves,
  X,
} from 'lucide-react';
import { useIntelStore } from '@/store/intel-store';
import type { PresetSnapshot, RiskTier } from '@/types/intel';
import { cn } from '@/lib/utils';

interface Notif {
  id: string;
  kind: 'ring' | 'hidden' | 'signal' | 'escalation' | 'superiority';
  tier: RiskTier;
  title: string;
  body: string;
  presetId: string;
  presetLabel: string;
  at: number; // unix ms (relative offset)
}

const KIND_META = {
  ring: { icon: CircleDot, label: 'ring detected', color: 'var(--color-rose-400)' },
  hidden: { icon: Spline, label: 'hidden tie', color: 'var(--color-violet-400)' },
  signal: { icon: Waves, label: 'signal', color: 'var(--color-ice-400)' },
  escalation: { icon: TrendingUp, label: 'escalation', color: 'var(--color-amber-400)' },
  superiority: { icon: Sparkles, label: 'graphrag', color: 'var(--color-emerald-400)' },
} as const;

export function NotificationCenter({
  open,
  onClose,
  anchor,
}: {
  open: boolean;
  onClose: () => void;
  anchor: { x: number; y: number };
}) {
  const navigate = useNavigate();
  const { presets, dismissedNotifications, dismissNotification, clearDismissedNotifications } =
    useIntelStore();
  const panelRef = useRef<HTMLDivElement>(null);

  const all = useMemo(() => buildNotifications(presets), [presets]);
  const visible = useMemo(
    () => all.filter((n) => !dismissedNotifications.has(n.id)),
    [all, dismissedNotifications]
  );

  // Group by severity tier
  const grouped = useMemo(() => {
    const order: RiskTier[] = ['critical', 'high', 'medium', 'low'];
    const result: { tier: RiskTier; items: Notif[] }[] = [];
    order.forEach((t) => {
      const items = visible.filter((n) => n.tier === t);
      if (items.length) result.push({ tier: t, items });
    });
    return result;
  }, [visible]);

  // ESC / click outside
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    const onDown = (e: MouseEvent) => {
      // ignore clicks on the bell itself (those toggle externally)
      const target = e.target as HTMLElement | null;
      if (target?.closest('[data-nav-bell="1"]')) return;
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    window.addEventListener('mousedown', onDown);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('mousedown', onDown);
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          ref={panelRef}
          initial={{ opacity: 0, y: -8, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
          className="fixed z-[70] w-[400px] max-w-[92vw] surface-floating overflow-hidden"
          style={{
            top: anchor.y,
            right: Math.max(12, window.innerWidth - anchor.x),
          }}
        >
          <div className="h-9 px-3 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
            <AlertOctagon className="w-3 h-3 text-[var(--color-rose-400)]" />
            <span className="heading-tactical">Notifications</span>
            <span className="chip ml-auto text-[9px]">{visible.length}</span>
            <button
              onClick={() => {
                // dismiss-all = mark every current id as dismissed
                visible.forEach((n) => dismissNotification(n.id));
              }}
              className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-emerald-400)] flex items-center gap-1"
              title="mark all read"
            >
              <CheckCheck className="w-3 h-3" /> clear
            </button>
            <button
              onClick={onClose}
              className="w-5 h-5 inline-flex items-center justify-center rounded-sm hover:bg-[rgba(148,163,184,0.06)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
              aria-label="close"
            >
              <X className="w-3 h-3" />
            </button>
          </div>

          <div className="max-h-[60vh] overflow-y-auto scroll-tactical">
            {visible.length === 0 ? (
              <div className="px-4 py-10 flex flex-col items-center text-center gap-3 text-[var(--color-text-muted)]">
                <CheckCheck className="w-6 h-6 opacity-50" />
                <div className="font-mono text-[10px] tracking-[0.22em] uppercase">
                  inbox zero
                </div>
                {dismissedNotifications.size > 0 && (
                  <button
                    onClick={clearDismissedNotifications}
                    className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-ice-400)] hover:underline"
                  >
                    restore {dismissedNotifications.size} dismissed
                  </button>
                )}
              </div>
            ) : (
              grouped.map(({ tier, items }) => (
                <div key={tier} className="divide-y divide-[var(--color-line-soft)]">
                  <div className="px-3 h-6 flex items-center font-mono text-[9px] tracking-[0.26em] uppercase bg-[rgba(255,255,255,0.012)]">
                    <TierLabel tier={tier} /> · {items.length}
                  </div>
                  {items.map((n) => {
                    const meta = KIND_META[n.kind];
                    const Icon = meta.icon;
                    return (
                      <div
                        key={n.id}
                        className="group px-3 py-2.5 flex items-start gap-3 hover:bg-[rgba(34,211,238,0.04)]"
                      >
                        <span
                          className="inline-flex items-center justify-center w-6 h-6 rounded-sm border shrink-0"
                          style={{
                            borderColor: meta.color,
                            color: meta.color,
                            background: `${meta.color}10`,
                          }}
                        >
                          <Icon className="w-3 h-3" strokeWidth={1.4} />
                        </span>
                        <button
                          onClick={() => {
                            navigate('/alerts');
                            onClose();
                          }}
                          className="flex-1 min-w-0 text-left"
                        >
                          <div className="flex items-center gap-2">
                            <span
                              className="font-mono text-[9px] tracking-[0.22em] uppercase"
                              style={{ color: meta.color }}
                            >
                              {meta.label}
                            </span>
                            <span className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] truncate">
                              {n.presetLabel}
                            </span>
                            <span className="ml-auto font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] shrink-0">
                              {relativeAge(n.at)}
                            </span>
                          </div>
                          <div className="text-[11.5px] text-[var(--color-text-bright)] mt-0.5 truncate">
                            {n.title}
                          </div>
                          <div className="text-[10.5px] text-[var(--color-text-secondary)] mt-0.5 line-clamp-2">
                            {n.body}
                          </div>
                        </button>
                        <button
                          onClick={() => dismissNotification(n.id)}
                          className="w-5 h-5 inline-flex items-center justify-center rounded-sm opacity-0 group-hover:opacity-100 hover:bg-[rgba(148,163,184,0.08)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] shrink-0"
                          aria-label="dismiss"
                          title="dismiss"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              ))
            )}
          </div>

          <div className="h-8 px-3 flex items-center gap-2 border-t border-[var(--color-line-soft)]">
            <button
              onClick={() => {
                navigate('/alerts');
                onClose();
              }}
              className="font-mono text-[9.5px] tracking-[0.26em] uppercase text-[var(--color-ice-400)] hover:underline flex items-center gap-1.5"
            >
              <Eye className="w-3 h-3" />
              open alert center
            </button>
            {dismissedNotifications.size > 0 && (
              <button
                onClick={clearDismissedNotifications}
                className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)]"
              >
                restore {dismissedNotifications.size}
              </button>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function TierLabel({ tier }: { tier: RiskTier }) {
  const color =
    tier === 'critical'
      ? 'var(--color-rose-400)'
      : tier === 'high'
      ? 'var(--color-amber-400)'
      : tier === 'medium'
      ? 'var(--color-ice-400)'
      : 'var(--color-emerald-400)';
  return <span style={{ color }}>{tier}</span>;
}

function relativeAge(ms: number) {
  const ago = ms;
  if (ago < 60_000) return `${Math.round(ago / 1000)}s`;
  if (ago < 3_600_000) return `${Math.round(ago / 60_000)}m`;
  return `${Math.round(ago / 3_600_000)}h`;
}

function buildNotifications(presets: PresetSnapshot[]): Notif[] {
  const out: Notif[] = [];
  let offset = 30_000;
  presets.forEach((p) => {
    p.rings.forEach((r) => {
      out.push({
        id: `n_ring_${r.id}`,
        kind: 'ring',
        tier: r.risk,
        title: r.name,
        body: `${r.signal.replace('_', ' ')} · cohesion ${r.cohesion.toFixed(2)} · ${r.members.length} members`,
        presetId: p.id,
        presetLabel: p.label,
        at: offset,
      });
      offset += 60_000;
    });
    p.hidden.slice(0, 2).forEach((h) => {
      out.push({
        id: `n_hid_${h.id}`,
        kind: 'hidden',
        tier: h.confidence >= 0.85 ? 'high' : h.confidence >= 0.7 ? 'medium' : 'low',
        title: `${h.from} ↔ ${h.to}`,
        body: h.reason,
        presetId: p.id,
        presetLabel: p.label,
        at: offset,
      });
      offset += 120_000;
    });
    p.report.structuralSignals.slice(0, 1).forEach((s) => {
      out.push({
        id: `n_sig_${s.id}`,
        kind: 'signal',
        tier: s.intensity >= 0.85 ? 'high' : s.intensity >= 0.65 ? 'medium' : 'low',
        title: s.name,
        body: s.description,
        presetId: p.id,
        presetLabel: p.label,
        at: offset,
      });
      offset += 180_000;
    });
  });
  // one synthetic "GraphRAG superiority" notice
  out.unshift({
    id: 'n_super_001',
    kind: 'superiority',
    tier: 'high',
    title: 'GraphRAG · 100% structural recall',
    body: 'Benchmark verdict: GraphRAG recovered all relationships vs 33% Vector RAG · 0% Pure LLM',
    presetId: presets[0].id,
    presetLabel: 'benchmark · all cases',
    at: 12_000,
  });
  // critical at top
  const tierRank: Record<RiskTier, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  out.sort((a, b) => {
    const t = tierRank[a.tier] - tierRank[b.tier];
    if (t !== 0) return t;
    return a.at - b.at;
  });
  return out;
}

void cn; // silence unused

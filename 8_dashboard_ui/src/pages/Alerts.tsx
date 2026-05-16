import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIntelStore } from '@/store/intel-store';
import { cn, formatTime } from '@/lib/utils';
import {
  AlertOctagon,
  CircleDot,
  Clock,
  Eye,
  Spline,
  TrendingUp,
  Waves,
} from 'lucide-react';
import type { PresetSnapshot, RiskTier } from '@/types/intel';

type AlertKind = 'ring' | 'hidden' | 'signal' | 'escalation';

interface AlertItem {
  id: string;
  kind: AlertKind;
  tier: RiskTier;
  title: string;
  why: string;
  presetId: string;
  presetLabel: string;
  refs: string[];
  at: string;
}

const KIND_META: Record<
  AlertKind,
  { icon: typeof AlertOctagon; label: string; color: string }
> = {
  ring: { icon: CircleDot, label: 'ring detected', color: 'var(--color-rose-400)' },
  hidden: { icon: Spline, label: 'hidden tie', color: 'var(--color-violet-400)' },
  signal: { icon: Waves, label: 'structural signal', color: 'var(--color-ice-400)' },
  escalation: {
    icon: TrendingUp,
    label: 'suspicion rising',
    color: 'var(--color-amber-400)',
  },
};

const TIER_ORDER: RiskTier[] = ['critical', 'high', 'medium', 'low'];

export function Alerts() {
  const navigate = useNavigate();
  const { presets, selectPreset } = useIntelStore();
  const [tier, setTier] = useState<RiskTier | 'all'>('all');
  const [kind, setKind] = useState<AlertKind | 'all'>('all');

  const all: AlertItem[] = useMemo(() => buildAlerts(presets), [presets]);

  const filtered = useMemo(
    () =>
      all.filter(
        (a) => (tier === 'all' || a.tier === tier) && (kind === 'all' || a.kind === kind)
      ),
    [all, tier, kind]
  );

  const open = (a: AlertItem) => {
    selectPreset(a.presetId);
    navigate('/investigate');
  };

  return (
    <div className="fill overflow-y-auto scroll-tactical">
      <div className="px-6 pt-16 pb-10 mx-auto" style={{ maxWidth: 1480 }}>
        {/* Header */}
        <div className="flex items-end justify-between mb-4">
          <div>
            <div className="font-mono text-[10px] tracking-[0.4em] uppercase text-[var(--color-text-muted)]">
              alerts · live monitoring
            </div>
            <h1 className="text-[22px] font-light tracking-tight text-[var(--color-text-bright)] mt-1">
              {all.length} active findings under review
            </h1>
          </div>
          <div className="font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            updated {new Date().toISOString().slice(11, 19)} UTC
          </div>
        </div>

        {/* Filter strip */}
        <div className="surface px-3 py-2 flex items-center gap-4 mb-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[9.5px] tracking-[0.26em] uppercase text-[var(--color-text-muted)] mr-1">
              tier
            </span>
            <Pill active={tier === 'all'} onClick={() => setTier('all')}>
              all · {all.length}
            </Pill>
            {TIER_ORDER.map((t) => (
              <Pill
                key={t}
                active={tier === t}
                onClick={() => setTier(t)}
                tier={t}
              >
                {t} · {all.filter((a) => a.tier === t).length}
              </Pill>
            ))}
          </div>
          <span className="w-px h-4 bg-[var(--color-line)]" />
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[9.5px] tracking-[0.26em] uppercase text-[var(--color-text-muted)] mr-1">
              kind
            </span>
            <Pill active={kind === 'all'} onClick={() => setKind('all')}>
              all
            </Pill>
            {(Object.keys(KIND_META) as AlertKind[]).map((k) => (
              <Pill key={k} active={kind === k} onClick={() => setKind(k)}>
                {KIND_META[k].label} · {all.filter((a) => a.kind === k).length}
              </Pill>
            ))}
          </div>
        </div>

        {/* List */}
        <div className="surface overflow-hidden">
          <div className="grid grid-cols-[40px_120px_minmax(0,1.4fr)_minmax(0,1fr)_100px_100px] px-3 h-8 items-center border-b border-[var(--color-line-soft)] font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            <span />
            <span>tier</span>
            <span>finding</span>
            <span>case</span>
            <span>kind</span>
            <span className="text-right">received</span>
          </div>
          <div className="divide-y divide-[var(--color-line-soft)]">
            {filtered.length === 0 ? (
              <div className="px-3 py-8 text-center font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
                no alerts match the filter
              </div>
            ) : (
              filtered.slice(0, 80).map((a) => {
                const meta = KIND_META[a.kind];
                const Icon = meta.icon;
                return (
                  <button
                    key={a.id}
                    onClick={() => open(a)}
                    className="w-full grid grid-cols-[40px_120px_minmax(0,1.4fr)_minmax(0,1fr)_100px_100px] px-3 py-2.5 items-center hover:bg-[rgba(244,63,94,0.04)] text-left"
                  >
                    <span
                      className="inline-flex items-center justify-center w-7 h-7 rounded-sm border"
                      style={{
                        borderColor: meta.color,
                        color: meta.color,
                        background: `${meta.color}10`,
                      }}
                    >
                      <Icon className="w-3.5 h-3.5" strokeWidth={1.4} />
                    </span>
                    <TierChip tier={a.tier} />
                    <div className="min-w-0">
                      <div className="text-[12px] text-[var(--color-text-bright)] truncate">
                        {a.title}
                      </div>
                      <div className="text-[10.5px] text-[var(--color-text-secondary)] truncate">
                        {a.why}
                      </div>
                    </div>
                    <div className="text-[11px] text-[var(--color-text-secondary)] truncate">
                      {a.presetLabel}
                    </div>
                    <div
                      className="font-mono text-[9.5px] tracking-[0.18em] uppercase"
                      style={{ color: meta.color }}
                    >
                      {meta.label}
                    </div>
                    <div className="font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] text-right flex items-center justify-end gap-1.5">
                      <Clock className="w-2.5 h-2.5" />
                      {formatTime(a.at)}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        <div className="font-mono text-[9px] tracking-[0.32em] uppercase text-[var(--color-text-faint)] mt-4 flex items-center gap-2">
          <Eye className="w-3 h-3" />
          click any alert to open its investigation
        </div>
      </div>
    </div>
  );
}

function Pill({
  children,
  active,
  onClick,
  tier,
}: {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
  tier?: RiskTier;
}) {
  const tierColorVar =
    tier === 'critical'
      ? 'var(--color-rose-400)'
      : tier === 'high'
      ? 'var(--color-amber-400)'
      : tier === 'medium'
      ? 'var(--color-ice-400)'
      : tier === 'low'
      ? 'var(--color-emerald-400)'
      : 'var(--color-ice-400)';
  return (
    <button
      onClick={onClick}
      className={cn(
        'h-6 px-2.5 inline-flex items-center rounded-sm border font-mono text-[9.5px] tracking-[0.22em] uppercase transition-colors',
        active
          ? 'text-[var(--color-text-bright)]'
          : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
      )}
      style={{
        borderColor: active ? tierColorVar : 'var(--color-line-soft)',
        background: active ? `${tierColorVar}10` : 'transparent',
      }}
    >
      {children}
    </button>
  );
}

function TierChip({ tier }: { tier: RiskTier }) {
  const color =
    tier === 'critical'
      ? 'var(--color-rose-400)'
      : tier === 'high'
      ? 'var(--color-amber-400)'
      : tier === 'medium'
      ? 'var(--color-ice-400)'
      : 'var(--color-emerald-400)';
  return (
    <span
      className="inline-flex items-center gap-1 px-2 h-5 rounded-sm border font-mono text-[9.5px] tracking-[0.22em] uppercase w-fit"
      style={{ color, borderColor: `${color}55`, background: `${color}10` }}
    >
      <span className="inline-block w-1 h-1 rounded-full" style={{ background: color }} />
      {tier}
    </span>
  );
}

function buildAlerts(presets: PresetSnapshot[]): AlertItem[] {
  const out: AlertItem[] = [];
  const now = Date.now();
  presets.forEach((p, pi) => {
    p.rings.forEach((r, i) => {
      out.push({
        id: `${p.id}_ring_${r.id}`,
        kind: 'ring',
        tier: r.risk,
        title: r.name,
        why: `${r.signal.replace('_', ' ')} · cohesion ${r.cohesion.toFixed(2)} · ${r.members.length} members`,
        presetId: p.id,
        presetLabel: p.label,
        refs: [r.id],
        at: new Date(now - pi * 600000 - i * 90000).toISOString(),
      });
    });
    p.hidden.forEach((h, i) => {
      out.push({
        id: `${p.id}_hid_${h.id}`,
        kind: 'hidden',
        tier: h.confidence >= 0.85 ? 'high' : h.confidence >= 0.7 ? 'medium' : 'low',
        title: `${h.from} → ${h.to}`,
        why: h.reason,
        presetId: p.id,
        presetLabel: p.label,
        refs: [h.id],
        at: new Date(now - pi * 600000 - 240000 - i * 70000).toISOString(),
      });
    });
    p.report.structuralSignals.forEach((s, i) => {
      out.push({
        id: `${p.id}_sig_${s.id}`,
        kind: 'signal',
        tier: s.intensity >= 0.85 ? 'high' : s.intensity >= 0.65 ? 'medium' : 'low',
        title: s.name,
        why: s.description,
        presetId: p.id,
        presetLabel: p.label,
        refs: [s.id],
        at: new Date(now - pi * 600000 - 480000 - i * 50000).toISOString(),
      });
    });
    // suspicion escalations from preset.stream
    p.stream
      .filter((e) => e.kind === 'suspicion.escalated')
      .forEach((e, i) => {
        out.push({
          id: `${p.id}_esc_${e.id}`,
          kind: 'escalation',
          tier: e.severity ?? 'high',
          title: e.title,
          why: `severity ${e.severity ?? 'high'}`,
          presetId: p.id,
          presetLabel: p.label,
          refs: e.refs ?? [],
          at: new Date(now - pi * 600000 - 720000 - i * 30000).toISOString(),
        });
      });
  });
  // Sort by tier then time desc
  const tierRank: Record<RiskTier, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  out.sort((a, b) => {
    const t = tierRank[a.tier] - tierRank[b.tier];
    if (t !== 0) return t;
    return b.at.localeCompare(a.at);
  });
  return out;
}

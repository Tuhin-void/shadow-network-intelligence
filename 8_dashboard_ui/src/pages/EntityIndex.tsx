import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIntelStore } from '@/store/intel-store';
import { cn, entityGlyph, riskToTier, tierColor } from '@/lib/utils';
import { Network, Search, ShieldAlert } from 'lucide-react';
import type { Entity, EntityKind, PresetSnapshot } from '@/types/intel';
import { RiskBadge } from '@/components/shared/RiskBadge';

interface EntityRow extends Entity {
  presetId: string;
  presetLabel: string;
}

const KIND_FILTERS: Array<{ id: 'all' | EntityKind; label: string }> = [
  { id: 'all', label: 'all' },
  { id: 'person', label: 'people' },
  { id: 'shell_company', label: 'shells' },
  { id: 'company', label: 'companies' },
  { id: 'wallet', label: 'wallets' },
  { id: 'account', label: 'accounts' },
  { id: 'device', label: 'devices' },
  { id: 'address', label: 'addresses' },
  { id: 'transaction', label: 'transactions' },
];

export function EntityIndex() {
  const navigate = useNavigate();
  const { presets, selectPreset } = useIntelStore();
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState<(typeof KIND_FILTERS)[number]['id']>('all');

  const all: EntityRow[] = useMemo(() => {
    return presets.flatMap((p) =>
      p.graph.entities.map((e) => ({
        ...e,
        presetId: p.id,
        presetLabel: p.label,
      }))
    );
  }, [presets]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    return all
      .filter((e) => (kind === 'all' ? true : e.kind === kind))
      .filter((e) => {
        if (!term) return true;
        return (
          e.label.toLowerCase().includes(term) ||
          e.id.toLowerCase().includes(term) ||
          e.presetLabel.toLowerCase().includes(term) ||
          (e.flags ?? []).some((f) => f.toLowerCase().includes(term))
        );
      })
      .sort((a, b) => b.risk - a.risk);
  }, [all, query, kind]);

  const counts = useMemo(() => {
    const acc: Record<string, number> = { all: all.length };
    all.forEach((e) => {
      acc[e.kind] = (acc[e.kind] ?? 0) + 1;
    });
    return acc;
  }, [all]);

  const openEntity = (presetId: string, entityId: string) => {
    selectPreset(presetId);
    navigate(`/entity/${entityId}`);
  };

  return (
    <div className="fill overflow-y-auto scroll-tactical">
      <div className="px-6 pt-16 pb-10 mx-auto" style={{ maxWidth: 1480 }}>
        {/* Header */}
        <div className="flex items-end justify-between mb-4">
          <div>
            <div className="font-mono text-[10px] tracking-[0.4em] uppercase text-[var(--color-text-muted)]">
              entities · dossier index
            </div>
            <h1 className="text-[22px] font-light tracking-tight text-[var(--color-text-bright)] mt-1">
              {all.length} entities under coverage
            </h1>
          </div>
        </div>

        {/* Toolbar */}
        <div className="surface px-3 py-2 flex items-center gap-3 mb-2.5">
          <Search className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="filter by id, label, flag, or case"
            className="flex-1 bg-transparent outline-none text-[12px] text-[var(--color-text-bright)] placeholder:text-[var(--color-text-faint)] min-w-0"
          />
          <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] shrink-0">
            {filtered.length} match
          </span>
        </div>

        {/* Kind filter strip */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          {KIND_FILTERS.map((f) => {
            const isActive = f.id === kind;
            const n = counts[f.id] ?? 0;
            return (
              <button
                key={f.id}
                onClick={() => setKind(f.id)}
                className={cn(
                  'h-6 px-2.5 inline-flex items-center gap-1.5 rounded-sm border font-mono text-[9.5px] tracking-[0.22em] uppercase transition-colors',
                  isActive
                    ? 'border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)]'
                    : 'border-[var(--color-line-soft)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
                )}
              >
                <span>{f.label}</span>
                <span className="text-[var(--color-text-faint)]">{n}</span>
              </button>
            );
          })}
        </div>

        {/* List */}
        <div className="surface overflow-hidden">
          <div className="grid grid-cols-[36px_minmax(0,1.4fr)_minmax(0,1fr)_120px_120px_90px] px-3 h-8 items-center border-b border-[var(--color-line-soft)] font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            <span />
            <span>entity</span>
            <span>case</span>
            <span>kind</span>
            <span>flags</span>
            <span className="text-right">risk</span>
          </div>
          <div className="divide-y divide-[var(--color-line-soft)]">
            {filtered.length === 0 ? (
              <div className="px-3 py-8 text-center font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
                no matching entities
              </div>
            ) : (
              filtered.slice(0, 80).map((e) => (
                <button
                  key={`${e.presetId}_${e.id}`}
                  onClick={() => openEntity(e.presetId, e.id)}
                  className="w-full grid grid-cols-[36px_minmax(0,1.4fr)_minmax(0,1fr)_120px_120px_90px] px-3 py-2 items-center hover:bg-[rgba(34,211,238,0.04)] transition-colors text-left"
                >
                  <span
                    className="inline-flex items-center justify-center w-6 h-6 rounded-sm border text-[11px]"
                    style={{
                      borderColor: tierColor(e.tier),
                      color: tierColor(e.tier),
                      background: `${tierColor(e.tier)}10`,
                    }}
                  >
                    {entityGlyph(e.kind)}
                  </span>
                  <div className="min-w-0">
                    <div className="text-[12px] text-[var(--color-text-bright)] truncate">
                      {e.label}
                    </div>
                    <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] truncate">
                      {e.id}
                    </div>
                  </div>
                  <div className="text-[11px] text-[var(--color-text-secondary)] truncate">
                    {e.presetLabel}
                  </div>
                  <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] truncate">
                    {e.kind.replace('_', ' ')}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {(e.flags ?? []).slice(0, 1).map((f) => (
                      <span
                        key={f}
                        className="chip text-[8.5px]"
                        style={{
                          borderColor: 'rgba(244,63,94,0.4)',
                          color: 'var(--color-rose-400)',
                        }}
                      >
                        <ShieldAlert className="w-2.5 h-2.5" />
                        {f}
                      </span>
                    ))}
                    {(e.flags ?? []).length > 1 && (
                      <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
                        +{(e.flags ?? []).length - 1}
                      </span>
                    )}
                  </div>
                  <div className="flex justify-end">
                    <RiskBadge score={e.risk} tier={riskToTier(e.risk)} size="xs" />
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {filtered.length > 80 && (
          <div className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] mt-2 px-1">
            showing first 80 of {filtered.length} · refine the filter to narrow
          </div>
        )}

        <div className="font-mono text-[9px] tracking-[0.32em] uppercase text-[var(--color-text-faint)] mt-5 flex items-center gap-2">
          <Network className="w-3 h-3" />
          click any entity to open its dossier
        </div>
      </div>
    </div>
  );
}

// avoid unused-import lint when EntityKind isn't directly referenced in JSX
void ({} as PresetSnapshot);

import { useMemo, useState } from 'react';
import { useIntelStore } from '@/store/intel-store';
import { cn, entityGlyph, tierColor } from '@/lib/utils';
import { Crosshair, Search, ArrowRight, CornerDownLeft } from 'lucide-react';

/**
 * Tactical command bar — analyst's primary research input.
 * Not a chatbot: this is an entity / signal / preset query that drives
 * graph focus + investigation seeding.
 */
export function CommandBar() {
  const { active, selectPreset, selectEntity, presets, startStream } = useIntelStore();
  const [q, setQ] = useState('');

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
      const score = [p.label, p.id, ...p.tags, p.description]
        .join(' ')
        .toLowerCase()
        .includes(term);
      if (score) {
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
      if (s.name.toLowerCase().includes(term) || s.description.toLowerCase().includes(term)) {
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
    if (s.type === 'entity') {
      selectEntity(s.id);
    }
    setQ('');
  };

  return (
    <div className="relative">
      <div className="panel-soft flex items-center gap-2 px-2.5 h-8 focus-within:border-[rgba(34,211,238,0.4)] transition-colors">
        <Crosshair className="w-3 h-3 text-[var(--color-ice-400)]" />
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-text-muted)] shrink-0">
          target
        </span>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && suggestions[0]) apply(suggestions[0]);
            if (e.key === 'Escape') setQ('');
          }}
          placeholder="entity, preset, or signal — e.g. obsidian, ring, p_alaric"
          className="flex-1 min-w-0 bg-transparent outline-none text-[12px] text-[var(--color-text-bright)] placeholder:text-[var(--color-text-faint)]"
        />
        <span className="kbd hidden md:inline-flex">
          <CornerDownLeft className="w-2.5 h-2.5" /> ENTER
        </span>
      </div>
      {suggestions.length > 0 && (
        <div className="absolute left-0 right-0 top-full mt-1 z-30 panel divide-y divide-[var(--color-line-soft)] shadow-xl">
          {suggestions.map((s, i) => (
            <button
              key={`${s.type}_${s.id}`}
              onClick={() => apply(s)}
              className={cn(
                'w-full flex items-center gap-2 px-2.5 h-8 text-left',
                'hover:bg-[rgba(34,211,238,0.05)]',
                i === 0 && 'bg-[rgba(34,211,238,0.04)]'
              )}
            >
              {s.type === 'entity' && (
                <span
                  className="inline-flex items-center justify-center w-5 h-5 rounded-sm border text-[10px]"
                  style={{
                    borderColor: tierColor(s.tier as 'critical') ?? 'var(--color-line)',
                    color: tierColor(s.tier as 'critical') ?? 'var(--color-text-primary)',
                  }}
                >
                  {entityGlyph(s.kind as 'person')}
                </span>
              )}
              {s.type === 'preset' && (
                <Search className="w-3 h-3 text-[var(--color-violet-400)]" />
              )}
              {s.type === 'signal' && (
                <ArrowRight className="w-3 h-3 text-[var(--color-amber-400)]" />
              )}
              <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] w-14">
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
    </div>
  );
}

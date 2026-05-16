import { useIntelStore } from '@/store/intel-store';
import { cn } from '@/lib/utils';
import {
  Eye,
  CircleDot,
  Spline,
  GitBranch,
  Flame,
  Layers,
} from 'lucide-react';
import type { ComponentType } from 'react';

type FocusMode = 'overview' | 'rings' | 'hidden' | 'paths' | 'risk';

const MODES: Array<{ id: FocusMode; label: string; icon: ComponentType<{ className?: string }> }> = [
  { id: 'overview', label: 'Overview', icon: Eye },
  { id: 'risk', label: 'Risk heat', icon: Flame },
  { id: 'rings', label: 'Rings', icon: CircleDot },
  { id: 'hidden', label: 'Hidden links', icon: Spline },
  { id: 'paths', label: 'Paths', icon: GitBranch },
];

export function GraphHud() {
  const { focusMode, setFocusMode, active, discoveredEntities, traversedEdges, focusModeOn, setFocusModeOn } =
    useIntelStore();

  if (focusModeOn) {
    // Minimal HUD when in focus mode — only "exit focus" affordance
    return (
      <div className="absolute top-3 right-3 z-30 pointer-events-auto">
        <button
          onClick={() => setFocusModeOn(false)}
          className="surface-floating h-7 px-2.5 inline-flex items-center gap-1.5 rounded-full text-[var(--color-violet-400)] font-mono text-[9.5px] tracking-[0.26em] uppercase hover:bg-[rgba(168,85,247,0.06)]"
          title="exit focus · F"
        >
          <Layers className="w-3 h-3" />
          focus · F
        </button>
      </div>
    );
  }

  return (
    <div className="absolute top-3 left-3 right-3 flex items-start gap-3 pointer-events-none">
      {/* Focus modes */}
      <div className="panel flex items-center p-0.5 pointer-events-auto">
        {MODES.map((m) => {
          const Icon = m.icon;
          const isActive = focusMode === m.id;
          return (
            <button
              key={m.id}
              onClick={() => setFocusMode(m.id)}
              className={cn(
                'h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-[0.16em] rounded-[3px]',
                isActive
                  ? 'bg-[rgba(34,211,238,0.12)] text-[var(--color-ice-400)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
              )}
            >
              <Icon className="w-3 h-3" />
              <span>{m.label}</span>
            </button>
          );
        })}
      </div>

      <div className="ml-auto flex flex-col items-end gap-2">
        <div className="panel-soft flex items-center gap-2 px-2.5 h-7 pointer-events-auto">
          <Layers className="w-3 h-3 text-[var(--color-text-muted)]" />
          <span className="font-mono text-[10px] text-[var(--color-text-secondary)]">
            {discoveredEntities.size}
            <span className="text-[var(--color-text-muted)]">/{active.graph.entities.length}</span>{' '}
            nodes
          </span>
          <span className="w-px h-3 bg-[var(--color-line)] mx-1" />
          <span className="font-mono text-[10px] text-[var(--color-text-secondary)]">
            {traversedEdges.size}
            <span className="text-[var(--color-text-muted)]">/{active.graph.edges.length}</span>{' '}
            edges
          </span>
        </div>
      </div>
    </div>
  );
}

export function GraphLegend() {
  return (
    <div className="absolute bottom-3 left-3 panel p-2 space-y-1.5 pointer-events-auto">
      <div className="label-tactical mb-1">Legend</div>
      <LegendRow color="#f43f5e" label="critical" />
      <LegendRow color="#f59e0b" label="high" />
      <LegendRow color="#22d3ee" label="medium" />
      <LegendRow color="#10b981" label="low" />
      <div className="divider-h my-1.5" />
      <LegendRow color="#a855f7" label="hidden link" dashed />
      <LegendRow color="#fbbf24" label="path edge" thick />
    </div>
  );
}

function LegendRow({
  color,
  label,
  dashed,
  thick,
}: {
  color: string;
  label: string;
  dashed?: boolean;
  thick?: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="inline-block w-5"
        style={{
          height: thick ? 3 : 2,
          background: dashed
            ? `repeating-linear-gradient(90deg, ${color} 0 4px, transparent 4px 7px)`
            : color,
          borderRadius: 2,
        }}
      />
      <span className="font-mono text-[10px] text-[var(--color-text-secondary)] uppercase tracking-wider">
        {label}
      </span>
    </div>
  );
}

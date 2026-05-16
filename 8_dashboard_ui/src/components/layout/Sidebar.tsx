import { NavLink } from 'react-router-dom';
import {
  Network,
  Swords,
  Archive,
  Radar,
  ShieldAlert,
  Cpu,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useIntelStore } from '@/store/intel-store';
import { StatusIndicator } from '@/components/shared/StatusIndicator';

const NAV = [
  { to: '/', label: 'Investigation', icon: Network, glyph: '01' },
  { to: '/benchmark', label: 'Benchmark', icon: Swords, glyph: '02' },
  { to: '/sessions', label: 'Session Vault', icon: Archive, glyph: '03' },
];

export function Sidebar() {
  const { active, presets, activePresetId, selectPreset, streamingPhase, progress } =
    useIntelStore();

  return (
    <aside className="w-[240px] shrink-0 h-full flex flex-col border-r border-[var(--color-line)] bg-[var(--color-graphite-950)] relative">
      {/* Logo */}
      <div className="h-12 px-4 flex items-center gap-3 border-b border-[var(--color-line-soft)]">
        <div className="relative flex items-center justify-center w-7 h-7 rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.08)]">
          <Radar className="w-3.5 h-3.5 text-[var(--color-ice-400)]" strokeWidth={1.5} />
          <span className="absolute inset-0 rounded-sm anim-pulse-ring bg-[rgba(34,211,238,0.4)] opacity-30" />
        </div>
        <div className="flex flex-col leading-tight min-w-0">
          <span className="text-[11px] font-semibold tracking-[0.22em] text-[var(--color-text-bright)]">
            SHADOW
          </span>
          <span className="text-[9px] font-mono uppercase tracking-[0.22em] text-[var(--color-text-muted)]">
            Network Intelligence
          </span>
        </div>
      </div>

      {/* Run telemetry */}
      <div className="px-4 py-3 border-b border-[var(--color-line-soft)] space-y-2">
        <div className="flex items-center justify-between">
          <span className="label-tactical">Run</span>
          <StatusIndicator
            status={
              streamingPhase === 'streaming'
                ? 'streaming'
                : streamingPhase === 'complete'
                ? 'complete'
                : 'idle'
            }
            label={
              streamingPhase === 'streaming'
                ? 'STREAMING'
                : streamingPhase === 'complete'
                ? 'COMPLETE'
                : 'STANDBY'
            }
          />
        </div>
        <div className="h-1 rounded-full bg-[var(--color-graphite-800)] overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[var(--color-ice-500)] to-[var(--color-violet-500)] transition-[width] duration-500"
            style={{ width: `${Math.round(progress * 100)}%` }}
          />
        </div>
        <div className="font-mono text-[10px] text-[var(--color-text-muted)] flex justify-between">
          <span>{active.label}</span>
          <span>{Math.round(progress * 100)}%</span>
        </div>
      </div>

      {/* Workspaces nav */}
      <nav className="px-2 py-3 space-y-0.5">
        <div className="label-tactical px-2 pb-2">Workspaces</div>
        {NAV.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'group relative flex items-center gap-3 px-2.5 h-8 rounded-sm text-[12px] transition-colors',
                  isActive
                    ? 'text-[var(--color-text-bright)] bg-[rgba(34,211,238,0.08)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[rgba(148,163,184,0.04)]'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={cn(
                      'absolute left-0 top-1 bottom-1 w-[2px] rounded-r-sm transition-opacity',
                      isActive
                        ? 'bg-[var(--color-ice-400)] opacity-100'
                        : 'bg-transparent opacity-0'
                    )}
                  />
                  <span className="font-mono text-[9px] text-[var(--color-text-faint)] w-5">
                    {item.glyph}
                  </span>
                  <Icon className="w-3.5 h-3.5" strokeWidth={1.5} />
                  <span className="flex-1 truncate">{item.label}</span>
                  {isActive && (
                    <ChevronRight className="w-3 h-3 text-[var(--color-ice-400)]" />
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div className="divider-h mx-3" />

      {/* Demo presets */}
      <div className="px-3 py-3 flex-1 min-h-0 flex flex-col">
        <div className="flex items-center justify-between px-1 pb-2">
          <span className="label-tactical">Demo presets</span>
          <span className="chip">{presets.length}</span>
        </div>
        <div className="space-y-1 overflow-y-auto scroll-tactical pr-1">
          {presets.map((p) => {
            const isActive = p.id === activePresetId;
            return (
              <button
                key={p.id}
                onClick={() => selectPreset(p.id)}
                className={cn(
                  'group w-full text-left px-2 py-2 rounded-sm transition-colors border',
                  isActive
                    ? 'border-[rgba(34,211,238,0.32)] bg-[rgba(34,211,238,0.05)]'
                    : 'border-transparent hover:bg-[rgba(148,163,184,0.04)]'
                )}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      'w-1 h-1 rounded-full',
                      isActive ? 'bg-[var(--color-ice-400)]' : 'bg-[var(--color-text-faint)]'
                    )}
                  />
                  <span
                    className={cn(
                      'text-[11px] font-medium truncate',
                      isActive ? 'text-[var(--color-text-bright)]' : 'text-[var(--color-text-secondary)]'
                    )}
                  >
                    {p.label}
                  </span>
                </div>
                <div className="font-mono text-[9px] text-[var(--color-text-muted)] truncate pl-3">
                  {p.tags.join(' · ')}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="px-3 py-2.5 border-t border-[var(--color-line-soft)] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="w-3 h-3 text-[var(--color-text-muted)]" strokeWidth={1.5} />
          <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
            graph-rag v0.94
          </span>
        </div>
        <ShieldAlert className="w-3.5 h-3.5 text-[var(--color-text-muted)]" strokeWidth={1.5} />
      </div>
    </aside>
  );
}

import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Brain,
  Network,
  Scale,
  Target,
  Zap,
} from 'lucide-react';
import type { BackendEnvironmentState } from '@/lib/api-client';

/**
 * SourceHandoffStrip — operational transitions from the Sources page into
 * the rest of the platform. Renders ONLY when the environment is
 * investigation-ready (env.investigation_ready=true), so we never offer
 * a path that would land on a broken surface.
 *
 * The four real handoffs:
 *   • investigate (with a default ranked-suspects seed)
 *   • open topology (the graph workstation, no seed → user's last session)
 *   • benchmark this environment
 *   • launch structural query (a fraud-ring discovery seed)
 *
 * Hard contracts:
 *   • No fake actions. If env isn't ready, render nothing.
 *   • The seed queries are stable, well-formed analyst questions —
 *     never AI-generated.
 *   • Handoff uses /investigate?q=<seed> which the Manual page reads
 *     once on mount.
 */
export function SourceHandoffStrip({ env }: { env: BackendEnvironmentState | null }) {
  const navigate = useNavigate();
  if (!env || !env.investigation_ready) return null;

  const total = env.total_vertices ?? 0;
  const kind = env.environment_kind ?? 'sample';

  const go = (path: string) => navigate(path);
  const investigate = (q: string) => navigate(`/investigate?q=${encodeURIComponent(q)}`);

  return (
    <section className="surface px-3 py-2 flex items-center gap-3 flex-wrap">
      <div className="flex items-center gap-2 shrink-0">
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-emerald-400)] anim-drift" />
        <span className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-emerald-400)]">
          environment ready
        </span>
        <span className="text-[var(--color-text-ghost)]">·</span>
        <span className="font-mono text-[10.5px] text-[var(--color-text-bright)]">
          {kind} · {total.toLocaleString()} vertices
        </span>
      </div>

      <div className="h-3 w-px bg-[var(--color-line-soft)] hidden md:block" />

      <div className="flex items-center gap-1.5 flex-wrap ml-auto">
        <HandoffButton
          icon={Target}
          label="investigate"
          tone="ice"
          onClick={() => investigate('who is the most suspected')}
          title="run a ranked-suspects investigation against this environment"
        />
        <HandoffButton
          icon={Zap}
          label="structural query"
          tone="emerald"
          onClick={() => investigate('show hidden fraud rings')}
          title="surface fraud rings and member entities via graph traversal"
        />
        <HandoffButton
          icon={Network}
          label="open topology"
          tone="violet"
          onClick={() => go('/investigate')}
          title="open the graph workstation"
        />
        <HandoffButton
          icon={Scale}
          label="benchmark"
          tone="amber"
          onClick={() => go('/benchmark')}
          title="run 3-pipeline comparison against this environment"
        />
        <HandoffButton
          icon={Brain}
          label="reasoning"
          tone="rose"
          onClick={() => go('/autopilot')}
          title="run the cognitive autopilot against this environment"
        />
      </div>
    </section>
  );
}

function HandoffButton({
  icon: Icon,
  label,
  tone,
  onClick,
  title,
}: {
  icon: typeof Target;
  label: string;
  tone: 'ice' | 'emerald' | 'amber' | 'violet' | 'rose';
  onClick: () => void;
  title: string;
}) {
  const color =
    tone === 'emerald' ? 'var(--color-emerald-400)' :
    tone === 'amber'   ? 'var(--color-amber-400)' :
    tone === 'violet'  ? 'var(--color-violet-400)' :
    tone === 'rose'    ? 'var(--color-rose-400)' :
    'var(--color-ice-400)';
  return (
    <button
      onClick={onClick}
      title={title}
      className="h-6 px-2 inline-flex items-center gap-1 rounded-sm border transition-colors hover:bg-[rgba(34,211,238,0.04)]"
      style={{ borderColor: `${color}55`, color }}
    >
      <Icon className="w-3 h-3" />
      <span className="font-mono text-[9px] tracking-[0.22em] uppercase">{label}</span>
      <ArrowRight className="w-2.5 h-2.5 opacity-60" />
    </button>
  );
}

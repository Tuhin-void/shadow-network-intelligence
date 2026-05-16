import { useIntelStore } from '@/store/intel-store';
import { Panel } from '@/components/shared/Panel';
import { Atmosphere } from '@/components/shared/Atmosphere';
import { cn, formatTime } from '@/lib/utils';
import {
  Archive,
  Rewind,
  GitBranch,
  Clock,
  Activity,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/layout/PageHeader';
import type { ComponentType } from 'react';

const ReplayIcon: ComponentType<{ className?: string }> = Rewind;

export function SessionVault() {
  const { sessions, presets, replaySession } = useIntelStore();
  const navigate = useNavigate();

  return (
    <div className="fill bg-[var(--color-void)] overflow-hidden text-[var(--color-text-primary)]">
      <Atmosphere density={28} intensity={0.55} />

      <div className="absolute top-[56px] inset-x-0 z-10">
        <PageHeader
          icon={Archive}
          eyebrow="sessions"
          title="Analyst vault"
          meta={`${sessions.length} archived`}
        />
      </div>

      <div
        className="absolute top-[100px] inset-x-0 bottom-0 grid gap-3 p-3"
        style={{ gridTemplateColumns: '1fr 360px' }}
      >
        <Panel
          title="Sessions"
          badge={<span className="chip">{sessions.length}</span>}
          scrollable
          className="min-h-0"
        >
          {sessions.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-[12px] text-[var(--color-text-muted)] gap-3">
              <Archive className="w-7 h-7 opacity-50" />
              <span className="font-mono uppercase tracking-[0.32em]">
                no sessions yet
              </span>
              <button
                onClick={() => navigate('/autopilot')}
                className="h-8 px-3 inline-flex items-center gap-2 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.05)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)]"
              >
                <Activity className="w-3 h-3" />
                launch autopilot
              </button>
            </div>
          ) : (
            <div className="p-2 space-y-1.5">
              {sessions.map((s) => {
                const preset = presets.find((p) => p.id === s.presetId);
                return (
                  <div
                    key={s.id}
                    className="surface px-3 py-2.5 flex items-center gap-3 hover:border-[var(--color-line-strong)] transition-colors"
                  >
                    <div className="flex flex-col items-center gap-1 w-12 shrink-0">
                      <div className="font-mono text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">
                        {s.id}
                      </div>
                      <span
                        className={cn(
                          'w-1.5 h-1.5 rounded-full',
                          s.status === 'complete'
                            ? 'bg-[var(--color-emerald-400)]'
                            : 'bg-[var(--color-ice-400)]'
                        )}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[12px] font-medium text-[var(--color-text-bright)] truncate">
                        {s.title}
                      </div>
                      <div className="flex items-center gap-3 mt-0.5 font-mono text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">
                        <span>{preset?.label}</span>
                        <span>·</span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" />
                          {formatTime(s.startedAt)}
                        </span>
                        <span>·</span>
                        <span>{s.events.length} events</span>
                        <span>·</span>
                        <span>{s.analyst}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        replaySession(s.id);
                        navigate('/investigate');
                      }}
                      className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-[0.26em] rounded-sm border border-[var(--color-line)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.06)]"
                    >
                      <ReplayIcon className="w-3 h-3" />
                      REPLAY
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </Panel>

        <Panel title="About sessions" className="min-h-0">
          <div className="p-3 space-y-3 text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
            <p>
              Each investigation produces an immutable session — a complete event
              stream, topology snapshot, and 9-section report.
            </p>
            <ul className="space-y-2">
              <Bullet icon={Activity} text="Full SSE event tape preserved" />
              <Bullet icon={GitBranch} text="Replay reconstructs topology + sections in order" />
              <Bullet icon={Archive} text="Sessions are local-only in this prototype" />
            </ul>
            <div className="divider-h" />
            <p className="font-mono text-[10px] text-[var(--color-text-muted)] uppercase tracking-[0.26em]">
              backend contract · /sessions/&lt;id&gt;.jsonl
            </p>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Bullet({
  icon: Icon,
  text,
}: {
  icon: ComponentType<{ className?: string }>;
  text: string;
}) {
  return (
    <li className="flex items-start gap-2">
      <Icon className="w-3 h-3 text-[var(--color-ice-400)] mt-0.5 shrink-0" />
      <span>{text}</span>
    </li>
  );
}

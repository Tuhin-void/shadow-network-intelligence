import { useNavigate, useParams } from 'react-router-dom';
import { useIntelStore } from '@/store/intel-store';
import { cn, entityGlyph, tierColor } from '@/lib/utils';
import {
  ArrowLeft,
  CircleDot,
  FileText,
  GitBranch,
  Printer,
  ShieldAlert,
  Sparkles,
  Spline,
} from 'lucide-react';
import type { PresetSnapshot } from '@/types/intel';
import { useEffect } from 'react';

/**
 * Reports — classified dossier list + per-case dossier view.
 *
 * /reports          → index list of all 8 cases as dossier covers
 * /reports/:id      → full dossier page for a single case
 */
export function Reports() {
  const params = useParams<{ id?: string }>();
  return params.id ? <Dossier id={params.id} /> : <DossierIndex />;
}

/* -------------------------------------------------------------------------- */

function DossierIndex() {
  const navigate = useNavigate();
  const { presets } = useIntelStore();
  return (
    <div className="fill overflow-y-auto scroll-tactical">
      <div className="px-6 pt-16 pb-10 mx-auto" style={{ maxWidth: 1480 }}>
        <div className="flex items-end justify-between mb-4">
          <div>
            <div className="font-mono text-[10px] tracking-[0.4em] uppercase text-[var(--color-text-muted)]">
              reports · classified dossiers
            </div>
            <h1 className="text-[22px] font-light tracking-tight text-[var(--color-text-bright)] mt-1">
              {presets.length} cases sealed
            </h1>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {presets.map((p) => (
            <button
              key={p.id}
              onClick={() => navigate(`/reports/${p.id}`)}
              className="text-left surface relative overflow-hidden hover:border-[rgba(34,211,238,0.3)] transition-colors"
            >
              <div className="fill tactical-grid-fine opacity-30 pointer-events-none" />
              <div className="relative px-4 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <FileText className="w-3 h-3 text-[var(--color-ice-400)]" />
                  <span className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
                    dossier · 0x{p.id.slice(0, 4).toUpperCase()}
                  </span>
                  <span
                    className="ml-auto px-2 py-[1px] rounded-sm font-mono text-[8.5px] tracking-[0.32em] uppercase border"
                    style={{
                      color: 'var(--color-rose-400)',
                      borderColor: 'rgba(244,63,94,0.4)',
                      background: 'rgba(244,63,94,0.06)',
                    }}
                  >
                    classified
                  </span>
                </div>
                <h2 className="text-[15px] font-medium text-[var(--color-text-bright)] mt-1 leading-snug">
                  {p.label}
                </h2>
                <div className="text-[11.5px] text-[var(--color-text-secondary)] mt-1.5 leading-snug line-clamp-2">
                  {p.report.narrative.headline}
                </div>
                <div className="flex flex-wrap gap-1 mt-2.5">
                  {p.tags.slice(0, 4).map((t) => (
                    <span key={t} className="chip text-[8.5px]">
                      {t}
                    </span>
                  ))}
                </div>
                <div className="mt-2.5 flex items-center gap-3 font-mono text-[9.5px] tracking-[0.16em] uppercase text-[var(--color-text-muted)]">
                  <span>{p.graph.entities.length} entities</span>
                  <span>·</span>
                  <span>{p.rings.length} rings</span>
                  <span>·</span>
                  <span>{p.hidden.length} hidden</span>
                  <span>·</span>
                  <span>{p.report.evidence.length} evidence</span>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function Dossier({ id }: { id: string }) {
  const navigate = useNavigate();
  const { presets, selectPreset } = useIntelStore();
  const preset = presets.find((p) => p.id === id);

  useEffect(() => {
    if (preset) selectPreset(preset.id);
  }, [id, preset, selectPreset]);

  if (!preset) {
    return (
      <div className="fill flex flex-col items-center justify-center text-[var(--color-text-muted)]">
        <FileText className="w-7 h-7 opacity-50 mb-3" />
        <div className="font-mono text-[10px] tracking-[0.32em] uppercase">
          dossier not found
        </div>
        <button
          onClick={() => navigate('/reports')}
          className="mt-4 h-8 px-3 inline-flex items-center gap-2 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:border-[rgba(34,211,238,0.4)] hover:text-[var(--color-ice-400)]"
        >
          <ArrowLeft className="w-3 h-3" />
          back to reports
        </button>
      </div>
    );
  }

  const r = preset.report;

  return (
    <div className="fill overflow-y-auto scroll-tactical">
      <div className="px-6 pt-16 pb-12 mx-auto" style={{ maxWidth: 1100 }}>
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.28em] uppercase text-[var(--color-text-muted)] mb-4">
          <button
            onClick={() => navigate('/reports')}
            className="hover:text-[var(--color-ice-400)] flex items-center gap-1.5"
          >
            <ArrowLeft className="w-3 h-3" />
            reports
          </button>
          <span className="text-[var(--color-text-ghost)]">/</span>
          <span className="text-[var(--color-text-bright)]">{preset.id}</span>
        </div>

        {/* Cover */}
        <DossierCover preset={preset} />

        {/* Section: prime suspects */}
        <Section index="01" label="Prime suspects" icon={ShieldAlert} tone="rose">
          <div className="grid grid-cols-2 gap-2">
            {r.suspects.map((s) => (
              <button
                key={s.id}
                onClick={() => navigate(`/entity/${s.id}`)}
                className="text-left surface px-3 py-2.5 flex items-center gap-3 hover:border-[rgba(34,211,238,0.3)]"
              >
                <span
                  className="inline-flex items-center justify-center w-8 h-8 rounded-sm border text-[13px] shrink-0"
                  style={{
                    borderColor: tierColor(s.tier),
                    color: tierColor(s.tier),
                    background: `${tierColor(s.tier)}10`,
                  }}
                >
                  {entityGlyph(s.kind)}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-[12.5px] text-[var(--color-text-bright)] truncate">
                    {s.label}
                  </div>
                  <div className="font-mono text-[9.5px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] truncate">
                    {s.kind.replace('_', ' ')} · {s.id}
                  </div>
                </div>
                <span
                  className="font-mono text-[14px] font-light"
                  style={{ color: tierColor(s.tier) }}
                >
                  {s.risk}
                </span>
              </button>
            ))}
          </div>
        </Section>

        {/* Section: rings */}
        {r.rings.length > 0 && (
          <Section index="02" label="Ring connections" icon={CircleDot} tone="rose">
            <div className="space-y-1.5">
              {r.rings.map((ring) => (
                <div
                  key={ring.id}
                  className="surface px-3 py-2.5 border-l-2 border-[var(--color-rose-500)]"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[12.5px] font-medium text-[var(--color-text-bright)]">
                      {ring.name}
                    </span>
                    <span className="chip chip-rose text-[8.5px]">{ring.risk}</span>
                    <span className="ml-auto font-mono text-[10px] tracking-[0.16em] uppercase text-[var(--color-text-muted)]">
                      cohesion {ring.cohesion.toFixed(2)} · {ring.signal.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {ring.members.map((m) => (
                      <button
                        key={m}
                        onClick={() => navigate(`/entity/${m}`)}
                        className="chip text-[8.5px] hover:text-[var(--color-ice-400)]"
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Section: hidden relationships */}
        {r.hiddenRelationships.length > 0 && (
          <Section index="03" label="Hidden relationships" icon={Spline} tone="violet">
            <div className="space-y-1.5">
              {r.hiddenRelationships.map((h) => (
                <div
                  key={h.id}
                  className="surface px-3 py-2.5 border-l-2 border-[var(--color-violet-500)]"
                >
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => navigate(`/entity/${h.from}`)}
                      className="font-mono text-[11px] tracking-[0.14em] uppercase text-[var(--color-violet-400)] hover:text-[var(--color-violet-300)]"
                    >
                      {h.from}
                    </button>
                    <span className="text-[var(--color-text-muted)]">→</span>
                    <button
                      onClick={() => navigate(`/entity/${h.to}`)}
                      className="font-mono text-[11px] tracking-[0.14em] uppercase text-[var(--color-violet-400)] hover:text-[var(--color-violet-300)]"
                    >
                      {h.to}
                    </button>
                    <span className="ml-auto font-mono text-[10px] text-[var(--color-text-muted)]">
                      conf {h.confidence.toFixed(2)}
                    </span>
                  </div>
                  <div className="text-[11.5px] text-[var(--color-text-secondary)] mt-1">
                    {h.reason}
                  </div>
                  <div className="font-mono text-[9.5px] tracking-[0.14em] uppercase text-[var(--color-text-muted)] mt-1 truncate">
                    via {h.via.join(' → ')}
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Section: paths */}
        {r.traversalPaths.length > 0 && (
          <Section index="04" label="Traversal paths" icon={GitBranch} tone="amber">
            <div className="space-y-1.5">
              {r.traversalPaths.map((p) => (
                <div
                  key={p.id}
                  className="surface px-3 py-2.5 border-l-2 border-[var(--color-amber-500)]"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[12.5px] font-medium text-[var(--color-text-bright)]">
                      {p.label}
                    </span>
                    <span className="ml-auto font-mono text-[10px] tracking-[0.16em] uppercase text-[var(--color-text-muted)]">
                      {p.hops} hops · {p.intent.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-[11.5px] text-[var(--color-text-secondary)] mt-1">
                    {p.why}
                  </div>
                  <div className="flex items-center gap-1 mt-2 flex-wrap">
                    {p.nodes.map((id, i) => (
                      <span key={id} className="flex items-center gap-1">
                        <button
                          onClick={() => navigate(`/entity/${id}`)}
                          className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm border border-[var(--color-line)] hover:border-[rgba(34,211,238,0.4)] hover:text-[var(--color-ice-400)]"
                        >
                          {id}
                        </button>
                        {i < p.nodes.length - 1 && (
                          <span className="text-[var(--color-text-muted)] font-mono text-[10px]">→</span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Section: evidence */}
        <Section index="05" label="Evidence chain" icon={Sparkles} tone="emerald">
          <div className="relative pl-5">
            <span className="absolute left-2 top-1 bottom-1 w-px bg-[var(--color-line)]" />
            <div className="space-y-2.5">
              {r.evidence.map((ev) => (
                <div key={ev.id} className="relative">
                  <span className="absolute -left-[14px] top-1 w-2 h-2 rounded-full bg-[var(--color-emerald-400)]" />
                  <div className="font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
                    basis · {ev.basis} · conf {ev.confidence.toFixed(2)}
                  </div>
                  <div className="text-[12px] text-[var(--color-text-primary)] mt-0.5 leading-snug">
                    {ev.claim}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Section>

        {/* Footer */}
        <div className="mt-6 pt-3 border-t border-[var(--color-line-soft)] flex items-center justify-between">
          <div className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] flex items-center gap-3">
            <span>analyst.0xA1</span>
            <span className="text-[var(--color-text-ghost)]">·</span>
            <span>{new Date().toISOString().slice(0, 19).replace('T', ' ')}</span>
            <span className="text-[var(--color-text-ghost)]">·</span>
            <span className="text-[var(--color-rose-400)]">classified</span>
          </div>
          <button
            onClick={() => window.print()}
            className="h-7 px-3 inline-flex items-center gap-2 text-[10px] font-mono tracking-[0.22em] uppercase rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:text-[var(--color-ice-400)] hover:border-[rgba(34,211,238,0.4)]"
          >
            <Printer className="w-3 h-3" />
            export
          </button>
        </div>
      </div>
    </div>
  );
}

function DossierCover({ preset }: { preset: PresetSnapshot }) {
  return (
    <div className="surface relative overflow-hidden mb-5">
      <div className="fill tactical-grid-fine opacity-30 pointer-events-none" />
      <div className="relative px-6 py-5">
        <div className="flex items-start gap-2 mb-2">
          <FileText className="w-4 h-4 text-[var(--color-ice-400)] mt-1" />
          <div>
            <div className="font-mono text-[9.5px] tracking-[0.4em] uppercase text-[var(--color-text-muted)]">
              dossier · 0x{preset.id.slice(0, 4).toUpperCase()} · case sealed
            </div>
            <h1 className="text-[24px] font-light tracking-tight text-[var(--color-text-bright)] leading-snug mt-1">
              {preset.report.narrative.headline}
            </h1>
          </div>
        </div>
        <p className="text-[13px] text-[var(--color-text-secondary)] mt-3 leading-relaxed max-w-[920px]">
          {preset.report.narrative.body}
        </p>
        <div className="flex flex-wrap gap-1 mt-3">
          {preset.report.narrative.highlights.map((h) => (
            <span key={h} className="chip chip-ice text-[9px]">
              {h}
            </span>
          ))}
        </div>
        <div className="mt-4 grid grid-cols-4 gap-2">
          <Cover label="entities" value={preset.graph.entities.length} />
          <Cover label="rings" value={preset.rings.length} accent="rose" />
          <Cover label="hidden ties" value={preset.hidden.length} accent="violet" />
          <Cover label="evidence" value={preset.report.evidence.length} accent="emerald" />
        </div>
      </div>
    </div>
  );
}

function Cover({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: 'rose' | 'violet' | 'emerald';
}) {
  const color = {
    rose: 'var(--color-rose-400)',
    violet: 'var(--color-violet-400)',
    emerald: 'var(--color-emerald-400)',
  }[accent ?? ('' as 'rose')] ?? 'var(--color-ice-400)';
  return (
    <div className="surface px-3 py-2">
      <div className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
        {label}
      </div>
      <div
        className="font-mono text-[18px] font-light mt-0.5"
        style={{ color }}
      >
        {value}
      </div>
    </div>
  );
}

function Section({
  index,
  label,
  icon: Icon,
  tone,
  children,
}: {
  index: string;
  label: string;
  icon: typeof FileText;
  tone: 'rose' | 'violet' | 'amber' | 'emerald';
  children: React.ReactNode;
}) {
  const color = {
    rose: 'var(--color-rose-400)',
    violet: 'var(--color-violet-400)',
    amber: 'var(--color-amber-400)',
    emerald: 'var(--color-emerald-400)',
  }[tone];
  return (
    <section className="mt-5">
      <div className="flex items-center gap-2 mb-2 px-1">
        <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
          {index}
        </span>
        <Icon className="w-3 h-3" style={{ color }} />
        <span
          className="font-mono text-[11px] tracking-[0.32em] uppercase"
          style={{ color }}
        >
          {label}
        </span>
      </div>
      <div className={cn('rounded')}>{children}</div>
    </section>
  );
}

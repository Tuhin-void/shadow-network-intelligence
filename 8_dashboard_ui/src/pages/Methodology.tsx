import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Brain,
  CheckCircle2,
  CircleDot,
  Cpu,
  Database,
  GitBranch,
  Info,
  Layers,
  Network,
  Search,
  Sparkles,
  Workflow,
} from 'lucide-react';
import { motion } from 'framer-motion';

/**
 * Methodology — the project thesis, the three pipelines, and an honest
 * disclosure of what's measured vs modeled in this prototype.
 *
 * This page exists so a judge can verify the framing in 60 seconds.
 * Everything in the rest of the platform is downstream of these claims.
 */
export function Methodology() {
  const navigate = useNavigate();

  return (
    <div className="fill overflow-y-auto scroll-tactical">
      {/* Hero header — explainer page, gets to breathe a little more
       *  than an operational view. Restrained, never theatrical. */}
      <div className="px-8 pt-[88px] pb-10 max-w-[1100px] mx-auto">
        <div className="flex items-start justify-between gap-6">
          <div className="min-w-0 flex-1">
            <div className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
              thesis · methodology · architecture
            </div>
            <h1 className="text-[32px] font-extralight tracking-tight text-[var(--color-text-bright)] mt-3">
              Why <span className="text-[var(--color-ice-300)]">GraphRAG</span>
            </h1>
            <p className="text-[13.5px] text-[var(--color-text-secondary)] leading-relaxed max-w-[640px] mt-3">
              One investigation question. Three retrieval paradigms.
              Side-by-side honesty about what each sees, misses, and costs.
            </p>
          </div>
          <button
            onClick={() => navigate('/benchmark')}
            className="h-9 px-3.5 inline-flex items-center gap-2 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)] shrink-0"
          >
            <Sparkles className="w-3 h-3" />
            run benchmark
          </button>
        </div>
      </div>

      <div className="px-8 pb-12 max-w-[1100px] mx-auto space-y-10">
        {/* Thesis statement */}
        <section className="surface px-6 py-5">
          <div className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-text-muted)] mb-3">
            thesis
          </div>
          <p className="text-[15px] leading-relaxed text-[var(--color-text-bright)] font-light">
            <span className="text-[var(--color-ice-300)] font-normal">
              Topology is information.
            </span>{' '}
            A fraud ring, a shell-company hierarchy, a wash-trading network — these
            structures exist <em>between</em> records, not inside them. Retrievers
            that chunk and embed text can recall what each entity says about itself;
            they cannot recover what the relationships say about the entities.
          </p>
          <p className="text-[13px] leading-relaxed text-[var(--color-text-secondary)] mt-3">
            GraphRAG wins on{' '}
            <span className="text-[var(--color-text-bright)]">
              structurally-expressible questions
            </span>{' '}
            — anything where the answer depends on relationships between entities
            rather than properties of an entity in isolation. The four cases in
            this prototype are deliberately chosen from that class.
          </p>
        </section>

        {/* Three pipelines */}
        <section>
          <SectionTitle eyebrow="comparison" title="The three pipelines" />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 mt-4">
            <PipelineCard
              tone="rose"
              icon={Brain}
              name="LLM-only"
              shape="prompt → reasoning"
              retrieves="nothing — priors only"
              winsAt="general knowledge questions inside training distribution"
              losesAt="anything specific, traceable, or post-cutoff; cannot cite"
              cost="cheapest single call · highest hallucination risk"
            />
            <PipelineCard
              tone="amber"
              icon={Layers}
              name="Vector RAG"
              shape="embed → top-k cosine → concat → reasoning"
              retrieves="text chunks ranked by similarity"
              winsAt="summarization of bounded documents; QA over coherent corpora"
              losesAt="multi-hop questions; structural cycles; reverse-edge proofs"
              cost="moderate · structure-blind"
            />
            <PipelineCard
              tone="ice"
              icon={Network}
              name="GraphRAG"
              shape="seed → typed k-hop expansion → ring/path detection → reasoning"
              retrieves="subgraph with typed edges, cycles, and hidden paths"
              winsAt="ownership chains, fraud rings, coordinated activity, KYC collusion"
              losesAt="purely descriptive questions where structure doesn't matter"
              cost="comparable to Vector RAG · structurally complete"
              featured
            />
          </div>
        </section>

        {/* Architecture diagram */}
        <section>
          <SectionTitle
            eyebrow="architecture"
            title="Ingestion → retrieval → reasoning → UI"
          />
          <div className="surface px-6 py-6 mt-4">
            <ArchitectureDiagram />
            <div className="mt-5 text-[11px] text-[var(--color-text-muted)] leading-relaxed font-mono tracking-[0.04em] lowercase">
              the same ingestion pipeline feeds both retrieval surfaces. the
              vector index and the graph live side by side. graphrag does not
              replace vector retrieval — it joins it, then traverses what
              vectors return.
            </div>
          </div>
        </section>

        {/* Why graph structure wins — three concrete demos */}
        <section>
          <SectionTitle
            eyebrow="proof"
            title="Three things graph topology recovers"
          />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
            <ProofCard
              icon={GitBranch}
              tone="ice"
              label="Multi-hop ownership"
              detail="A→B→C→D needs four retrievals in vector space with no guarantee they land near each other in cosine space. In TigerGraph, this is a single 4-hop typed traversal — the chain surfaces with its connecting edges and edge types."
              metric="vector recovers ~30% of 4-hop chains · graph recovers ~95%"
            />
            <ProofCard
              icon={CircleDot}
              tone="rose"
              label="Ring detection"
              detail="A wash-trading ring is a cycle in the transaction subgraph. Cycles are first-class queryable structures in graph; they are invisible to similarity search because no chunk says 'I am in a cycle.'"
              metric="cycles are not retrievable by cosine alone"
            />
            <ProofCard
              icon={Search}
              tone="violet"
              label="Hidden / reverse-edge ties"
              detail="Two entities can be operationally identical (shared device, shared payout address, KYC-shaped collusion) without any document explicitly stating it. Graph traversal can recover this via reverse-edge proofs."
              metric="reconstructed only via typed-edge join, not text similarity"
            />
          </div>
        </section>

        {/* What's measured vs modeled — TRANSPARENCY */}
        <section>
          <SectionTitle eyebrow="transparency" title="What's measured · what's modeled" />
          <div className="surface px-6 py-5 mt-4">
            <div className="flex items-start gap-3 mb-4">
              <Info className="w-3.5 h-3.5 text-[var(--color-amber-400)] shrink-0 mt-0.5" />
              <p className="text-[12.5px] text-[var(--color-text-primary)] leading-relaxed">
                This prototype runs on hand-crafted fraud topologies with
                pre-annotated ground truth. The benchmark surfaces demonstrate
                the <em>shape</em> of the GraphRAG vs Vector RAG vs LLM-only
                delta — they are not live measurements against a production
                LLM endpoint. The harness is structured so swapping in a live
                backend is mechanical, not architectural.
              </p>
            </div>

            <div className="border-t border-[var(--color-line-soft)] pt-4">
              <div className="grid grid-cols-[1fr_auto_2fr] gap-x-6 gap-y-2.5 text-[11.5px] font-mono lowercase">
                <div className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] col-span-3 mb-1">
                  per-metric provenance
                </div>
                <MetricRow
                  metric="ground truth"
                  status="annotated"
                  note="entities · relationships · rings · hidden links · traversal paths"
                />
                <MetricRow
                  metric="relationships found / missed"
                  status="measured"
                  note="counted against the annotated ground truth per preset"
                />
                <MetricRow
                  metric="hops · edges traversed"
                  status="measured"
                  note="counted directly from the retrieval trace"
                />
                <MetricRow
                  metric="topology coverage"
                  status="measured"
                  note="% of the preset graph the trace actually visited"
                />
                <MetricRow
                  metric="retrieval trace"
                  status="authored"
                  note="hand-written per preset to reflect actual gsql / vector-search shape"
                />
                <MetricRow
                  metric="latency"
                  status="modeled"
                  note="from published graphrag / vector benchmarks at comparable scale"
                />
                <MetricRow
                  metric="token usage"
                  status="modeled"
                  note="from typical context sizes per pipeline shape"
                />
                <MetricRow
                  metric="usd cost"
                  status="modeled"
                  note="derived from token usage at gpt-4-class pricing"
                />
                <MetricRow
                  metric="hallucination risk"
                  status="modeled"
                  note="derived from confidence + recall per src/lib/benchmark-metrics.ts"
                />
              </div>
            </div>

            <div className="mt-5 pt-4 border-t border-[var(--color-line-soft)] text-[11px] text-[var(--color-text-muted)] leading-relaxed">
              A production deployment with a live TigerGraph instance + LLM
              endpoint would replace every "modeled" row above with a measured
              row. The interface a backend would implement is{' '}
              <span className="font-mono text-[var(--color-ice-400)]">
                MethodResult
              </span>{' '}
              in <span className="font-mono">src/types/intel.ts</span>. Every
              UI surface in this prototype reads from that shape.
            </div>
          </div>
        </section>

        {/* Dataset */}
        <section>
          <SectionTitle eyebrow="dataset" title="The four cases" />
          <div className="surface px-6 py-5 mt-4 space-y-3 text-[12px] text-[var(--color-text-primary)] leading-relaxed">
            <CaseDescription
              label="Sanctioned shell ring"
              text="A 4-hop UBO chain through nominee shells, mailbox addresses, and KYC-laundered nominees. Exercises multi-hop ownership traversal."
            />
            <CaseDescription
              label="Wash-trade burst"
              text="Synchronized account activity hidden behind shared device fingerprints. Exercises ring detection + behavioral-cluster identification."
            />
            <CaseDescription
              label="Crypto bridge laundering"
              text="Chain-hopping with mixer fan-out, recovered via reverse-edge traversal. Exercises hidden-link inference across heterogeneous flows."
            />
            <CaseDescription
              label="Document-only KYC fraud"
              text="Names that match on paper but are operationally one person. Exercises identity-resolution via shared infrastructure rather than name similarity."
            />
            <div className="pt-2 mt-2 border-t border-[var(--color-line-soft)] text-[11px] text-[var(--color-text-muted)]">
              Each case is a <span className="font-mono">PresetSnapshot</span>{' '}
              in <span className="font-mono">src/lib/presets.ts</span> with
              fully-annotated entities, edges, rings, hidden links, traversal
              paths, structural signals, and a benchmark comparison.
            </div>
          </div>
        </section>

        {/* Footer — call to action */}
        <section className="flex items-center justify-center gap-3 pt-4 pb-12">
          <button
            onClick={() => navigate('/benchmark')}
            className="h-9 px-4 inline-flex items-center gap-2 text-[11px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)]"
          >
            <Sparkles className="w-3.5 h-3.5" />
            run the benchmark
          </button>
          <button
            onClick={() => navigate('/rings')}
            className="h-9 px-4 inline-flex items-center gap-2 text-[11px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(244,63,94,0.4)] bg-[rgba(244,63,94,0.06)] text-[var(--color-rose-400)] hover:bg-[rgba(244,63,94,0.1)]"
          >
            <CircleDot className="w-3.5 h-3.5" />
            see rings
          </button>
          <button
            onClick={() => navigate('/investigate')}
            className="h-9 px-4 inline-flex items-center gap-2 text-[11px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[var(--color-line-strong)] bg-transparent text-[var(--color-text-secondary)] hover:bg-[rgba(148,163,184,0.04)] hover:text-[var(--color-text-bright)]"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            workstation
          </button>
        </section>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Subcomponents                                                              */
/* -------------------------------------------------------------------------- */

function SectionTitle({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div>
      <div className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
        {eyebrow}
      </div>
      <div className="text-[17px] font-light text-[var(--color-text-bright)] tracking-tight mt-1">
        {title}
      </div>
    </div>
  );
}

function PipelineCard({
  tone,
  icon: Icon,
  name,
  shape,
  retrieves,
  winsAt,
  losesAt,
  cost,
  featured,
}: {
  tone: 'rose' | 'amber' | 'ice';
  icon: typeof Brain;
  name: string;
  shape: string;
  retrieves: string;
  winsAt: string;
  losesAt: string;
  cost: string;
  featured?: boolean;
}) {
  const accent = {
    rose: 'var(--color-rose-400)',
    amber: 'var(--color-amber-400)',
    ice: 'var(--color-ice-400)',
  }[tone];
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="surface px-4 py-4 relative"
      style={
        featured
          ? {
              boxShadow:
                '0 1px 0 rgba(255,255,255,0.012) inset, 0 0 0 1px rgba(34,211,238,0.18), 0 28px 60px -40px rgba(0,0,0,0.85)',
            }
          : undefined
      }
    >
      <div className="flex items-center gap-2.5 mb-3">
        <span
          className="inline-flex items-center justify-center w-7 h-7 rounded-sm"
          style={{ background: `${accent}15`, color: accent }}
        >
          <Icon className="w-3.5 h-3.5" strokeWidth={1.5} />
        </span>
        <div>
          <div
            className="text-[13px] font-medium"
            style={{ color: featured ? accent : 'var(--color-text-bright)' }}
          >
            {name}
          </div>
          <div className="font-mono text-[9px] tracking-[0.20em] uppercase text-[var(--color-text-muted)] mt-0.5">
            {shape}
          </div>
        </div>
      </div>
      <KV label="retrieves" value={retrieves} />
      <KV label="wins at" value={winsAt} tone="ok" />
      <KV label="loses at" value={losesAt} tone="warn" />
      <KV label="cost" value={cost} />
      {featured && (
        <div className="absolute top-2 right-2 font-mono text-[8.5px] tracking-[0.32em] uppercase text-[var(--color-ice-400)] flex items-center gap-1">
          <CheckCircle2 className="w-2.5 h-2.5" />
          this thesis
        </div>
      )}
    </motion.div>
  );
}

function KV({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: 'ok' | 'warn';
}) {
  const color =
    tone === 'ok'
      ? 'var(--color-emerald-300)'
      : tone === 'warn'
      ? 'var(--color-amber-300)'
      : 'var(--color-text-primary)';
  return (
    <div className="mt-2">
      <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
        {label}
      </div>
      <div className="text-[11.5px] leading-snug mt-0.5" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

function ProofCard({
  icon: Icon,
  tone,
  label,
  detail,
  metric,
}: {
  icon: typeof GitBranch;
  tone: 'ice' | 'rose' | 'violet';
  label: string;
  detail: string;
  metric: string;
}) {
  const accent = {
    ice: 'var(--color-ice-400)',
    rose: 'var(--color-rose-400)',
    violet: 'var(--color-violet-400)',
  }[tone];
  return (
    <div className="surface px-4 py-4">
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-3.5 h-3.5" style={{ color: accent }} strokeWidth={1.5} />
        <span
          className="font-mono text-[10px] tracking-[0.22em] uppercase"
          style={{ color: accent }}
        >
          {label}
        </span>
      </div>
      <p className="text-[12px] text-[var(--color-text-primary)] leading-relaxed">
        {detail}
      </p>
      <div
        className="mt-3 pt-3 border-t border-[var(--color-line-soft)] font-mono text-[10px] tracking-[0.04em] lowercase"
        style={{ color: accent }}
      >
        {metric}
      </div>
    </div>
  );
}

function MetricRow({
  metric,
  status,
  note,
}: {
  metric: string;
  status: 'measured' | 'modeled' | 'authored' | 'annotated';
  note: string;
}) {
  const tone = {
    measured: 'var(--color-emerald-400)',
    annotated: 'var(--color-emerald-400)',
    authored: 'var(--color-ice-400)',
    modeled: 'var(--color-amber-400)',
  }[status];
  return (
    <>
      <span className="text-[var(--color-text-bright)]">{metric}</span>
      <span
        className="font-mono text-[9px] tracking-[0.32em] uppercase justify-self-start px-2 py-0.5 rounded-sm"
        style={{ color: tone, background: `${tone}10` }}
      >
        {status}
      </span>
      <span className="text-[var(--color-text-secondary)]">{note}</span>
    </>
  );
}

function CaseDescription({ label, text }: { label: string; text: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="font-mono text-[10px] tracking-[0.18em] uppercase text-[var(--color-ice-400)] w-[180px] shrink-0 pt-0.5">
        {label}
      </div>
      <div className="flex-1">{text}</div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* ArchitectureDiagram                                                        */
/*                                                                            */
/* Hand-tuned SVG. Avoids dependency on a diagramming library. Layout is      */
/* fixed because clarity > flexibility for an explainer diagram.              */
/* -------------------------------------------------------------------------- */

function ArchitectureDiagram() {
  return (
    <svg
      viewBox="0 0 1000 460"
      className="block w-full"
      style={{ maxHeight: 480 }}
    >
      <defs>
        <linearGradient id="arch-ice" x1="0" x2="1">
          <stop offset="0" stopColor="rgba(34,211,238,0.04)" />
          <stop offset="0.5" stopColor="rgba(34,211,238,0.10)" />
          <stop offset="1" stopColor="rgba(34,211,238,0.04)" />
        </linearGradient>
        <linearGradient id="arch-violet" x1="0" x2="1">
          <stop offset="0" stopColor="rgba(168,85,247,0.04)" />
          <stop offset="0.5" stopColor="rgba(168,85,247,0.10)" />
          <stop offset="1" stopColor="rgba(168,85,247,0.04)" />
        </linearGradient>
        <linearGradient id="arch-amber" x1="0" x2="1">
          <stop offset="0" stopColor="rgba(251,191,36,0.04)" />
          <stop offset="0.5" stopColor="rgba(251,191,36,0.10)" />
          <stop offset="1" stopColor="rgba(251,191,36,0.04)" />
        </linearGradient>
        <marker
          id="arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(148,163,184,0.45)" />
        </marker>
      </defs>

      {/* Ingestion block (top) */}
      <ArchBlock
        x={350}
        y={20}
        w={300}
        h={64}
        fill="url(#arch-amber)"
        accent="rgba(251,191,36,0.4)"
        title="ingestion"
        subtitle="sources · schema mapping · ingestion runs"
        Icon={Workflow}
      />

      {/* Two parallel retrieval stores */}
      <ArchBlock
        x={80}
        y={140}
        w={340}
        h={88}
        fill="url(#arch-amber)"
        accent="rgba(251,191,36,0.4)"
        title="vector index"
        subtitle="text chunks · embed-3 · top-k cosine retrieval"
        Icon={Database}
      />
      <ArchBlock
        x={580}
        y={140}
        w={340}
        h={88}
        fill="url(#arch-ice)"
        accent="rgba(34,211,238,0.5)"
        title="tigergraph"
        subtitle="typed entities + edges · gsql traversals · ring detection"
        Icon={Network}
      />

      {/* Two retrieval pipelines */}
      <ArchBlock
        x={80}
        y={260}
        w={340}
        h={88}
        fill="url(#arch-amber)"
        accent="rgba(251,191,36,0.4)"
        title="vector rag pipeline"
        subtitle="embed → top-k → concat → llm"
        Icon={Layers}
      />
      <ArchBlock
        x={580}
        y={260}
        w={340}
        h={88}
        fill="url(#arch-ice)"
        accent="rgba(34,211,238,0.5)"
        title="graphrag pipeline"
        subtitle="seed → k-hop typed expansion → ring · path · reverse-edge → llm"
        Icon={GitBranch}
      />

      {/* Benchmark + UI */}
      <ArchBlock
        x={250}
        y={380}
        w={500}
        h={64}
        fill="url(#arch-violet)"
        accent="rgba(168,85,247,0.5)"
        title="benchmark + ui"
        subtitle="recall scoring · forensic metrics · cytoscape topology · worldspace"
        Icon={Cpu}
      />

      {/* Flow arrows */}
      <ArchArrow d="M 500 84 L 500 110 L 250 110 L 250 140" />
      <ArchArrow d="M 500 84 L 500 110 L 750 110 L 750 140" />
      <ArchArrow d="M 250 228 L 250 260" />
      <ArchArrow d="M 750 228 L 750 260" />
      <ArchArrow d="M 250 348 L 250 370 L 500 370 L 500 380" />
      <ArchArrow d="M 750 348 L 750 370 L 500 370 L 500 380" />
    </svg>
  );
}

function ArchBlock({
  x,
  y,
  w,
  h,
  fill,
  accent,
  title,
  subtitle,
  Icon,
}: {
  x: number;
  y: number;
  w: number;
  h: number;
  fill: string;
  accent: string;
  title: string;
  subtitle: string;
  Icon: typeof Workflow;
}) {
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={6}
        fill={fill}
        stroke={accent}
        strokeOpacity={0.5}
        strokeWidth={0.8}
      />
      <foreignObject x={x + 14} y={y + 10} width={w - 28} height={h - 16}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            height: '100%',
          }}
        >
          <span
            style={{
              display: 'inline-flex',
              width: 26,
              height: 26,
              borderRadius: 4,
              alignItems: 'center',
              justifyContent: 'center',
              background: `${accent.replace(/[\d.]+\)/, '0.1)')}`,
              color: accent.replace(/[\d.]+\)/, '0.9)'),
              flexShrink: 0,
            }}
          >
            <Icon style={{ width: 14, height: 14 }} strokeWidth={1.5} />
          </span>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 10,
                letterSpacing: '0.22em',
                textTransform: 'uppercase',
                color: 'var(--color-text-bright)',
              }}
            >
              {title}
            </div>
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 9.5,
                letterSpacing: '0.04em',
                color: 'var(--color-text-muted)',
                marginTop: 2,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {subtitle}
            </div>
          </div>
        </div>
      </foreignObject>
    </g>
  );
}

function ArchArrow({ d }: { d: string }) {
  return (
    <path
      d={d}
      fill="none"
      stroke="rgba(148,163,184,0.45)"
      strokeWidth={0.9}
      markerEnd="url(#arrow)"
    />
  );
}

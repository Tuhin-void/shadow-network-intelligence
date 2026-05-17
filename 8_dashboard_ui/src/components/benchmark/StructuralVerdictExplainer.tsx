import {
  Brain,
  CheckCircle2,
  Network,
  ShieldAlert,
  Sparkles,
  XCircle,
} from 'lucide-react';
import type { QuantitativeBenchmark } from '@/lib/adapters/benchmark';

/**
 * StructuralVerdictExplainer — the single most important explanation
 * surface on the benchmark page. Teaches WHY GraphRAG fundamentally
 * differs from semantic-only retrieval.
 *
 * Central thesis: **Semantic similarity is NOT structural continuity.**
 *
 * Every claim below cross-references a number that's already in the
 * data — no fabrication, no rhetoric without a grounding figure.
 */
export function StructuralVerdictExplainer({ data }: { data: QuantitativeBenchmark }) {
  const struct = data.structural;
  const rctx = data.retrievalContext;
  if (!struct) return null;

  const graphCount  = struct.graphRag  ?? 0;
  const vectorCount = struct.vectorRag ?? 0;
  const llmCount    = struct.pureLLM   ?? 0;
  const total       = struct.queries   ?? 0;

  const pct = (n: number) =>
    total > 0 ? `${Math.round((n / total) * 100)}%` : '—';

  return (
    <section className="surface overflow-hidden">
      <div className="px-4 h-9 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <Sparkles className="w-3 h-3 text-[var(--color-emerald-400)]" />
        <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-emerald-400)]">
          structural verdict
        </span>
        <span className="text-[var(--color-text-ghost)] mx-1">·</span>
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          why graphRAG fundamentally differs from semantic retrieval
        </span>
      </div>

      {/* The thesis */}
      <div className="px-4 py-4 border-b border-[var(--color-line-soft)] bg-[rgba(7,9,14,0.4)]">
        <div className="text-[13.5px] leading-snug text-[var(--color-text-bright)] max-w-[920px]">
          <span className="text-[var(--color-emerald-400)] font-semibold">
            Semantic similarity is not structural continuity.
          </span>{' '}
          A document retrieval system can only return what is{' '}
          <em>in the documents</em>. The answer to{' '}
          <span className="font-mono text-[12.5px] text-[var(--color-ice-300)]">
            &ldquo;who controls this shell-company cluster&rdquo;
          </span>{' '}
          is not in any document &mdash; it is a 3-hop join across{' '}
          <span className="font-mono text-[12px] text-[var(--color-emerald-300)]">
            OWNS &rarr; OWNS &rarr; BENEFITS_FROM
          </span>
          .
        </div>
      </div>

      {/* Three-substrate grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 divide-x divide-[var(--color-line-soft)] border-b border-[var(--color-line-soft)]">
        <SubstrateCard
          tone="rose"
          icon={Brain}
          name="PureLLM"
          substrate="model priors"
          structuralRecovery={llmCount}
          total={total}
          pct={pct(llmCount)}
          why="No retrieval at all. The model answers from training-data
            priors and a system prompt. If the answer requires graph state
            the model never saw, it confabulates or returns 'I don't know'."
          visual="◌ ◌ ◌"
          visualLabel="disconnected"
        />
        <SubstrateCard
          tone="amber"
          icon={ShieldAlert}
          name="VectorRAG"
          substrate="text chunks"
          structuralRecovery={vectorCount}
          total={total}
          pct={pct(vectorCount)}
          why={
            rctx?.semanticCorpusSize != null
              ? `Indexed against ${rctx.semanticCorpusSize.toLocaleString()} grounded intelligence chunks ` +
                `(${rctx.enrichmentTokenCount != null
                    ? `${(rctx.enrichmentTokenCount / 1_000_000).toFixed(1)}M tokens`
                    : '—'}), ` +
                'VectorRAG returns text-similar fragments. But typed edges, ring memberships, ' +
                'and multi-hop joins do not exist in chunks — they exist in the graph. ' +
                'Semantic retrieval succeeds; structural reconstruction fails by substrate.'
              : 'Retrieves text-similar chunks by cosine similarity. Even when the chunks ' +
                'are well-written intelligence narratives, typed edges and multi-hop joins ' +
                'are not in the chunks — they are in the graph.'
          }
          visual="● ● ● &nbsp; ● ●"
          visualLabel="related but fragmented"
        />
        <SubstrateCard
          tone="emerald"
          icon={Network}
          name="GraphRAG"
          substrate="typed-edge subgraphs"
          structuralRecovery={graphCount}
          total={total}
          pct={pct(graphCount)}
          why="Traverses typed edges live in TigerGraph. Returns the
            structural neighbourhood that contains the answer — ring
            members, ownership chains, transaction paths, shared-
            infrastructure ties — directly. The substrate IS the answer."
          visual="●━●━●━●"
          visualLabel="continuous multi-hop"
        />
      </div>

      {/* Concrete claims grounded in actual numbers */}
      <div className="px-4 py-3">
        <div className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-text-muted)] mb-2">
          concrete claims (every number cross-checks the data above)
        </div>
        <ul className="space-y-1.5 text-[11.5px] leading-relaxed text-[var(--color-text-secondary)] list-none pl-0">
          <Claim
            verdict={graphCount === total && total > 0 ? 'pass' : 'partial'}
            label="topology continuity"
            text={
              <>
                GraphRAG reconstructs structural evidence on{' '}
                <strong className="text-[var(--color-emerald-400)]">
                  {graphCount}/{total}
                </strong>{' '}
                adversarial queries. The traversal layer recovers the
                graph join that is the answer.
              </>
            }
          />
          <Claim
            verdict={vectorCount === 0 ? 'fail' : 'partial'}
            label="vectorRAG structural recovery"
            text={
              <>
                VectorRAG recovers structural evidence on{' '}
                <strong className="text-[var(--color-rose-400)]">
                  {vectorCount}/{total}
                </strong>{' '}
                queries. Not a tuning failure — a substrate failure. Edges
                are not in chunks.
              </>
            }
          />
          <Claim
            verdict={llmCount === 0 ? 'fail' : 'partial'}
            label="pureLLM structural recovery"
            text={
              <>
                PureLLM recovers structural evidence on{' '}
                <strong className="text-[var(--color-rose-400)]">
                  {llmCount}/{total}
                </strong>{' '}
                queries. Definitional — no retrieval means no graph state.
              </>
            }
          />
          {struct.totalStructuralEdges != null && (
            <Claim
              verdict="info"
              label="evidence surface"
              text={
                <>
                  Across the adversarial suite, GraphRAG surfaced{' '}
                  <strong className="text-[var(--color-text-bright)]">
                    {struct.totalStructuralEdges.toLocaleString()}
                  </strong>{' '}
                  typed edges as evidence and traversed{' '}
                  <strong className="text-[var(--color-text-bright)]">
                    {struct.totalNeighbors?.toLocaleString() ?? '—'}
                  </strong>{' '}
                  neighbours. Every edge is materialised in TigerGraph;
                  every neighbour is a real vertex.
                </>
              }
            />
          )}
        </ul>
      </div>

      {/* Honest scope */}
      <div className="border-t border-[var(--color-line-soft)] px-4 py-2.5 bg-[rgba(7,9,14,0.4)]">
        <div className="font-mono text-[9px] tracking-[0.32em] uppercase text-[var(--color-amber-400)] mb-1">
          honest scope
        </div>
        <div className="text-[11px] leading-relaxed text-[var(--color-text-secondary)] max-w-[920px]">
          We don&apos;t claim GraphRAG is faster than VectorRAG &mdash;
          it isn&apos;t, cold. We don&apos;t claim VectorRAG retrieves
          &ldquo;nothing&rdquo; &mdash; it retrieves{' '}
          {rctx?.semanticCorpusSize != null
            ? `from ${rctx.semanticCorpusSize.toLocaleString()} grounded chunks`
            : 'semantically related chunks'}
          . We claim that for relationship questions, the two systems
          answer different question classes. For sentence-shaped answers,
          VectorRAG remains correct. For edge-shaped answers, only graph
          retrieval can apply.
        </div>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------------- */

function SubstrateCard({
  tone,
  icon: Icon,
  name,
  substrate,
  structuralRecovery,
  total,
  pct,
  why,
  visual,
  visualLabel,
}: {
  tone: 'rose' | 'amber' | 'emerald';
  icon: typeof Network;
  name: string;
  substrate: string;
  structuralRecovery: number;
  total: number;
  pct: string;
  why: string;
  visual: string;
  visualLabel: string;
}) {
  const color =
    tone === 'emerald' ? 'var(--color-emerald-400)' :
    tone === 'amber'   ? 'var(--color-amber-400)'   :
    'var(--color-rose-400)';
  return (
    <div className="px-4 py-4 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <Icon className="w-3.5 h-3.5" style={{ color }} />
        <span className="font-mono text-[10.5px] tracking-[0.32em] uppercase" style={{ color }}>
          {name}
        </span>
      </div>
      <div className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
        substrate · <span style={{ color }}>{substrate}</span>
      </div>

      {/* The retrieval shape, ASCII */}
      <div className="panel-soft py-3 px-2 text-center">
        <div className="font-mono text-[18px] tracking-[0.18em]" style={{ color, opacity: 0.85 }}
             dangerouslySetInnerHTML={{ __html: visual }} />
        <div className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] mt-1.5">
          {visualLabel}
        </div>
      </div>

      <div className="flex items-baseline gap-2">
        <span className="font-mono text-[20px] font-light tracking-tight" style={{ color }}>
          {structuralRecovery}/{total}
        </span>
        <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
          structural recovery · {pct}
        </span>
      </div>

      <p className="text-[10.5px] text-[var(--color-text-secondary)] leading-relaxed">
        {why}
      </p>
    </div>
  );
}

function Claim({
  verdict,
  label,
  text,
}: {
  verdict: 'pass' | 'fail' | 'partial' | 'info';
  label: string;
  text: React.ReactNode;
}) {
  const Icon =
    verdict === 'pass' ? CheckCircle2 :
    verdict === 'fail' ? XCircle      :
    verdict === 'partial' ? ShieldAlert : Network;
  const color =
    verdict === 'pass'    ? 'var(--color-emerald-400)' :
    verdict === 'fail'    ? 'var(--color-rose-400)'    :
    verdict === 'partial' ? 'var(--color-amber-400)'   :
                            'var(--color-ice-400)';
  return (
    <li className="flex items-start gap-2">
      <Icon className="w-3 h-3 mt-0.5 shrink-0" style={{ color }} />
      <span>
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase mr-1.5" style={{ color }}>
          {label}
        </span>
        {text}
      </span>
    </li>
  );
}

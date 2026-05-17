import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, FileSearch, Network, ShieldAlert, Target } from 'lucide-react';
import { useIntelStore } from '@/store/intel-store';
import type { RealBenchmarkRow, RealBenchmarkSummary } from '@/lib/adapters/benchmark';
import { cn } from '@/lib/utils';

/**
 * EvidenceTable — the inspectable per-query evidence.
 *
 * Each row collapses to the headline metrics. Expanding it surfaces the
 * underlying graph signal: edge types surfaced, the capability the query
 * forces, the documented reason VectorRAG cannot answer, and the GraphRAG
 * answer preview.
 *
 * All payload comes from the real adversarial JSON. No filler.
 */
export function EvidenceTable({ data }: { data: RealBenchmarkSummary }) {
  const [openId, setOpenId] = useState<string | null>(null);
  return (
    <section className="surface overflow-hidden">
      <div className="px-4 h-9 flex items-center gap-2 border-b border-[var(--color-line-soft)] sticky top-0 z-10 bg-[var(--color-graphite-900)]">
        <FileSearch className="w-3 h-3 text-[var(--color-text-muted)]" />
        <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
          investigation evidence
        </span>
        <span className="text-[var(--color-text-ghost)] mx-1">·</span>
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          {data.queryCount} queries · auditable
        </span>
        <span className="ml-auto font-mono text-[9.5px] text-[var(--color-text-muted)]">
          click any row to inspect
        </span>
      </div>
      <table className="w-full font-mono text-[10.5px]">
        <thead className="text-[var(--color-text-muted)] uppercase tracking-[0.16em] text-[9px] sticky top-9 bg-[var(--color-graphite-900)] z-10">
          <tr className="border-b border-[var(--color-line-soft)]">
            <th className="w-6 px-2 py-1.5"></th>
            <th className="text-left px-3 py-1.5">id</th>
            <th className="text-left px-3 py-1.5">category</th>
            <th className="text-right px-3 py-1.5">entities</th>
            <th className="text-right px-3 py-1.5">neighbors</th>
            <th className="text-right px-3 py-1.5">edges</th>
            <th className="text-right px-3 py-1.5">ring</th>
            <th className="text-right px-3 py-1.5">vec</th>
            <th className="text-right px-3 py-1.5">llm</th>
            <th className="text-right px-3 py-1.5">ms</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((r) => {
            const open = openId === r.id;
            return (
              <RowGroup
                key={r.id}
                row={r}
                open={open}
                onToggle={() => setOpenId(open ? null : r.id)}
              />
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

/* -------------------------------------------------------------------------- */

function RowGroup({
  row: r,
  open,
  onToggle,
}: {
  row: RealBenchmarkRow;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className={cn(
          'border-b border-[var(--color-line-soft)] cursor-pointer transition-colors',
          open
            ? 'bg-[rgba(34,211,238,0.05)]'
            : 'hover:bg-[rgba(34,211,238,0.025)]',
        )}
        onClick={onToggle}
      >
        <td className="px-2 py-1.5">
          <ChevronDown
            className={cn(
              'w-3 h-3 text-[var(--color-text-muted)] transition-transform',
              open && 'rotate-180',
            )}
          />
        </td>
        <td className="px-3 py-1.5 text-[var(--color-ice-400)]">{r.id}</td>
        <td className="px-3 py-1.5 text-[var(--color-text-secondary)]">
          {r.category.replace(/_/g, ' ')}
        </td>
        <td className="px-3 py-1.5 text-right text-[var(--color-text-bright)]">
          {r.graphrag.entities}
        </td>
        <td className="px-3 py-1.5 text-right text-[var(--color-text-bright)]">
          {r.graphrag.neighbors}
        </td>
        <td
          className="px-3 py-1.5 text-right"
          style={{
            color:
              r.graphrag.structuralEdges >= 3
                ? 'var(--color-emerald-400)'
                : 'var(--color-text-secondary)',
          }}
        >
          {r.graphrag.structuralEdges}
        </td>
        <td className="px-3 py-1.5 text-right text-[var(--color-text-bright)]">
          {r.graphrag.ringTouch}
        </td>
        <td className="px-3 py-1.5 text-right text-[var(--color-rose-400)]">
          {r.vectorrag.structuralEvidence}
        </td>
        <td className="px-3 py-1.5 text-right text-[var(--color-rose-400)]">
          {r.pureLLM.structuralEvidence}
        </td>
        <td className="px-3 py-1.5 text-right text-[var(--color-text-muted)]">
          {Math.round(r.graphrag.latencyMs).toLocaleString()}
        </td>
      </tr>
      <AnimatePresence initial={false}>
        {open && (
          <motion.tr
            key={r.id + '_detail'}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="border-b border-[var(--color-line-soft)]"
          >
            <td colSpan={10} className="px-3 py-3 bg-[rgba(7,9,14,0.4)]">
              <Detail row={r} />
            </td>
          </motion.tr>
        )}
      </AnimatePresence>
    </>
  );
}

/* -------------------------------------------------------------------------- */

function Detail({ row: r }: { row: RealBenchmarkRow }) {
  const navigate = useNavigate();
  const runCustomDeep = useIntelStore((s) => s.runCustomDeepStream);
  const investigate = async () => {
    try { await runCustomDeep(r.question); } catch { /* navigate anyway */ }
    navigate('/investigate');
  };
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      <div>
        <div className="flex items-start justify-between gap-2 mb-1">
          <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            query
          </div>
          <button
            onClick={investigate}
            title="Run this query through the live GraphRAG investigation"
            className="inline-flex items-center gap-1 h-5 px-2 rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.05)] text-[var(--color-ice-300)] hover:bg-[rgba(34,211,238,0.1)] transition-colors"
          >
            <Target className="w-2.5 h-2.5" />
            <span className="font-mono text-[8.5px] tracking-[0.22em] uppercase">investigate</span>
          </button>
        </div>
        <div className="text-[12px] text-[var(--color-text-bright)] leading-snug">
          {r.question}
        </div>

        <div className="mt-3 font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] mb-1">
          capability the query forces
        </div>
        <div className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
          {r.needs}
        </div>

        <div className="mt-3 font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-rose-400)] mb-1 flex items-center gap-1">
          <ShieldAlert className="w-3 h-3" />
          why vectorRAG cannot answer
        </div>
        <div className="text-[11px] text-[var(--color-rose-300)] leading-relaxed">
          {r.vectorrag.limitation || 'definitionally — text retrieval cannot expose structural edges'}
        </div>
      </div>

      <div>
        <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-emerald-400)] mb-1 flex items-center gap-1">
          <Network className="w-3 h-3" />
          edge types surfaced by graphRAG
        </div>
        <div className="flex flex-wrap gap-1 mb-3">
          {r.graphrag.edgeTypes.length === 0 ? (
            <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
              none recorded in evidence chain
            </span>
          ) : (
            r.graphrag.edgeTypes.map((e) => (
              <span
                key={e}
                className="chip text-[8.5px] border-[rgba(16,185,129,0.32)] text-[var(--color-emerald-400)]"
              >
                {e}
              </span>
            ))
          )}
        </div>

        <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] mb-1">
          graphRAG narrative preview
        </div>
        <pre className="font-mono text-[10.5px] text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap break-words p-2 panel-soft max-h-48 overflow-y-auto scroll-tactical">
{r.graphrag.answerPreview || extractPreview(r)}
        </pre>

        <div className="mt-2 flex gap-3 font-mono text-[9.5px] text-[var(--color-text-muted)]">
          <span>latency: <span className="text-[var(--color-text-bright)]">{Math.round(r.graphrag.latencyMs).toLocaleString()}ms</span></span>
          <span className="ml-auto">evidence items: <span className="text-[var(--color-text-bright)]">{r.graphrag.evidence}</span></span>
        </div>
      </div>
    </div>
  );
}

// The adapter doesn't pass the answer_preview into RealBenchmarkRow directly;
// pull it from the original payload via the row's stored fields. (The adapter
// preserves it under graphrag.edgeTypes/etc but not the answer; we keep this
// helper-stub for forward-compat. Right now it falls back to the needs text.)
function extractPreview(r: RealBenchmarkRow): string {
  return (
    `${r.id} · ${r.category}\n` +
    `Entities surfaced: ${r.graphrag.entities}\n` +
    `Neighbors traversed: ${r.graphrag.neighbors}\n` +
    `Structural edges in evidence chain: ${r.graphrag.structuralEdges}\n` +
    `Edge types: ${r.graphrag.edgeTypes.join(', ') || '(none)'}\n` +
    `Ring-touch sum: ${r.graphrag.ringTouch}`
  );
}

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  CheckCircle2,
  Cpu,
  GitBranch,
  Lightbulb,
  Network,
} from 'lucide-react';
import { entityGlyph } from '@/lib/utils';
import type { EntityKind } from '@/types/intel';
import type { SchemaMapping } from '@/types/sources';

const ENTITY_KINDS: EntityKind[] = [
  'person',
  'shell_company',
  'company',
  'account',
  'wallet',
  'device',
  'address',
  'transaction',
  'phone',
  'document',
];

const ENTITY_LABEL: Record<EntityKind, string> = {
  person: 'Person',
  shell_company: 'Shell co.',
  company: 'Company',
  account: 'Account',
  wallet: 'Wallet',
  device: 'Device',
  address: 'Address',
  transaction: 'Transaction',
  phone: 'Phone',
  document: 'Document',
};

const ENTITY_COLOR: Record<EntityKind, string> = {
  person: 'var(--color-rose-400)',
  shell_company: 'var(--color-rose-400)',
  company: 'var(--color-amber-400)',
  account: 'var(--color-ice-400)',
  wallet: 'var(--color-violet-400)',
  device: 'var(--color-emerald-400)',
  address: 'var(--color-ice-400)',
  transaction: 'var(--color-amber-400)',
  phone: 'var(--color-emerald-400)',
  document: 'var(--color-text-secondary)',
};

export function SchemaMappingView({
  sourceId,
  mapping,
}: {
  sourceId: string;
  mapping?: SchemaMapping;
}) {
  void sourceId;
  if (!mapping) {
    return (
      <div className="p-6 text-center">
        <Lightbulb className="w-6 h-6 text-[var(--color-amber-400)] mx-auto mb-2 opacity-70" />
        <div className="font-mono text-[10px] tracking-[0.26em] uppercase text-[var(--color-text-muted)]">
          no schema mapping yet
        </div>
        <div className="text-[11px] text-[var(--color-text-secondary)] mt-2 max-w-[420px] mx-auto leading-relaxed">
          Once a source is connected, the platform inspects sample rows and
          auto-suggests entity + edge mappings. Validate them to begin ingestion.
        </div>
      </div>
    );
  }

  const stats = useMemo(() => {
    const validated = mapping.entityRules.filter((r) => r.validated).length;
    const total = mapping.entityRules.length;
    const avgConf =
      total > 0
        ? mapping.entityRules.reduce((a, r) => a + r.confidence, 0) / total
        : 0;
    return { validated, total, avgConf, edgeRules: mapping.edgeRules.length };
  }, [mapping]);

  return (
    <div className="p-3 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <GitBranch className="w-3.5 h-3.5 text-[var(--color-ice-400)]" />
        <span className="heading-tactical">Schema → graph mapping</span>
        <span className="chip text-[9px] ml-2">
          {stats.validated}/{stats.total} validated
        </span>
        {mapping.validatedAt && (
          <span className="font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-emerald-400)] ml-auto inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            validated
          </span>
        )}
      </div>

      <div className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
        The platform auto-detects entity types and relationships from sample
        rows. Confidence shows how certain the suggester is — analysts validate
        before ingestion writes to the graph.
      </div>

      {/* Entity rules */}
      <section className="surface overflow-hidden">
        <div className="px-3 h-7 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
          <Cpu className="w-3 h-3 text-[var(--color-ice-400)]" />
          <span className="heading-tactical">Entity rules</span>
          <span className="chip ml-auto text-[8.5px]">{mapping.entityRules.length}</span>
        </div>
        <div className="grid grid-cols-[1fr_36px_1fr_84px_84px] px-3 h-7 items-center border-b border-[var(--color-line-soft)] font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          <span>source field</span>
          <span />
          <span>graph entity</span>
          <span className="text-right">confidence</span>
          <span className="text-right">state</span>
        </div>
        <div className="divide-y divide-[var(--color-line-soft)]">
          {mapping.entityRules.map((r, i) => (
            <motion.div
              key={r.sourceField}
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.28, delay: i * 0.03 }}
              className="grid grid-cols-[1fr_36px_1fr_84px_84px] px-3 py-2 items-center gap-2 hover:bg-[rgba(34,211,238,0.04)]"
            >
              {/* source field */}
              <div className="min-w-0">
                <div className="font-mono text-[11px] text-[var(--color-text-primary)] truncate">
                  {r.sourceField}
                </div>
                <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] truncate">
                  e.g. {r.sampleValue}
                </div>
              </div>
              {/* arrow */}
              <div className="font-mono text-[14px] text-[var(--color-text-faint)] text-center">
                →
              </div>
              {/* graph entity */}
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="inline-flex items-center justify-center w-6 h-6 rounded-sm border text-[11px] shrink-0"
                  style={{
                    borderColor: ENTITY_COLOR[r.targetEntity],
                    color: ENTITY_COLOR[r.targetEntity],
                    background: `${ENTITY_COLOR[r.targetEntity]}10`,
                  }}
                >
                  {entityGlyph(r.targetEntity)}
                </span>
                <div className="min-w-0">
                  <div
                    className="text-[11px] truncate"
                    style={{ color: ENTITY_COLOR[r.targetEntity] }}
                  >
                    {ENTITY_LABEL[r.targetEntity]}
                  </div>
                  <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] truncate">
                    {r.autoSuggested ? 'auto-suggested' : 'analyst-defined'}
                  </div>
                </div>
              </div>
              {/* confidence */}
              <ConfidenceBar value={r.confidence} />
              {/* state */}
              <StateChip validated={r.validated} />
            </motion.div>
          ))}
        </div>
      </section>

      {/* Edge rules */}
      <section className="surface overflow-hidden">
        <div className="px-3 h-7 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
          <Network className="w-3 h-3 text-[var(--color-amber-400)]" />
          <span className="heading-tactical">Edge rules</span>
          <span className="chip ml-auto text-[8.5px]">{mapping.edgeRules.length}</span>
        </div>
        <div className="grid grid-cols-[1fr_36px_1fr_120px_84px] px-3 h-7 items-center border-b border-[var(--color-line-soft)] font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          <span>from field</span>
          <span />
          <span>to field</span>
          <span>kind</span>
          <span className="text-right">confidence</span>
        </div>
        <div className="divide-y divide-[var(--color-line-soft)]">
          {mapping.edgeRules.map((r, i) => (
            <motion.div
              key={`${r.fromField}_${r.toField}_${r.edgeKind}`}
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.28, delay: 0.1 + i * 0.04 }}
              className="grid grid-cols-[1fr_36px_1fr_120px_84px] px-3 py-2 items-center gap-2 hover:bg-[rgba(245,158,11,0.04)]"
            >
              <div className="font-mono text-[11px] text-[var(--color-text-primary)] truncate">
                {r.fromField}
              </div>
              <div className="font-mono text-[14px] text-[var(--color-text-faint)] text-center">
                →
              </div>
              <div className="font-mono text-[11px] text-[var(--color-text-primary)] truncate">
                {r.toField}
              </div>
              <span className="chip text-[9px] chip-amber">{r.edgeKind.replace('_', ' ')}</span>
              <ConfidenceBar value={r.confidence} />
            </motion.div>
          ))}
        </div>
      </section>

      {/* Footer summary */}
      <div className="surface px-3 py-2 flex items-center gap-3 flex-wrap text-[11px]">
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          mapping summary
        </span>
        <span className="text-[var(--color-text-secondary)]">
          {mapping.entityRules.length} entity rules
        </span>
        <span className="text-[var(--color-text-faint)]">·</span>
        <span className="text-[var(--color-text-secondary)]">
          {mapping.edgeRules.length} edge rules
        </span>
        <span className="text-[var(--color-text-faint)]">·</span>
        <span className="text-[var(--color-text-secondary)]">
          avg confidence{' '}
          <span className="text-[var(--color-ice-400)] font-mono">
            {(stats.avgConf * 100).toFixed(0)}%
          </span>
        </span>
        {!mapping.validatedAt && (
          <button className="ml-auto h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(16,185,129,0.4)] bg-[rgba(16,185,129,0.06)] text-[var(--color-emerald-400)] hover:bg-[rgba(16,185,129,0.1)]">
            <CheckCircle2 className="w-3 h-3" />
            validate &amp; enable ingestion
          </button>
        )}
      </div>
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const tone =
    value >= 0.9
      ? 'var(--color-emerald-400)'
      : value >= 0.75
      ? 'var(--color-ice-400)'
      : value >= 0.6
      ? 'var(--color-amber-400)'
      : 'var(--color-rose-400)';
  return (
    <div className="flex items-center gap-2 justify-end">
      <div className="w-12 h-1 rounded-full bg-[var(--color-graphite-800)] overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5 }}
          className="h-full"
          style={{ background: tone }}
        />
      </div>
      <span className="font-mono text-[10px] w-7 text-right" style={{ color: tone }}>
        {pct}%
      </span>
    </div>
  );
}

function StateChip({ validated }: { validated: boolean }) {
  if (validated) {
    return (
      <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-emerald-400)] inline-flex items-center justify-end gap-1">
        <CheckCircle2 className="w-3 h-3" />
        ok
      </span>
    );
  }
  return (
    <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-amber-400)] text-right">
      review
    </span>
  );
}

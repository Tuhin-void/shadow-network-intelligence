/**
 * Benchmark adapter — backend real benchmark artifacts → frontend
 * RealBenchmarkSummary shape.
 *
 * Hard constraint: this file performs PROJECTION ONLY. It never invents,
 * computes, or interpolates numbers. Every field returned originates in
 * the underlying JSON artifact produced by `scripts/adversarial_benchmark.py`
 * (or the reliability / TG validator scripts).
 */

import type {
  BackendAdversarialBenchmark,
  BackendAdversarialQuery,
  BackendQuantitativeBenchmark,
  BackendReliability,
} from '@/lib/api-client';

export interface RealBenchmarkRow {
  id: string;
  category: string;
  question: string;
  /** What capability the query forces — text from the benchmark JSON. */
  needs: string;
  graphrag: {
    entities: number;
    neighbors: number;
    evidence: number;
    structuralEdges: number;
    ringTouch: number;
    latencyMs: number;
    edgeTypes: string[];
    answerPreview: string;
  };
  vectorrag: {
    /** Structural edges reachable by chunked text retrieval. Always 0 by definition. */
    structuralEvidence: number;
    keywordDocHits: number;
    limitation: string;
  };
  pureLLM: {
    structuralEvidence: number;
    retrieval: string;
  };
}

export interface RealBenchmarkSummary {
  profile: string;
  generatedAt: number;
  queryCount: number;
  rows: RealBenchmarkRow[];
  aggregate: {
    queriesWithStructuralEvidence: number;
    totalNeighborsTraversed: number;
    totalStructuralEdges: number;
    avgLatencyMs: number;
    vectorragStructuralTotal: number;
    pureLLMStructuralTotal: number;
  };
}

export interface RealReliability {
  verdict: 'STABLE' | 'ACCEPTABLE' | 'DEGRADED' | 'OFFLINE' | string;
  queriesRun: number;
  trialsPerQuery: number;
  structuralDrift: number;
  latencyOutliers: number;
  emptyAnswers: number;
  latencyTolerancePct: number;
  issues: string[];
}

export interface RealTigerGraphSnapshot {
  status: string;
  vertexTotal: number;
  edgeTotal: number;
  reverseEdgesObserved: number;
  ringsWithMembers: number;
  ringsSampled: number;
}

export interface RealBenchmarkBundle {
  adversarial: RealBenchmarkSummary | null;
  reliability: RealReliability | null;
  tigergraph: RealTigerGraphSnapshot | null;
  /** Per-section presence flags + commands to regenerate missing pieces. */
  artifactsPresent: { adversarial: boolean; reliability: boolean; tigergraph: boolean };
  scriptsToRegenerate: Record<string, string>;
}

/* -------------------------------------------------------------------------- */
/* Quantitative comparison (3-pipeline side-by-side)                          */
/* -------------------------------------------------------------------------- */

export type PipelineKey = 'pure_llm' | 'vector_rag' | 'graph_rag';

export interface PipelineAggregate {
  approach: PipelineKey;
  queries: number;
  errors: number;
  avgTotalTokens: number;
  avgPromptTokens: number;
  avgCompletionTokens: number;
  /** Mock-LLM placeholder — not real model latency. */
  avgLatencyMs: number;
  /** REAL retrieval cost measured end-to-end. */
  avgRetrievalMs: number;
  avgSourcesRetrieved: number;
  /** Real total $ for all queries in this pipeline (pricing from TokenTracker). */
  totalCost: number;
  /** Real avg $ per query. */
  avgCost: number;
  /** Ratio (0..1) of tokens reduction vs the heaviest pipeline. */
  tokenReductionVsHeaviest: number;
  /** Optional scoring aggregates — present iff the run included evaluations. */
  scoring: PipelineScoring | null;
}

export interface PipelineScoring {
  nEvaluated: number;
  judgeOverall: number;     // 1..5
  judgeRelevance: number;
  judgeAccuracy: number;
  judgeCompleteness: number;
  judgeHallucination: number;  // 1..5, where 5 = no hallucinations
  judgeClarity: number;
  judgePassRate: number;    // 0..1, fraction where overall >= 4
  hallucinationResistanceRate: number;  // 0..1
  entityF1: number;
  entityPrecision: number;
  entityRecall: number;
  entityPathCoverage: number;
  semanticScore: number;
  overallAccuracy: number;
  failureCounts: Record<string, number>;
}

export interface QuantitativeBenchmark {
  runId: string;
  timestamp: string;
  profile: string;
  queriesRun: number;
  pipelines: PipelineAggregate[];
  structural: null | {
    queries: number;
    graphRag: number;
    vectorRag: number;
    pureLLM: number;
    totalStructuralEdges: number;
    totalNeighbors: number;
  };
  scoring: { enabled: boolean; semanticMethods: string[] } | null;
  /** Honest disclosures from the backend (latency-is-mock, etc.). */
  disclosure: Record<string, string>;
}

/* -------------------------------------------------------------------------- */

export function transformAdversarialBenchmark(
  b: BackendAdversarialBenchmark,
): RealBenchmarkSummary {
  return {
    profile: b.profile,
    generatedAt: b.generated_at,
    queryCount: b.query_count,
    rows: (b.queries ?? []).map(transformAdversarialRow),
    aggregate: {
      queriesWithStructuralEvidence: b.aggregate?.queries_with_structural_evidence ?? 0,
      totalNeighborsTraversed:       b.aggregate?.total_neighbors_traversed ?? 0,
      totalStructuralEdges:          b.aggregate?.total_structural_edges ?? 0,
      avgLatencyMs:                  b.aggregate?.avg_latency_ms ?? 0,
      vectorragStructuralTotal:      b.aggregate?.vectorrag_structural_total ?? 0,
      pureLLMStructuralTotal:        b.aggregate?.pure_llm_structural_total ?? 0,
    },
  };
}

function transformAdversarialRow(q: BackendAdversarialQuery): RealBenchmarkRow {
  return {
    id:        q.id,
    category:  q.category,
    question:  q.question,
    needs:     q.needs_capability,
    graphrag: {
      entities:        q.graphrag.entities,
      neighbors:       q.graphrag.neighbors,
      evidence:        q.graphrag.evidence,
      structuralEdges: q.graphrag.structural_edges,
      ringTouch:       q.graphrag.ring_touch_sum,
      latencyMs:       q.graphrag.latency_ms,
      edgeTypes:       q.graphrag.edge_types ?? [],
      answerPreview:   q.graphrag.answer_preview ?? '',
    },
    vectorrag: {
      structuralEvidence: q.vectorrag_proxy.structural_signal,
      keywordDocHits:     q.vectorrag_proxy.keyword_doc_hits,
      limitation:         q.vectorrag_proxy.limitation,
    },
    pureLLM: {
      structuralEvidence: q.pure_llm.structural_signal,
      retrieval:          q.pure_llm.retrieval,
    },
  };
}

export function transformReliability(r: BackendReliability): RealReliability {
  return {
    verdict:              r.status,
    queriesRun:           r.queries_run,
    trialsPerQuery:       r.trials_per_query,
    structuralDrift:      r.structural_drift_count,
    latencyOutliers:      r.latency_outlier_count,
    emptyAnswers:         r.empty_answer_count,
    latencyTolerancePct:  r.latency_tolerance_pct,
    issues:               r.issues ?? [],
  };
}

export function transformTigergraph(
  tg: Record<string, unknown>,
): RealTigerGraphSnapshot {
  const ringProbe = (tg.ring_probe as unknown[] | undefined) ?? [];
  const rev = (tg.reverse_edges_observed as Record<string, unknown> | undefined) ?? {};
  return {
    status:               String(tg.status ?? '—'),
    vertexTotal:          Number(tg.vertex_total ?? 0),
    edgeTotal:            Number(tg.edge_total ?? 0),
    reverseEdgesObserved: Object.keys(rev).length,
    ringsWithMembers:     Number(tg.rings_with_members ?? 0),
    ringsSampled:         ringProbe.length,
  };
}

export function transformBenchmarkBundle(payload: {
  adversarial: BackendAdversarialBenchmark | null;
  reliability: BackendReliability | null;
  tigergraph: Record<string, unknown> | null;
  artifacts_present: { adversarial: boolean; reliability: boolean; tigergraph: boolean };
  scripts_to_regenerate: Record<string, string>;
}): RealBenchmarkBundle {
  return {
    adversarial: payload.adversarial ? transformAdversarialBenchmark(payload.adversarial) : null,
    reliability: payload.reliability ? transformReliability(payload.reliability) : null,
    tigergraph:  payload.tigergraph  ? transformTigergraph(payload.tigergraph)  : null,
    artifactsPresent: payload.artifacts_present,
    scriptsToRegenerate: payload.scripts_to_regenerate ?? {},
  };
}

export function transformQuantitativeBenchmark(
  q: BackendQuantitativeBenchmark,
): QuantitativeBenchmark {
  const pipelines: PipelineAggregate[] = (q.pipelines ?? []).map((p) => {
    // Scoring fields are only present when the run included evaluations.
    const hasScoring = p.n_evaluated != null && p.n_evaluated > 0;
    const scoring: PipelineScoring | null = hasScoring
      ? {
          nEvaluated:                  p.n_evaluated ?? 0,
          judgeOverall:                p.avg_judge_overall ?? 0,
          judgeRelevance:              p.avg_judge_relevance ?? 0,
          judgeAccuracy:               p.avg_judge_accuracy ?? 0,
          judgeCompleteness:           p.avg_judge_completeness ?? 0,
          judgeHallucination:          p.avg_judge_hallucination ?? 0,
          judgeClarity:                p.avg_judge_clarity ?? 0,
          judgePassRate:               p.judge_pass_rate ?? 0,
          hallucinationResistanceRate: p.hallucination_resistance_rate ?? 0,
          entityF1:                    p.avg_entity_f1 ?? 0,
          entityPrecision:             p.avg_entity_precision ?? 0,
          entityRecall:                p.avg_entity_recall ?? 0,
          entityPathCoverage:          p.avg_entity_path_coverage ?? 0,
          semanticScore:               p.avg_semantic_score ?? 0,
          overallAccuracy:             p.avg_accuracy ?? 0,
          failureCounts:               p.failure_counts ?? {},
        }
      : null;
    return {
      approach:               (p.approach as PipelineKey),
      queries:                p.queries ?? 0,
      errors:                 p.errors ?? 0,
      avgTotalTokens:         p.avg_total_tokens ?? 0,
      avgPromptTokens:        p.avg_prompt_tokens ?? 0,
      avgCompletionTokens:    p.avg_completion_tokens ?? 0,
      avgLatencyMs:           p.avg_latency_ms ?? 0,
      avgRetrievalMs:         p.avg_retrieval_ms ?? 0,
      avgSourcesRetrieved:    p.avg_sources_retrieved ?? 0,
      totalCost:              p.total_cost ?? 0,
      avgCost:                p.avg_cost ?? 0,
      tokenReductionVsHeaviest: (p.token_reduction_pct_vs_heaviest ?? 0) / 100,
      scoring,
    };
  });
  return {
    runId:       q.run_id,
    timestamp:   q.timestamp,
    profile:     q.profile,
    queriesRun:  q.queries_run ?? 0,
    pipelines,
    structural: q.structural
      ? {
          queries:              q.structural.queries,
          graphRag:             q.structural.graph_rag,
          vectorRag:            q.structural.vector_rag,
          pureLLM:              q.structural.pure_llm,
          totalStructuralEdges: q.structural.total_structural_edges,
          totalNeighbors:       q.structural.total_neighbors,
        }
      : null,
    scoring: q.scoring
      ? { enabled: q.scoring.enabled, semanticMethods: q.scoring.semantic_methods ?? [] }
      : null,
    disclosure: q.disclosure ?? {},
  };
}

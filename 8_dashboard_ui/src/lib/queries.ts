import type { PresetSnapshot } from '@/types/intel';

/**
 * Investigation queries — graph-native operations the analyst can dispatch.
 * Each query returns a "transform" — a description of how to set
 * focusMode + selection + surfaced sets to highlight the result on the graph.
 *
 * NOT a chatbot. Every query maps deterministically to a graph transformation.
 */

export type QueryKind =
  | 'trace_ownership_from'
  | 'isolate_ring'
  | 'show_hidden_to'
  | 'shortest_path'
  | 'follow_money_exit'
  | 'expand_offshore'
  | 'find_shared_infra'
  | 'reverse_edge_from_terminal';

export interface QueryTransform {
  focusMode?: 'overview' | 'rings' | 'hidden' | 'paths' | 'risk';
  selectEntityId?: string | null;
  surfacePaths?: string[];
  surfaceRings?: string[];
  discoverEntities?: string[];
  narrationLine: string | null;
}

export interface InvestigationQuery {
  id: string;
  kind: QueryKind;
  label: string;
  hint: string;
  /** which graph primitives this query consults — shown beneath the row */
  consults: string[];
}

/**
 * Generate the queries that make sense for the given preset.
 * Every preset gets the same 4 universal queries plus 1–3 preset-specific ones.
 */
export function queriesForPreset(p: PresetSnapshot): InvestigationQuery[] {
  const universal: InvestigationQuery[] = [
    {
      id: 'q_isolate_ring',
      kind: 'isolate_ring',
      label: 'Isolate detected ring',
      hint: `${p.rings.length} ring${p.rings.length === 1 ? '' : 's'} · cohesion ${p.rings[0]?.cohesion.toFixed(2) ?? '–'}`,
      consults: ['rings', 'cohesion', 'shared_infrastructure'],
    },
    {
      id: 'q_show_hidden',
      kind: 'show_hidden_to',
      label: 'Show hidden relationships',
      hint: `${p.hidden.length} hidden tie${p.hidden.length === 1 ? '' : 's'} via topology`,
      consults: ['hidden_link', 'topology_traversal', 'shared_signals'],
    },
    {
      id: 'q_trace_ownership',
      kind: 'trace_ownership_from',
      label: 'Trace ownership cascade',
      hint: `from seed ${p.seed}`,
      consults: ['owns', 'controls', 'authorizes'],
    },
    {
      id: 'q_path',
      kind: 'shortest_path',
      label: 'Surface all traversal paths',
      hint: `${p.paths.length} path${p.paths.length === 1 ? '' : 's'} · max ${
        Math.max(...p.paths.map((x) => x.hops))
      } hops`,
      consults: ['shortest_path', 'evidence_chain', 'reverse_edge'],
    },
  ];

  const presetSpecific: InvestigationQuery[] = [];
  const hasMoneyFlow = p.paths.some((path) => path.intent === 'evidence_chain');
  if (hasMoneyFlow) {
    presetSpecific.push({
      id: 'q_money',
      kind: 'follow_money_exit',
      label: 'Follow money to exit point',
      hint: 'evidence-chain path · transfers + wires',
      consults: ['transfers', 'wires_to', 'reverse_edge'],
    });
  }
  const hasReverse = p.paths.some((path) => path.intent === 'reverse_edge');
  if (hasReverse) {
    presetSpecific.push({
      id: 'q_reverse',
      kind: 'reverse_edge_from_terminal',
      label: 'Reverse-edge from terminal',
      hint: 'walk back from beneficiary',
      consults: ['reverse_edge', 'ownership_chain'],
    });
  }
  const hasShells = p.graph.entities.some((e) => e.kind === 'shell_company');
  if (hasShells) {
    presetSpecific.push({
      id: 'q_offshore',
      kind: 'expand_offshore',
      label: 'Expand offshore structure',
      hint: `${
        p.graph.entities.filter((e) => e.kind === 'shell_company').length
      } shell entities`,
      consults: ['shell_company', 'ownership_layering', 'jurisdictional_hops'],
    });
  }
  const hasSharedInfra = p.report.sharedInfrastructure.length > 0;
  if (hasSharedInfra) {
    presetSpecific.push({
      id: 'q_shared',
      kind: 'find_shared_infra',
      label: 'Find shared infrastructure',
      hint: `${p.report.sharedInfrastructure.length} shared assets`,
      consults: ['shares_device', 'shares_address', 'shares_phone'],
    });
  }

  return [...universal, ...presetSpecific];
}

export function runQuery(p: PresetSnapshot, query: InvestigationQuery): QueryTransform {
  switch (query.kind) {
    case 'isolate_ring': {
      const ring = p.rings[0];
      return {
        focusMode: 'rings',
        surfaceRings: ring ? [ring.id] : [],
        discoverEntities: ring?.members ?? [],
        selectEntityId: ring?.members[0] ?? null,
        narrationLine: ring
          ? `Isolated ring — ${ring.members.length} members · cohesion ${ring.cohesion.toFixed(2)}`
          : 'No ring to isolate',
      };
    }
    case 'show_hidden_to': {
      const ids = new Set<string>();
      p.hidden.forEach((h) => {
        ids.add(h.from);
        ids.add(h.to);
        h.via.forEach((v) => ids.add(v));
      });
      return {
        focusMode: 'hidden',
        discoverEntities: Array.from(ids),
        selectEntityId: p.hidden[0]?.from ?? null,
        narrationLine: `${p.hidden.length} hidden ties surfaced via topology traversal`,
      };
    }
    case 'trace_ownership_from': {
      const ownership = p.paths.filter((x) => x.intent === 'shortest_path');
      const all = new Set<string>();
      ownership.forEach((path) => path.nodes.forEach((n) => all.add(n)));
      return {
        focusMode: 'paths',
        surfacePaths: ownership.map((x) => x.id),
        discoverEntities: Array.from(all),
        selectEntityId: p.seed,
        narrationLine: `Ownership cascade traced from ${p.seed} · ${ownership.length} chain${
          ownership.length === 1 ? '' : 's'
        }`,
      };
    }
    case 'shortest_path': {
      const all = new Set<string>();
      p.paths.forEach((path) => path.nodes.forEach((n) => all.add(n)));
      return {
        focusMode: 'paths',
        surfacePaths: p.paths.map((x) => x.id),
        discoverEntities: Array.from(all),
        narrationLine: `${p.paths.length} traversal paths surfaced`,
      };
    }
    case 'follow_money_exit': {
      const money = p.paths.filter((x) => x.intent === 'evidence_chain');
      const all = new Set<string>();
      money.forEach((path) => path.nodes.forEach((n) => all.add(n)));
      return {
        focusMode: 'paths',
        surfacePaths: money.map((x) => x.id),
        discoverEntities: Array.from(all),
        selectEntityId: money[0]?.nodes.at(-1) ?? null,
        narrationLine: `Money flow traced to exit · ${money[0]?.hops ?? '?'} hops`,
      };
    }
    case 'expand_offshore': {
      const shells = p.graph.entities
        .filter((e) => e.kind === 'shell_company')
        .map((e) => e.id);
      return {
        focusMode: 'rings',
        discoverEntities: shells,
        selectEntityId: shells[0] ?? null,
        narrationLine: `${shells.length} shell entities expanded`,
      };
    }
    case 'find_shared_infra': {
      const ids = new Set<string>();
      p.report.sharedInfrastructure.forEach((h) => {
        ids.add(h.from);
        ids.add(h.to);
        h.via.forEach((v) => ids.add(v));
      });
      return {
        focusMode: 'hidden',
        discoverEntities: Array.from(ids),
        narrationLine: `${p.report.sharedInfrastructure.length} shared-infrastructure ties`,
      };
    }
    case 'reverse_edge_from_terminal': {
      const reverse = p.paths.filter((x) => x.intent === 'reverse_edge');
      const all = new Set<string>();
      reverse.forEach((path) => path.nodes.forEach((n) => all.add(n)));
      return {
        focusMode: 'paths',
        surfacePaths: reverse.map((x) => x.id),
        discoverEntities: Array.from(all),
        selectEntityId: reverse[0]?.nodes[0] ?? null,
        narrationLine:
          reverse.length > 0
            ? `Reverse-edge from terminal — collapses onto seed`
            : 'No reverse-edge available',
      };
    }
  }
}

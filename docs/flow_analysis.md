# Shadow Network Intelligence: End-to-End Data Flow Analysis

## Overview

The system has two main components working in sequence:

```
1_data_engine          generates          2_baseline_systems           evaluates
─────────────────     synthetic AML ──►  ────────────────────────►    3 pipelines
  [profiles]             data              [reads CSV/JSON]            [benchmarks]
  [generators]                             [builds docs]              [scores]
  [topology]                                [runs queries]
  [exporters]                              [reports]
```

---

## Stage 1: Data Generation (1_data_engine/)

**Entry point:** `1_data_engine/main.py` → `generate()`

```
main.py:generate(args)
    ├── Phase 1: EntityFactory.generate_all(config)
    ├── Phase 2: TopologyOrchestrator.inject_all(registry)
    ├── Phase 3: Validation
    │       ├── GraphIntegrityValidator.validate(registry)
    │       └── FraudRingValidator.validate(registry)
    └── Phase 4: Export
            ├── CSVExporter.export(registry, output_dir)   → 7 CSV files
            └── JSONExporter.export(registry, output_dir)  → 3 JSON files
```

**Output location:** `outputs/{profile}/` (e.g., `outputs/small/csv/`, `outputs/small/json/`)

---

### Phase 1: Entity Generation

**File:** `1_data_engine/generators/entity_factory.py`

```
EntityFactory(config)
    ├── _generate_addresses()           → AddressSchema × address_count
    │       └── AddressGenerator        → registry.add_address()
    ├── _generate_persons()             → PersonSchema × person_count
    │       └── PersonGenerator         → registry.add_person()
    ├── _generate_companies()           → CompanySchema × company_count
    │       └── CompanyGenerator        → registry.add_company()
    ├── _generate_accounts()            → AccountSchema × account_count
    │       └── AccountGenerator        → registry.add_account()
    │       └── EdgeBuilder.has_account() → HAS_ACCOUNT edge → registry.add_edge()
    └── _generate_baseline_transactions() → TransactionSchema × edge_target × 0.3
            └── TransactionGenerator    → registry.add_transaction()
            └── EdgeBuilder.account_transfer() → TRANSFERRED_TO edge → registry.add_edge()
```

**Schemas (what each entity contains):**

| Schema | File | Key Fields |
|--------|------|------------|
| `PersonSchema` | `schemas/person.py` | id, name, tax_id, nationality, risk_score, is_pep, is_sanctioned, is_watched, is_mule |
| `CompanySchema` | `schemas/company.py` | id, name, ein, industry, company_type, incorporation_date, is_offshore, is_shell, risk_score |
| `AccountSchema` | `schemas/account.py` | id, account_number, owner_id, owner_type, balance, account_type, risk_score, velocity_score |
| `AddressSchema` | `schemas/address.py` | id, street_address, city, state, country, address_type, is_shell_location, risk_score |
| `TransactionSchema` | `schemas/transaction.py` | id, from_account, to_account, amount, currency, transaction_type, status, is_suspicious, risk_score |
| `EdgeSchema` | `schemas/edge.py` | id, from_id, from_type, to_id, to_type, relationship, weight, is_fraud_related, fraud_ring_id |

**Profiles (`orchestration/profiles.py`):**

| Profile | Persons | Companies | Accounts | Addresses | Transactions | Fraud Rings |
|---------|---------|-----------|----------|-----------|-------------|-------------|
| `small` | 300 | 200 | 400 | 100 | 5,000 | 3 |
| `medium` | 3,000 | 2,000 | 4,000 | 1,000 | 50,000 | 8 |
| `large` | 30,000 | 20,000 | 40,000 | 10,000 | 500,000 | 30 |
| `hackathon_default` | 6,000 | 5,000 | 10,000 | 4,000 | 50,000 | 15 |

---

### Phase 2: Fraud Topology Injection

**File:** `1_data_engine/topology/orchestrator.py` → `inject_all(registry)`

Runs 12 injectors in sequence. Each injector:
- Creates fraud-ring-scoped edges (with `fraud_ring_id` set)
- Creates `FraudRingSchema` objects → `registry.add_fraud_ring()`

```
TopologyOrchestrator(seed).inject_all(registry)
    ├── CircularOwnershipInjector   → OWNS edges between shell companies + FR-CIRC-XX
    ├── FunnelAccountInjector       → TRANSFERRED_TO edges + FR-FUNNEL-XX
    ├── SmurfingInjector            → Sub-$10K transactions + TRANSFERRED_TO + FR-SMURF-XX
    ├── LaunderingChainInjector     → Multi-hop TRANSFERRED_TO + FR-LAYER-XX
    ├── AddressCollisionInjector    → LOCATED_AT edges + FR-ADDR-XX
    ├── OffshoreRoutingInjector     → Offshore transfers + FR-OFFSHORE-XX
    ├── CentralHubInjector          → Hub connections + FR-HUB-XXX
    ├── DormantBurstInjector        → Burst transactions + FR-DORMANT-XX
    ├── BeneficialOwnershipInjector → BENEFICIAL_OWNER_OF + OWNS + FR-BENEF-XX
    ├── SemanticTrapInjector        → Noise companies + FR-TRAP-XX
    ├── HybridNetworkInjector       → Combined patterns + FR-HYBRID-XX
    └── TemporalSpikeInjector       → Rapid transactions + FR-SPIKE-XX
```

**FraudRingSchema** (`schemas/fraud_ring.py`):
```
FraudRingBuilder:
    build_circular_ownership()      → FR-CIRC-XX, CIRCULAR_OWNERSHIP
    build_funnel_account()           → FR-FUNNEL-XX, FUNNEL_ACCOUNT
    build_laundering_chain()          → FR-LAYER-XX, LAYERING_CHAIN
    build_address_collision()        → FR-ADDR-XX, SHARED_ADDRESS
    build_semantic_trap()            → FR-TRAP-XX, SEMANTIC_TRAP
```

**Edge types created by topology (`edges/edge_factory.py`):**

| Method | From | To | Relationship |
|--------|------|-----|--------------|
| `owns()` | Person | Company | OWNS |
| `company_owns_company()` | Company | Company | OWNS |
| `has_account()` | Owner | Account | HAS_ACCOUNT |
| `transferred_to()` | Account | Account | TRANSFERRED_TO |
| `located_at()` | Entity | Address | LOCATED_AT |
| `uses_device()` | Person | Device | USES_DEVICE |
| `accessed_from()` | Account | Device | ACCESSED_FROM |
| `associated_with()` | Entity | Entity | ASSOCIATED_WITH |
| `shares_device_with()` | Person | Person | SHARES_DEVICE_WITH |
| `shares_address_with()` | Entity | Address | SHARES_ADDRESS_WITH |
| `controls()` | Person | Company | CONTROLS |
| `director_of()` | Person | Company | DIRECTOR_OF |
| `benefits_from()` | Company | Company | BENEFITS_FROM |

---

### Phase 3: Validation

**File:** `1_data_engine/validators/`

```
GraphIntegrityValidator.validate(registry)
    └── Checks: no orphaned edges, no duplicates
    └── Returns: IntegrityReport { valid, entity_count, edge_count }

FraudRingValidator.validate(registry)
    └── Checks: each ring's entities exist, traversal paths valid
    └── Returns: FraudRingReport { valid_rings, total_rings }
```

---

### Phase 4: Export

#### CSV Exporter (`exporters/csv_exporter.py`)

```
CSVExporter.export(registry, output_dir)
    ├── _export_persons()        → outputs/{profile}/csv/persons.csv
    ├── _export_companies()     → outputs/{profile}/csv/companies.csv
    ├── _export_accounts()      → outputs/{profile}/csv/accounts.csv
    ├── _export_addresses()     → outputs/{profile}/csv/addresses.csv
    ├── _export_edges()         → outputs/{profile}/csv/edges.csv
    ├── _export_fraud_rings()   → outputs/{profile}/csv/fraud_rings.csv
    └── _export_transactions()  → outputs/{profile}/csv/transactions.csv  [NEW]
```

**`transactions.csv` columns:**
```
id, from_account, to_account, amount, currency, transaction_type,
status, timestamp, description, reference, is_suspicious, risk_score,
is_layering, is_placement, is_integration, is_structuring, is_smurfing, fraud_ring_id
```

#### JSON Exporter (`exporters/json_exporter.py`)

```
JSONExporter.export(registry, output_dir)
    ├── _export_graph()         → outputs/{profile}/json/graph.json
    │       └── Contains: { entities: {persons, companies, accounts, addresses},
    │                       transactions: [...],   ← [NEW]
    │                       edges: [...] }
    ├── _export_fraud_rings()   → outputs/{profile}/json/fraud_rings.json
    │       └── Dict keyed by ring ID (FR-CIRC-00, FR-FUNNEL-00, etc.)
    └── _export_metadata()       → outputs/{profile}/json/metadata.json
```

---

## Stage 2: Data Loading (2_baseline_systems/)

**Entry point:** `2_baseline_systems/shared/data_loader.py` → `AdaptiveDataLoader`

```
AdaptiveDataLoader(profile='hackathon_default')
    └── load(force_regenerate=False)
            ├── If output_dir missing → _run_data_engine()
            │       └── Runs: python3 -m 1_data_engine.main generate --profile X --seed 42
            │
            └── _load_from_outputs()
                    │
                    ├── Read CSVs (if csv_dir exists):
                    │       ├── persons.csv       → dataset.persons
                    │       ├── companies.csv     → dataset.companies
                    │       ├── accounts.csv      → dataset.accounts
                    │       ├── addresses.csv     → dataset.addresses
                    │       ├── edges.csv         → dataset.edges
                    │       ├── devices.csv       → dataset.devices (if present)
                    │       └── transactions.csv  → dataset.transactions  [NEW - prioritized]
                    │
                    ├── Read JSON (if json_dir exists):
                    │       ├── graph.json        → transactions fallback, entity enrichment
                    │       ├── fraud_rings.json  → fraud ring metadata (dict keyed by ring ID)
                    │       └── metadata.json     → counts summary
                    │
                    ├── Merge fraud rings (CSV + JSON):
                    │       ├── CSV: id, name, type, severity, entity_count, edge_count, key_entities (comma-sep string)
                    │       └── JSON: entities (list), traversal_paths (list), ring_type, description, key_entities (list)
                    │       └── Result: list of fraud rings with merged fields
                    │
                    ├── Transaction derivation (if no transactions.csv):
                    │       └── 1_data_engine v1 had no transactions.csv export
                    │       └── If dataset.transactions empty and edges exist:
                    │               └── Derives up to 50,000 transactions from TRANSFERRED_TO edges
                    │               └── Each edge becomes: { id: TX-NNNNNNNN, from_account, to_account,
                    │                                        amount, is_suspicious, fraud_ring_id, ... }
                    │
                    └── _compute_graph_metadata(dataset)
                            └── Returns: GraphMetadata with entity counts, density, avg_degree
```

**Output schema (`shared/schemas.py`):**

```
ShadowDataset:
    persons:       list[dict]       # from persons.csv
    companies:     list[dict]       # from companies.csv
    accounts:      list[dict]       # from accounts.csv
    addresses:     list[dict]       # from addresses.csv
    devices:       list[dict]       # from devices.csv
    transactions:  list[dict]       # from transactions.csv (NEW) or derived
    edges:         list[dict]       # from edges.csv
    fraud_rings:   list[dict]       # merged CSV + JSON
    graph_metadata: GraphMetadata   # computed stats

    get_entity_by_id(entity_id)     # O(n) scan, prefix-based collection selection
    get_edges_for_entity(entity_id)  # O(1) via lazy hash index
    get_transaction_chain(from, to)  # BFS traversal via TRANSFERRED_TO edges
    to_graph_summary()              # dict of entity counts
```

---

## Stage 3: Document Building (2_baseline_systems/)

**Entry point:** `2_baseline_systems/shared/document_builder.py` → `DocumentBuilder.build_all()`

```
DocumentBuilder(dataset, chunk_size=500, chunk_overlap=50)
    └── build_all()
            ├── _build_entity_profiles()
            │       ├── For each person  → _person_to_doc(person)
            │       ├── For each company → _company_to_doc(company)
            │       ├── For each account → _account_to_doc(account)
            │       └── For each address → _address_to_doc(address)
            │
            ├── _build_transaction_docs()
            │       └── Top 5,000 transactions → _transaction_to_doc(tx)
            │               (uses dataset.get_edges_for_entity for account context)
            │
            └── _build_authored_docs()
                    └── Top 100 fraud rings → _fraud_ring_to_doc(ring)
                            (generates human-readable summary from ring metadata)

    └── Each method returns Document(id, text, metadata):
            Document:
                id:      "entity::{entity_id}" | "tx::{tx_id}" | "ring::{ring_id}"
                text:    Human-readable natural language description
                metadata: { doc_type, entity_type, risk_score, fraud_ring_id, ... }
```

**Performance:** With 160K edges, `get_edges_for_entity()` uses lazy O(1) hash index. Building 30K docs from 25K entities takes ~150ms.

**Chunks created per entity:**
- Entity profiles: 1 doc each (no chunking at entity level)
- Transactions: 1 doc each, up to 5,000 total
- Fraud rings: 1 doc each, up to 100 total

---

## Stage 4: Benchmark Execution (2_baseline_systems/)

**Entry point:** `2_baseline_systems/benchmarking/runner.py` → `BenchmarkRunner.run()`

```
BenchmarkRunner(profile, config)
    ├── __init__
    │       ├── AdaptiveDataLoader(profile)
    │       ├── LLMClient(provider='mock', ...)      # default: mock for offline
    │       ├── Embedder(provider='mock', ...)        # default: mock for offline
    │       ├── TokenTracker(model=...)
    │       ├── VectorStore(provider='mock', ...)     # default: mock for offline
    │       ├── RetrievalCache(max_size=1000)
    │       ├── QueryLoader(data_loader)
    │       └── DifficultyTierClassifier()
    │
    └── run(queries, approaches, ...)
            │
            ├── QueryLoader.load_queries(tier=None)
            │       ├── _generate_from_fraud_rings(dataset)
            │       │       ├── For each fraud ring:
            │       │       │   ├── TRAVERSAL query: "Find all entities connected to {entity}"
            │       │       │   ├── IDENTIFY query: "Identify fraud ring containing {entity}"
            │       │       │   └── PATH query: "Trace fund flow from {src} to {dst}"
            │       │       └── Ground truth: key_entities, traversal_paths, ring_type
            │       │       └── Tier: 1-5 based on ring_type, complexity, entity_count
            │       │
            │       ├── _generate_synthetic_queries(dataset)
            │       │       ├── Tier 2: Offshore company query, money mule query
            │       │       └── Tier 3: High-velocity account query
            │       │
            │       └── Returns: list[BenchmarkQuery]
            │               BenchmarkQuery:
            │                   id, question, tier, ground_truth_entities,
            │                   expected_paths, fraud_ring_id, complexity
            │
            ├── _init_pipelines()
            │       ├── "pure_llm"      → PureLLMPipeline(llm, tokens, data_loader)
            │       ├── "vector_rag"     → VectorRAGPipeline(llm, tokens, data_loader, vector_store, embedder)
            │       └── "graph_rag"      → GraphRAGPipeline(llm, tokens, data_loader, embedder=embedder)
            │
            ├── For each query:
            │       ├── If parallel: ThreadPoolExecutor submits all pipelines
            │       └── Else: sequential calls to pipeline.answer(question)
            │
            ├── Collect results: dict[approach] → list[PipelineResult]
            │
            └── Save to: 2_baseline_systems/outputs/benchmark_results/benchmark_{run_id}.json
                    BenchmarkRun:
                        run_id, timestamp, dataset_hash, profile,
                        queries_loaded, queries_run, results{approach: [PipelineResult]}
```

---

## Stage 5: The Three Pipelines

### Pipeline 1: Pure LLM (`pipelines/pure_llm.py`)

```
PureLLMPipeline.answer(question)
    └── No retrieval whatsoever
            ├── Gets graph summary: { person_count, company_count, ... }
            ├── Builds prompt:
            │   ├── System: "You are a financial crime intelligence analyst..."
            │   ├── Context: "Dataset overview: {counts}"
            │   └── Question: {question}
            ├── llm.generate(prompt, temperature=0.0, max_tokens=2048)
            │       ├── Ollama: POST /api/generate
            │       ├── OpenAI: chat.completions.create
            │       ├── Anthropic: messages.create
            │       └── Mock: token count estimate + "[MOCK] ..." text
            │
            └── _parse_response(response)
                    └── PipelineResult:
                            approach: "pure_llm"
                            answer: LLM text
                            sources: []         (none)
                            latency_ms: ms from LLM
                            retrieval_ms: 0
                            prompt/completion/total_tokens
                            retrieval_trace.strategy: "none"
```

**Token cost:** Highest of all pipelines (no context narrowing)

---

### Pipeline 2: Vector RAG (`pipelines/vector_rag.py`)

```
VectorRAGPipeline(llm, tokens, data_loader, vector_store, embedder, top_k=10)
    ├── _ensure_indexed()  [one-time on first call]
    │       ├── DocumentBuilder.build_all() → 30K docs
    │       └── vector_store.index_documents(docs, embedder)
    │               ├── Mock provider: embed each doc, store in _mock_docs list
    │               └── ChromaDB provider: embed_batch → upsert to collection
    │
    └── answer(question)
            ├── embedder.embed(question) → query_embedding
            │       ├── Ollama: POST /api/embeddings
            │       ├── OpenAI: embeddings.create
            │       └── Mock: deterministic random vector, cached by MD5 hash
            │
            ├── vector_store.search(query_embedding, top_k=10)
            │       ├── Mock: dot product similarity → top-k
            │       └── ChromaDB: collection.query(n_results=top_k)
            │
            ├── Build sources: [ {id, doc_type, entity_id, distance, text}, ... ]
            ├── Build RetrievalTrace:
            │       ├── strategy: "vector_search"
            │       ├── retrieved_chunks: sources
            │       └── total_retrieved: k
            │
            ├── _format_context(sources)
            │       └── "=== CONTEXT (k sources) ===\n[Source 1] (entity::X, relevance: 0.87):\n{text}\n..."
            │
            ├── _build_prompt(question, context) → system + user_prompt
            ├── llm.generate(prompt + context, ...)
            │
            └── _parse_response() → PipelineResult
                    retrieval_ms: embedding + search time
                    sources: top-k chunks with distances
```

**Token cost:** Lower than Pure LLM (retrieved context narrows prompt)

---

### Pipeline 3: Graph RAG (`pipelines/graph_rag.py`)

```
GraphRAGPipeline(llm, tokens, data_loader, graph_retriever=None, embedder, top_k=10)
    └── answer(question)
            ├── _fallback_graph_retrieval(question)  [no graph_retriever provided]
            │       ├── _create_mock_retriever()  [one-time]
            │       │       └── Loads dataset + DocumentBuilder
            │       │       └── Builds _local_docs from entity docs
            │       │
            │       ├── Keyword expansion:
            │       │   ├── Extract keywords from question
            │       │   ├── Match against 18 FRAUD_KEYWORDS:
            │       │   │   fraud, laundering, shell, offshore, funnel, smurfing,
            │       │   │   layering, circular, sanctioned, pep, mule, structuring,
            │       │   │   dormant, burst, ownership, trafficking, placement, integration
            │       │   └── Expanded query with keyword synonyms
            │       │
            │       ├── For each matched doc:
            │       │   └── dataset.get_edges_for_entity(entity_id)  [O(1) index]
            │       │       └── Build TraversalPath for each edge
            │       │
            │       ├── Fraud ring matching:
            │       │   ├── Extract ring IDs from question (FR-CIRC-XX, FR-FUNNEL-XX, etc.)
            │       │   └── Include ring entities + paths
            │       │
            │       └── Limit: top_k*5 docs, top_k*2 rings
            │
            ├── _format_context(context_parts)
            │       └── "=== GRAPH CONTEXT ===\n[Entity P-000001] (CRITICAL risk):
            │       connected to C-000021 (OWNS), C-000004 (OWNS)
            │       Risk: 0.85 [PEP] [SANCTIONED]\n..."
            │
            ├── Build RetrievalTrace:
            │       ├── strategy: "graph_traversal"
            │       ├── visited_nodes: unique entities
            │       ├── traversed_edges: edge count
            │       ├── retrieval_depth: 2
            │       └── traversal_paths: [ {path, path_type, hops, weight}, ... ]
            │
            ├── _build_prompt(question, context) → system + user_prompt
            ├── llm.generate(prompt + context, ...)
            │
            └── _parse_response() → PipelineResult
                    retrieval_ms: graph traversal time
                    sources: matched entities + paths
```

**Token cost:** Highest of all (graph context is verbose — includes topology relationships)

---

## Stage 6: Evaluation & Scoring

**Entry point:** `2_baseline_systems/evaluation/scorer.py` → `BenchmarkScorer.evaluate()`

```
BenchmarkScorer(result, query, context)
    ├── LLMJudge.evaluate(answer, question, context)
    │       ├── Builds JUDGE_PROMPT with question + context + answer
    │       ├── llm.generate() → JSON with 6 scores (1-5 each):
    │       │   relevance, accuracy, completeness, hallucination, clarity, overall
    │       └── Returns: judge_scores dict
    │
    ├── EntityMatcher.match(answer, query)
    │       ├── extract_entity_ids(answer)
    │       │       └── Regex: \b(P-\d+|C-\d+|A-\d+|ADDR-\d+|D-\d+|TX-\d+|T-\d+|FR-[A-Z]+-\d+)\b
    │       ├── Compare predicted vs ground_truth_entities
    │       └── Returns: { tp, fp, fn, precision, recall, f1 }
    │
    ├── _compute_accuracy(judge_overall, entity_f1, tokens, latency_ms)
    │       └── Weighted: 0.5×overall + 0.3×f1 + 0.1×(1-normalized_tokens) + 0.1×(1-normalized_latency)
    │
    └── _classify_failures(judge_scores, entity_match)
            └── RETRIEVAL_FAILURE_TYPES:
                    hallucination       → judge.hallucination ≤ 2
                    missed_topology      → entity_recall < 0.3
                    context_pollution    → fp > tp × 2
                    retrieval_irrelevance → relevance ≤ 2
                    context_overload     → tokens > 8000
```

---

## Stage 7: Analytics & Reporting

```
TokenEfficiencyAnalyzer.analyze(run)
    ├── Per approach: avg_tokens, min_tokens, max_tokens
    ├── Comparisons:
    │       graphrag_vs_pure_llm: (pure_tokens - graph_tokens) / pure_tokens × 100
    │       graphrag_vs_vector_rag: (vector_tokens - graph_tokens) / vector_tokens × 100
    └── Projected savings for 1M queries

FailureAnalyzer.generate_report(run)
    ├── Per approach: error count, failure type counts
    ├── Failure types: from RETRIEVAL_FAILURE_TYPES
    └── Summary: total, errors, error_rate

GraphAnalytics.compute(dataset)
    ├── Degree analysis: avg_degree, max_degree, min_degree, variance
    ├── Fraud metrics: fraud_edges, fraud_entities, fraud_ring_count
    ├── Risk counts: offshore_companies, shell_companies, mule_persons
    └── By-type breakdown: persons, companies, accounts, addresses, transactions

BenchmarkReportGenerator.generate(run)
    ├── TokenEfficiencyAnalyzer → token_report
    ├── FailureAnalyzer → failure_report
    ├── _build_summary_table: per-approach tokens, latency, cost, errors
    ├── _generate_recommendations: based on error rates and token comparisons
    ├── Outputs:
    │       ├── JSON: 2_baseline_systems/outputs/benchmark_results/report_{run_id}.json
    │       └── Console: formatted summary table
```

---

## Complete End-to-End Call Graph

```
python -m 2_baseline_systems benchmark --profile small --limit 2
│
├─ AdaptiveDataLoader('small').load()
│   ├─ [output exists] → skip generation
│   └─ _load_from_outputs()
│       ├─ persons.csv       → 6,000 persons
│       ├─ companies.csv     → 5,000 companies
│       ├─ accounts.csv      → 10,000 accounts
│       ├─ addresses.csv     → 4,000 addresses
│       ├─ edges.csv         → 160,185 edges
│       ├─ transactions.csv  → 149,980 transactions  ← NEW from CSV
│       ├─ fraud_rings.csv   → CSV scalars (id, severity, entity_count)
│       ├─ fraud_rings.json  → entities list, traversal_paths, ring_type
│       ├─ graph.json        → transaction fallback (unused when CSV exists)
│       └─ MERGE(fraud_rings) → list with merged CSV + JSON fields
│           └─ dataset.fraud_rings: [ {id, name, ring_type, severity,
│                                     entities: [P-, C-, A-...], traversal_paths: [...]} ]
│
├─ GraphAnalytics(data_loader).compute()
│   ├─ degree_map from edges (O(1) index via get_edges_for_entity)
│   ├─ fraud_edges, offshore_companies, shell_companies
│   └─ Returns: { total_entities: 25,000, total_edges: 160,185,
│                  transactions: 149,980, fraud_rings: 33, ... }
│
├─ BenchmarkRunner(profile='small', config={llm: mock, embedder: mock, vector: mock})
│   ├─ QueryLoader(data_loader).load_queries()
│   │   ├─ _generate_from_fraud_rings() → 66 BenchmarkQuery from 33 rings
│   │   │   (TRAVERSAL + IDENTIFY per ring, plus PATH queries)
│   │   └─ _generate_synthetic_queries() → 4 BenchmarkQuery (tier 1-3)
│   │   └─ Total: 70 queries
│   │
│   └─ run(queries[:2], approaches=[pure_llm, vector_rag, graph_rag])
│       │
│       ├─ [Query 1: "Find all entities connected to C-000001..."]
│       │   │
│       │   ├─ PureLLMPipeline.answer(question)
│       │   │   ├─ dataset.to_graph_summary() → { persons: 6000, ... }
│       │   │   ├─ _build_prompt() → "System: analyst...\nDataset: {counts}\nQ: {question}"
│       │   │   ├─ LLMClient(provider=mock).generate(prompt)
│       │   │   │   └─ Returns: "[MOCK] Processed query with 74 prompt tokens..."
│       │   │   └─ _parse_response() → PipelineResult(approach=pure_llm, tokens=83, ...)
│       │   │
│       │   ├─ VectorRAGPipeline.answer(question)
│       │   │   ├─ _ensure_indexed() [first call]
│       │   │   │   ├─ DocumentBuilder.build_all() → 30,033 Document
│       │   │   │   │   ├─ 6,000 _person_to_doc()  → get_edges_for_entity() each [O(1)]
│       │   │   │   ├─ 5,000 _company_to_doc()
│       │   │   │   ├─ 10,000 _account_to_doc()
│       │   │   │   ├─ 4,000 _address_to_doc()
│       │   │   │   ├─ 5,000 _transaction_to_doc()
│       │   │   │   └─ 33 _fraud_ring_to_doc()
│       │   │   │       └── Each: "Entity {id}: {name}. Risk Score: {score}. Type: {ring_type}."
│       │   │   │           Connected entities: {entities}. Severity: {severity}."
│       │   │   └─ VectorStore(provider=mock).index_documents(docs, embedder)
│       │   │       └─ Mock: embed + store 30,033 docs in _mock_docs list
│       │   │   │
│       │   │   ├─ Embedder(provider=mock).embed(question) → unit vector
│       │   │   ├─ VectorStore(provider=mock).search(embedding, top_k=10)
│       │   │   │   └─ Mock: dot product similarity → top-10 ranked docs
│       │   │   ├─ _format_context(top_10_docs) → "=== CONTEXT (10 sources) ===..."
│       │   │   ├─ _build_prompt(question, context)
│       │   │   ├─ LLMClient(provider=mock).generate(prompt)
│       │   │   └─ _parse_response() → PipelineResult(approach=vector_rag, tokens=40, ...)
│       │   │
│       │   └─ GraphRAGPipeline.answer(question)
│       │       ├─ _create_mock_retriever() [first call]
│       │       │   └─ Builds entity docs subset from fraud ring entities
│       │       ├─ _fallback_graph_retrieval(question)
│       │       │   ├─ Keyword extraction: "fraud" → matches FR-CIRC-00
│       │       │   ├─ For each matched entity: get_edges_for_entity() [O(1)]
│       │       │   ├─ TraversalPath creation per edge
│       │       │   └─ Limit: top_k×5 docs, top_k×2 rings
│       │       ├─ _format_context(context) → "=== GRAPH CONTEXT ===..."
│       │       ├─ _build_prompt(question, context)
│       │       ├─ LLMClient(provider=mock).generate(prompt)
│       │       └─ _parse_response() → PipelineResult(approach=graph_rag, tokens=409, ...)
│       │
│       ├─ [Query 2: "Identify the fraud ring containing C-000021..."]
│       │   └─ Same 3 pipelines called again
│       │
│       └─ Save: benchmark_RUN_YYYYMMDD_HHMMSS_XXXXX.json
│           BenchmarkRun:
│               run_id, timestamp, profile=small, dataset_hash,
│               queries_loaded=70, queries_run=2,
│               results:
│                   pure_llm: [PipelineResult, PipelineResult]
│                   vector_rag: [PipelineResult, PipelineResult]
│                   graph_rag: [PipelineResult, PipelineResult]
│
├─ TokenEfficiencyAnalyzer(benchmark_run).analyze()
│   ├─ pure_llm: avg=77.5 tokens, latency=50ms
│   ├─ vector_rag: avg=34.5 tokens (-55% vs pure_llm)
│   ├─ graph_rag: avg=382 tokens (+393% vs pure_llm)
│   └─ Returns: token_report with comparisons
│
├─ BenchmarkReportGenerator(benchmark_run).generate()
│   ├─ _build_summary_table()
│   ├─ _generate_recommendations()
│   ├─ Console: formatted summary
│   └─ File: report_RUN_YYYYMMDD_HHMMSS.json
│
└─ python -m 2_baseline_systems report --run-id RUN_YYYYMMDD_HHMMSS_XXXXX
    ├─ Load benchmark JSON
    ├─ BenchmarkReportGenerator(run).generate()
    └─ Console: full report with recommendations
```

---

## File-by-File Reference

### 1_data_engine (data generation)

| File | Role | Input | Output |
|------|------|-------|--------|
| `main.py` | CLI + orchestration | `generate --profile small` | Orchestrates all phases |
| `generators/entity_factory.py` | Entity creation | `GenerationConfig` | `EntityRegistry` (persons, companies, accounts, addresses, transactions, edges) |
| `generators/person_generator.py` | Person entity | seed, pep_ratio | `PersonSchema` |
| `generators/company_generator.py` | Company entity | seed, offshore_ratio | `CompanySchema` |
| `generators/account_generator.py` | Account entity | seed | `AccountSchema` |
| `generators/address_generator.py` | Address entity | seed | `AddressSchema` |
| `generators/transaction_generator.py` | Transaction entity | seed, from/to accounts | `TransactionSchema` |
| `edges/edge_factory.py` | Edge creation | entity IDs | `GraphEdge` |
| `topology/orchestrator.py` | Fraud injector runner | registry, seed | registry with fraud rings |
| `topology/funnel_account.py` | Funnel fraud | registry | FR-FUNNEL-XX, edges |
| `topology/circular_ownership.py` | Circular ownership | registry | FR-CIRC-XX, edges |
| `topology/smurfing_pattern.py` | Smurfing | registry | FR-SMURF-XX, transactions |
| `topology/laundering_chain.py` | Layering chain | registry | FR-LAYER-XX, transactions |
| `topology/central_hub.py` | Hub fraud | registry | FR-HUB-XXX, edges |
| `topology/offshore_routing.py` | Offshore routing | registry | FR-OFFSHORE-XX, edges |
| `topology/dormant_burst.py` | Dormant burst | registry | FR-DORMANT-XX, transactions |
| `topology/beneficial_ownership.py` | Beneficial ownership | registry | FR-BENEF-XX, edges |
| `topology/address_collision.py` | Shared address | registry | FR-ADDR-XX, edges |
| `topology/semantic_trap.py` | Semantic trap | registry | FR-TRAP-XX, entities |
| `topology/temporal_spike.py` | Temporal spike | registry | FR-SPIKE-XX, transactions |
| `schemas/person.py` | Person schema | — | Dataclass for persons |
| `schemas/company.py` | Company schema | — | Dataclass for companies |
| `schemas/account.py` | Account schema | — | Dataclass for accounts |
| `schemas/address.py` | Address schema | — | Dataclass for addresses |
| `schemas/edge.py` | Edge schema | — | Dataclass for edges |
| `schemas/transaction.py` | Transaction schema | — | Dataclass for transactions |
| `schemas/fraud_ring.py` | Fraud ring schema + builder | — | FraudRingSchema, FraudRingBuilder |
| `schemas/entity_registry.py` | Central registry | — | Dict of all entities by type |
| `validators/graph_integrity.py` | Integrity check | registry | IntegrityReport |
| `validators/fraud_ring_validator.py` | Fraud ring check | registry | FraudRingReport |
| `exporters/csv_exporter.py` | CSV export | registry | 7 CSV files including **transactions.csv** |
| `exporters/json_exporter.py` | JSON export | registry | 3 JSON files including **transactions in graph.json** |

### 2_baseline_systems (benchmarking)

| File | Role | Input | Output |
|------|------|-------|--------|
| `__main__.py` | CLI entry | CLI args | Orchestrates commands |
| `shared/data_loader.py` | Data ingestion | 1_data_engine outputs | `ShadowDataset` |
| `shared/schemas.py` | Data models | — | ShadowDataset, PipelineResult, etc. |
| `shared/document_builder.py` | Doc transformation | ShadowDataset | `Document` list |
| `shared/chunkers/recursive.py` | Text chunking | text, chunk_size | list[str] chunks |
| `shared/llm_client.py` | LLM abstraction | prompt, messages | `LLMResponse` |
| `shared/embedder.py` | Embedding abstraction | text | list[float] vector |
| `shared/token_tracker.py` | Token counting | text | token count, cost |
| `pipelines/base.py` | Pipeline base class | question | `PipelineResult` |
| `pipelines/pure_llm.py` | No-retrieval baseline | question | `PipelineResult` |
| `pipelines/vector_rag.py` | Vector RAG | question | `PipelineResult` |
| `pipelines/graph_rag.py` | Graph RAG | question | `PipelineResult` |
| `retrieval/vector_store.py` | Vector DB | documents, query | top-k results |
| `retrieval/cache.py` | LRU cache | query hash | cached results |
| `benchmarking/runner.py` | Benchmark execution | queries, approaches | `BenchmarkRun` |
| `benchmarking/query_loader.py` | Query generation | ShadowDataset | `BenchmarkQuery` list |
| `benchmarking/difficulty_tiers.py` | Tier classification | query metadata | tier 1-5 |
| `evaluation/entity_matcher.py` | Entity extraction | answer text | EntityMatchResult |
| `evaluation/llm_judge.py` | LLM-as-Judge | answer, question | judge_scores |
| `evaluation/scorer.py` | Combined scoring | result, query | `EvaluationResult` |
| `analytics/token_efficiency.py` | Token analysis | BenchmarkRun | token_report |
| `analytics/failure_analysis.py` | Failure analysis | BenchmarkRun | failure_report |
| `analytics/graph_analytics.py` | Graph metrics | ShadowDataset | graph_stats |
| `reports/benchmark_report.py` | Report generation | BenchmarkRun | JSON + console |
| `reports/explainability_report.py` | Explainability | BenchmarkRun | explainability_report |
| `orchestration/benchmark_orchestrator.py` | Full orchestrator | config | BenchmarkRun |
| `explainability/trace_builder.py` | Trace building | PipelineResult | trace dict |
| `explainability/graph_narrator.py` | Narrative gen | TraversalPath | human-readable |
| `dashboards/dashboard_adapter.py` | Dashboard output | BenchmarkRun | dashboard format |

---

## Data Transformations Summary

```
CSV/JSON Files (1_data_engine output)
    │
    │ persons.csv → [AdaptiveDataLoader] → ShadowDataset.persons
    │ companies.csv →                              → .companies
    │ accounts.csv →                              → .accounts
    │ addresses.csv →                             → .addresses
    │ devices.csv →                               → .devices
    │ transactions.csv →                          → .transactions   [NEW]
    │ edges.csv →                                  → .edges
    │ fraud_rings.csv + fraud_rings.json →        → .fraud_rings (merged)
    │
    ▼
ShadowDataset
    │
    │ [DocumentBuilder.build_all]
    │
    │ .persons (×1 doc each)         → Document(id=entity::P-XXXXXX, text="Person P-... risk:...", metadata)
    │ .companies (×1 doc each)       → Document(id=entity::C-XXXXXX, ...)
    │ .accounts (×1 doc each)         → Document(id=entity::A-XXXXXX, ...)
    │ .addresses (×1 doc each)        → Document(id=entity::ADDR-XXXXXX, ...)
    │ .transactions (up to 5000)      → Document(id=tx::TX-XXXXXXXX, ...)
    │ .fraud_rings (up to 100)         → Document(id=ring::FR-XXX-XX, ...)
    │
    ▼
list[Document] (~30K total for small profile)
    │
    │ [VectorRAGPipeline._ensure_indexed]
    │     Embedder.embed_batch(texts)  → list[list[float]]  (dimension 768)
    │     VectorStore.index_documents  → ChromaDB collection / mock_docs
    │
    │ [GraphRAGPipeline._fallback_graph_retrieval]
    │     dataset.get_edges_for_entity(id)  → O(1) hash lookup
    │     TraversalPath for each edge
    │
    ▼
Question → [Pipeline.answer] → PipelineResult
    │
    │ pure_llm:    question → LLM(→ "[MOCK] ...")         → tokens ~75
    │ vector_rag:  question → embed → search → context → LLM → tokens ~35  (-55%)
    │ graph_rag:   question → keyword expand → traverse → context → LLM → tokens ~380  (+400%)
    │
    ▼
PipelineResult → [Scorer.evaluate] → EvaluationResult
    │
    │ EntityMatcher.match  → precision/recall/F1
    │ LLMJudge.evaluate    → relevance/accuracy/completeness/hallucination/clarity/overall
    │
    ▼
BenchmarkRun → [Analytics] → Reports + Console
```

import type { EntityKind } from './intel';

export type SourceKind =
  | 'postgres'
  | 'mysql'
  | 'mongodb'
  | 'neo4j'
  | 'tigergraph'
  | 'snowflake'
  | 'bigquery'
  | 'csv'
  | 'json'
  | 'excel'
  | 'parquet'
  | 'kafka'
  | 'webhook'
  | 'event_stream'
  | 'sse'
  | 's3'
  | 'gcs'
  | 'azure_blob'
  | 'rest_api'
  | 'graphql'
  | 'blockchain'
  | 'financial_feed'
  | 'sanctions_feed';

export type SourceCategory =
  | 'database'
  | 'file'
  | 'streaming'
  | 'cloud_storage'
  | 'api';

export type SourceStatus =
  | 'connected'
  | 'syncing'
  | 'paused'
  | 'error'
  | 'configured';

export type SourceHealth = 'healthy' | 'degraded' | 'failing' | 'idle';

export type SyncCadence = 'realtime' | 'every_15m' | 'hourly' | 'daily' | 'manual';

export interface DataSource {
  id: string;
  name: string;
  kind: SourceKind;
  category: SourceCategory;
  status: SourceStatus;
  health: SourceHealth;
  cadence: SyncCadence;
  uri: string;
  region?: string;
  /** ISO timestamp of the last successful sync */
  lastSyncAt?: string;
  /** ISO timestamp the source was first connected */
  connectedAt: string;
  /** Total rows pulled across all runs */
  rowsIngested: number;
  /** Total entities produced into the graph */
  entitiesProduced: number;
  /** Total edges produced into the graph */
  edgesProduced: number;
  /** Owner team / department */
  owner: string;
  /** A short description of what this source contains */
  description: string;
  /** Number of recent errors (last 24h) */
  errorCount: number;
  /** Connection token / cred ref (masked) */
  credentialRef: string;
}

export interface SchemaMappingRule {
  sourceField: string;
  /** sample value the analyst can verify */
  sampleValue: string;
  /** mapped to which graph entity kind */
  targetEntity: EntityKind;
  /** 0-1 confidence */
  confidence: number;
  /** true if the platform auto-suggested this rule */
  autoSuggested: boolean;
  /** validated by analyst */
  validated: boolean;
}

export interface EdgeMappingRule {
  /** From which source field */
  fromField: string;
  /** To which source field */
  toField: string;
  /** edge kind */
  edgeKind: string;
  confidence: number;
  autoSuggested: boolean;
}

export interface SchemaMapping {
  sourceId: string;
  /** Field-to-entity rules */
  entityRules: SchemaMappingRule[];
  /** Field-to-edge rules */
  edgeRules: EdgeMappingRule[];
  /** Last validated timestamp */
  validatedAt?: string;
}

export type IngestionRunStatus =
  | 'queued'
  | 'running'
  | 'success'
  | 'partial'
  | 'failed';

export interface IngestionRun {
  id: string;
  sourceId: string;
  startedAt: string;
  finishedAt?: string;
  status: IngestionRunStatus;
  rowsRead: number;
  entitiesAdded: number;
  edgesAdded: number;
  ringsDiscovered: number;
  hiddenLinksFound: number;
  errors: number;
  /** Lines from the operational log */
  log: string[];
}

export interface DataHealthSnapshot {
  /** 0-1, weighted across signals */
  overall: number;
  orphanEntities: number;
  duplicateEntities: number;
  unmappedFields: number;
  edgeDensity: number;
  topologyCompleteness: number;
  relationshipConfidence: number;
}

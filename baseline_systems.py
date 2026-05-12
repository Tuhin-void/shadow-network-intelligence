"""
Compatibility shim enabling `from baseline_systems import X` syntax.
Works around Python's restriction on module names starting with digits.
"""
import importlib
import sys
from pathlib import Path

_root = Path(__file__).parent

_baseline = importlib.import_module("2_baseline_systems")
_config = importlib.import_module("2_baseline_systems.config")

_shared = importlib.import_module("2_baseline_systems.shared")
_pipelines = importlib.import_module("2_baseline_systems.pipelines")
_benchmarking = importlib.import_module("2_baseline_systems.benchmarking")
_evaluation = importlib.import_module("2_baseline_systems.evaluation")
_analytics = importlib.import_module("2_baseline_systems.analytics")
_orchestration = importlib.import_module("2_baseline_systems.orchestration")
_reports = importlib.import_module("2_baseline_systems.reports")
_dashboards = importlib.import_module("2_baseline_systems.dashboards")

config = _config
get_config = _config.get_config
AdaptiveDataLoader = _shared.AdaptiveDataLoader
DocumentBuilder = _shared.DocumentBuilder
LLMClient = _shared.LLMClient
Embedder = _shared.Embedder
TokenTracker = _shared.TokenTracker
get_chunker = _shared.get_chunker
ShadowDataset = _shared.ShadowDataset
BenchmarkQuery = _shared.BenchmarkQuery
PipelineResult = _shared.PipelineResult
GraphMetadata = _shared.GraphMetadata
Document = _shared.Document

PureLLMPipeline = _pipelines.PureLLMPipeline
VectorRAGPipeline = _pipelines.VectorRAGPipeline
GraphRAGPipeline = _pipelines.GraphRAGPipeline

QueryLoader = _benchmarking.QueryLoader
DifficultyTierClassifier = _benchmarking.DifficultyTierClassifier
BenchmarkRunner = _benchmarking.BenchmarkRunner

LLMJudge = _evaluation.LLMJudge
EntityMatcher = _evaluation.EntityMatcher
BenchmarkScorer = _evaluation.BenchmarkScorer

TokenEfficiencyAnalyzer = _analytics.TokenEfficiencyAnalyzer
FailureAnalyzer = _analytics.FailureAnalyzer
GraphAnalytics = _analytics.GraphAnalytics

BenchmarkOrchestrator = _orchestration.BenchmarkOrchestrator
ExperimentTracker = _orchestration.ExperimentTracker

BenchmarkReportGenerator = _reports.BenchmarkReportGenerator
ExplainabilityReportGenerator = _reports.ExplainabilityReportGenerator

DashboardAdapter = _dashboards.DashboardAdapter

__all__ = [
    "config", "get_config",
    "AdaptiveDataLoader", "DocumentBuilder", "LLMClient", "Embedder",
    "TokenTracker", "get_chunker", "ShadowDataset", "BenchmarkQuery",
    "PipelineResult", "GraphMetadata", "Document",
    "PureLLMPipeline", "VectorRAGPipeline", "GraphRAGPipeline",
    "QueryLoader", "DifficultyTierClassifier", "BenchmarkRunner",
    "LLMJudge", "EntityMatcher", "BenchmarkScorer",
    "TokenEfficiencyAnalyzer", "FailureAnalyzer", "GraphAnalytics",
    "BenchmarkOrchestrator", "ExperimentTracker",
    "BenchmarkReportGenerator", "ExplainabilityReportGenerator",
    "DashboardAdapter",
]
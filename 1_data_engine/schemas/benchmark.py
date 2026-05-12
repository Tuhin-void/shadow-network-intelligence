"""
Benchmark Schema - Benchmark questions, answers, and scoring
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class QuestionType(Enum):
    TRAVERSAL = "traversal"
    PATH_FINDING = "path_finding"
    CYCLE_DETECTION = "cycle_detection"
    CENTRALITY = "centrality"
    CLUSTERING = "clustering"
    TEMPORAL = "temporal"
    ENTITY_RESOLUTION = "entity_resolution"
    FRAUD_RING_IDENTIFICATION = "fraud_ring_identification"


class RetrievalType(Enum):
    GRAPHRAG = "graphrag"
    VECTOR_RAG = "vector_rag"
    HYBRID = "hybrid"
    VANILLA_LLM = "vanilla_llm"


@dataclass
class BenchmarkQuestion:
    """Benchmark question with expected answer metadata"""

    id: str
    question: str
    question_type: QuestionType
    required_hops: int
    relevant_entities: List[str]
    relevant_paths: List[List[str]]
    fraud_ring_id: Optional[str] = None
    ground_truth_entities: List[str] = field(default_factory=list)
    ground_truth_paths: List[str] = field(default_factory=list)
    complexity_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "question_type": self.question_type.value,
            "required_hops": self.required_hops,
            "relevant_entities": self.relevant_entities,
            "relevant_paths": self.relevant_paths,
            "fraud_ring_id": self.fraud_ring_id,
            "ground_truth_entities": self.ground_truth_entities,
            "ground_truth_paths": self.ground_truth_paths,
            "complexity_score": self.complexity_score,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class BenchmarkAnswer:
    """Expected answer for a benchmark question"""

    question_id: str
    answer: str
    key_entities: List[str] = field(default_factory=list)
    key_paths: List[str] = field(default_factory=list)
    token_count_estimate: int = 0
    retrieval_type: RetrievalType = RetrievalType.GRAPHRAG

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "answer": self.answer,
            "key_entities": self.key_entities,
            "key_paths": self.key_paths,
            "token_count_estimate": self.token_count_estimate,
            "retrieval_type": self.retrieval_type.value,
        }


@dataclass
class BenchmarkResult:
    """Benchmark result for a retrieval method"""

    question_id: str
    retrieval_type: RetrievalType
    retrieved_entities: List[str] = field(default_factory=list)
    retrieved_context: str = ""
    token_count: int = 0
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "retrieval_type": self.retrieval_type.value,
            "retrieved_entities": self.retrieved_entities,
            "retrieved_context": self.retrieved_context[:500],
            "token_count": self.token_count,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class BenchmarkReport:
    """Aggregated benchmark report"""

    total_questions: int
    graphrag_results: List[BenchmarkResult]
    vectorrag_results: List[BenchmarkResult]
    graphrag_avg_tokens: float = 0.0
    vectorrag_avg_tokens: float = 0.0
    graphrag_avg_accuracy: float = 0.0
    vectorrag_avg_accuracy: float = 0.0
    graphrag_token_reduction: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "total_questions": self.total_questions,
            "graphrag_avg_tokens": self.graphrag_avg_tokens,
            "vectorrag_avg_tokens": self.vectorrag_avg_tokens,
            "graphrag_avg_accuracy": self.graphrag_avg_accuracy,
            "vectorrag_avg_accuracy": self.vectorrag_avg_accuracy,
            "graphrag_token_reduction": self.graphrag_token_reduction,
            "created_at": self.created_at.isoformat(),
        }

    def calculate_metrics(self) -> Dict[str, Any]:
        if not self.graphrag_results:
            return {}

        graphrag_tokens = [r.token_count for r in self.graphrag_results]
        vectorrag_tokens = [r.token_count for r in self.vectorrag_results]
        graphrag_acc = [r.accuracy for r in self.graphrag_results]
        vectorrag_acc = [r.accuracy for r in self.vectorrag_results]

        self.graphrag_avg_tokens = sum(graphrag_tokens) / len(graphrag_tokens)
        self.vectorrag_avg_tokens = sum(vectorrag_tokens) / len(vectorrag_tokens)
        self.graphrag_avg_accuracy = sum(graphrag_acc) / len(graphrag_acc)
        self.vectorrag_avg_accuracy = sum(vectorrag_acc) / len(vectorrag_acc)

        if self.vectorrag_avg_tokens > 0:
            self.graphrag_token_reduction = (
                (self.vectorrag_avg_tokens - self.graphrag_avg_tokens) / self.vectorrag_avg_tokens
            ) * 100

        return {
            "graphrag_avg_tokens": self.graphrag_avg_tokens,
            "vectorrag_avg_tokens": self.vectorrag_avg_tokens,
            "graphrag_avg_accuracy": self.graphrag_avg_accuracy,
            "vectorrag_avg_accuracy": self.vectorrag_avg_accuracy,
            "token_reduction_pct": self.graphrag_token_reduction,
        }


class BenchmarkQuestionGenerator:
    """Generator for benchmark questions based on fraud rings"""

    QUESTION_TEMPLATES = {
        QuestionType.TRAVERSAL: [
            "Find all entities connected to {entity} within {hops} hops",
            "List all accounts reachable from {entity} through ownership chains",
            "What companies does {entity} control indirectly?",
        ],
        QuestionType.PATH_FINDING: [
            "Trace the laundering path from {source} to {target}",
            "Find the transaction chain from {source_account} through {intermediate} to {dest}",
            "What is the fund flow from {entity}?",
        ],
        QuestionType.CYCLE_DETECTION: [
            "Identify circular ownership structures involving {company}",
            "Find ownership loops that return to {company}",
            "Which companies form a circular ownership ring?",
        ],
        QuestionType.CENTRALITY: [
            "Which entity has the highest betweenness centrality in the laundering network?",
            "Identify transaction hubs connecting multiple fraud rings",
            "Find accounts acting as funnel points for multiple sources",
        ],
        QuestionType.FRAUD_RING_IDENTIFICATION: [
            "Which companies share addresses with {company} and transferred funds to offshore accounts?",
            "Identify all entities in the {ring_type} ring starting from {entity}",
            "Find the fraud ring containing {entity}",
        ],
    }

    @staticmethod
    def generate_from_fraud_ring(
        ring,
        seed: int = 0,
    ) -> List[BenchmarkQuestion]:
        """Generate benchmark questions from a fraud ring"""
        import random
        r = random.Random(seed)

        questions = []

        if ring.traversal_paths:
            for i, path in enumerate(ring.traversal_paths[:3]):
                hops = len(path) - 1
                entity = path[0]

                q = BenchmarkQuestion(
                    id=f"BQ-{ring.id}-{i:02d}",
                    question=f"Find all entities connected to {entity} within {hops} hops",
                    question_type=QuestionType.TRAVERSAL,
                    required_hops=hops,
                    relevant_entities=path,
                    relevant_paths=[path],
                    fraud_ring_id=ring.id,
                    ground_truth_entities=path,
                    complexity_score=0.5 + (hops * 0.1),
                )
                questions.append(q)

        if ring.key_entities:
            for i, entity in enumerate(ring.key_entities[:2]):
                q = BenchmarkQuestion(
                    id=f"BQ-{ring.id}-K{i:02d}",
                    question=f"Identify the fraud ring containing {entity}",
                    question_type=QuestionType.FRAUD_RING_IDENTIFICATION,
                    required_hops=3,
                    relevant_entities=[entity],
                    relevant_paths=ring.traversal_paths,
                    fraud_ring_id=ring.id,
                    ground_truth_entities=ring.entities,
                    complexity_score=0.7,
                )
                questions.append(q)

        return questions
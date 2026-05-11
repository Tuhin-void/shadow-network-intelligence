"""
Shadow Network Intelligence - Benchmark Data Loader
Loads test questions and ground truth
"""
from typing import Dict, List, Any
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

BENCHMARK_QUESTIONS = [
    {
        "id": "Q001",
        "category": "pattern_detection",
        "question": "Detect all circular transaction patterns in the last 30 days",
        "expected_patterns": ["circular"]
    },
    {
        "id": "Q002",
        "category": "entity_search",
        "question": "Find all shell companies with shared addresses",
        "expected_patterns": ["shell_company", "address_collision"]
    },
    {
        "id": "Q003",
        "category": "risk_scoring",
        "question": "What is the risk score for account ACC001?",
        "expected_risk_min": 0.5
    },
    {
        "id": "Q004",
        "category": "pattern_detection",
        "question": "Identify potential structuring (CTR avoidance) patterns",
        "expected_patterns": ["structuring"]
    },
    {
        "id": "Q005",
        "category": "entity_search",
        "question": "Who are the beneficial owners of company CPY001?",
        "expected_entities": ["Person"]
    },
    {
        "id": "Q006",
        "category": "transaction_analysis",
        "question": "Summarize large transactions (>$10,000) this month",
        "expected_transaction_min": 10000
    },
    {
        "id": "Q007",
        "category": "network_analysis",
        "question": "Find all entities connected to offshore jurisdiction H001",
        "expected_patterns": ["offshore_hop"]
    },
    {
        "id": "Q008",
        "category": "pattern_detection",
        "question": "Detect rapid transfer loops in the last 24 hours",
        "expected_patterns": ["rapid_loop"]
    }
]

GROUND_TRUTH = {
    "Q001": {"is_fraud": True, "fraud_type": "circular", "entities_affected": 5},
    "Q002": {"is_fraud": True, "fraud_type": "shell_company", "entities_affected": 8},
    "Q003": {"is_fraud": True, "risk_level": "HIGH"},
    "Q004": {"is_fraud": True, "fraud_type": "structuring", "entities_affected": 3}
}

class BenchmarkDataLoader:
    """
    Loads and manages benchmark test data.
    """
    
    def __init__(self, data_dir: str = "tests/benchmark_questions"):
        self.data_dir = Path(data_dir)
        self.questions = BENCHMARK_QUESTIONS
        self.ground_truth = GROUND_TRUTH
    
    def get_questions(self, category: str = None) -> List[Dict]:
        """Get benchmark questions, optionally filtered by category"""
        if category:
            return [q for q in self.questions if q.get("category") == category]
        return self.questions
    
    def get_ground_truth(self, question_id: str) -> Dict:
        """Get ground truth for a question"""
        return self.ground_truth.get(question_id, {})
    
    def load_custom_questions(self, filepath: str) -> List[Dict]:
        """Load custom questions from JSON file"""
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Custom questions file not found: {filepath}")
            return []
        
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load questions: {e}")
            return []
    
    def validate_answer(
        self,
        question_id: str,
        answer: Dict
    ) -> Dict[str, Any]:
        """
        Validate answer against ground truth.
        Returns accuracy score and feedback.
        """
        truth = self.get_ground_truth(question_id)
        
        if not truth:
            return {"accuracy": None, "feedback": "No ground truth available"}
        
        correct = 0
        total = 0
        
        if "is_fraud" in truth:
            total += 1
            if answer.get("is_fraud") == truth["is_fraud"]:
                correct += 1
        
        if "fraud_type" in truth:
            total += 1
            if answer.get("fraud_type") == truth["fraud_type"]:
                correct += 1
        
        if "risk_level" in truth:
            total += 1
            if answer.get("risk_level") == truth["risk_level"]:
                correct += 1
        
        accuracy = correct / total if total > 0 else 0
        
        return {
            "accuracy": accuracy,
            "correct": correct,
            "total": total,
            "feedback": "Good match" if accuracy >= 1.0 else "Partial match"
        }
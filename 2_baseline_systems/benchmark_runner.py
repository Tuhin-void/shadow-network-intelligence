"""
Shadow Network Intelligence - Benchmark Runner
Compares Pure LLM, Vector RAG, and GraphRAG approaches
"""
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BenchmarkRunner:
    """
    Runs benchmark comparisons between different RAG approaches.
    
    Compares:
    - Pure LLM (direct questioning)
    - Vector RAG (semantic search)
    - GraphRAG (graph + vector hybrid)
    """
    
    def __init__(self, llm_provider, vector_store, graph_connection):
        self.llm = llm_provider
        self.vector_store = vector_store
        self.graph = graph_connection
        self.results = []
    
    def run_benchmark(
        self,
        questions: List[str],
        approaches: List[str] = ["pure_llm", "vector_rag", "graphrag"],
        ground_truth: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Run benchmark comparison across approaches.
        
        Args:
            questions: List of test questions
            approaches: List of approaches to test
            ground_truth: Expected answers for accuracy calculation
            
        Returns:
            List of benchmark results per approach
        """
        logger.info(f"Running benchmark: {len(questions)} questions, {len(approaches)} approaches")
        
        results = []
        
        for approach in approaches:
            start_time = time.time()
            
            responses = self._run_approach(approach, questions)
            
            latency = time.time() - start_time
            tokens = self._estimate_tokens(responses)
            
            accuracy = self._calculate_accuracy(responses, ground_truth) if ground_truth else None
            
            result = {
                "approach": approach,
                "questions_tested": len(questions),
                "responses": responses,
                "total_latency_ms": latency * 1000,
                "avg_latency_ms": (latency * 1000) / len(questions),
                "total_tokens": tokens,
                "estimated_cost": self._estimate_cost(tokens, approach),
                "accuracy": accuracy,
                "timestamp": datetime.now().isoformat()
            }
            
            results.append(result)
            self.results.append(result)
        
        return results
    
    def _run_approach(self, approach: str, questions: List[str]) -> List[Dict[str, Any]]:
        """Run a specific approach"""
        responses = []
        
        for question in questions:
            if approach == "pure_llm":
                response = self._run_pure_llm(question)
            elif approach == "vector_rag":
                response = self._run_vector_rag(question)
            elif approach == "graphrag":
                response = self._run_graphrag(question)
            else:
                response = {"answer": "Unknown approach", "sources": []}
            
            responses.append(response)
        
        return responses
    
    def _run_pure_llm(self, question: str) -> Dict[str, Any]:
        """Run pure LLM without retrieval"""
        start = time.time()
        
        answer = f"[Pure LLM Response] Based on general knowledge, regarding: {question}"
        
        return {
            "question": question,
            "answer": answer,
            "sources": [],
            "latency_ms": (time.time() - start) * 1000,
            "method": "pure_llm"
        }
    
    def _run_vector_rag(self, question: str) -> Dict[str, Any]:
        """Run vector RAG approach"""
        start = time.time()
        
        retrieved = self.vector_store.search(question, top_k=5) if self.vector_store else []
        
        context = "\n".join([f"- {r.get('text', '')}" for r in retrieved[:3]])
        
        answer = f"[Vector RAG Response] Based on retrieved documents:\n{context}"
        
        return {
            "question": question,
            "answer": answer,
            "sources": [r.get("id") for r in retrieved],
            "latency_ms": (time.time() - start) * 1000,
            "method": "vector_rag"
        }
    
    def _run_graphrag(self, question: str) -> Dict[str, Any]:
        """Run GraphRAG approach"""
        start = time.time()
        
        graph_results = self.graph.search(question) if self.graph else []
        vector_results = self.vector_store.search(question, top_k=3) if self.vector_store else []
        
        context = f"Graph: {len(graph_results)} entities, Vector: {len(vector_results)} docs"
        
        answer = f"[GraphRAG Response] Using graph intelligence:\n{context}"
        
        return {
            "question": question,
            "answer": answer,
            "sources": {
                "graph": [g.get("id") for g in graph_results],
                "vector": [v.get("id") for v in vector_results]
            },
            "latency_ms": (time.time() - start) * 1000,
            "method": "graphrag"
        }
    
    def _estimate_tokens(self, responses: List[Dict]) -> int:
        """Estimate token usage"""
        total = 0
        for response in responses:
            answer = response.get("answer", "")
            total += len(answer.split()) * 1.3
        return int(total)
    
    def _estimate_cost(self, tokens: int, approach: str) -> float:
        """Estimate API cost"""
        cost_per_token = {
            "pure_llm": 0.00001,
            "vector_rag": 0.000015,
            "graphrag": 0.00002
        }
        return tokens * cost_per_token.get(approach, 0.00001)
    
    def _calculate_accuracy(self, responses: List[Dict], ground_truth: List[str]) -> float:
        """Calculate accuracy against ground truth"""
        if not ground_truth or len(responses) != len(ground_truth):
            return None
        
        correct = 0
        for response, truth in zip(responses, ground_truth):
            if self._answers_match(response.get("answer", ""), truth):
                correct += 1
        
        return correct / len(responses)
    
    def _answers_match(self, answer: str, truth: str) -> bool:
        """Check if answer matches truth (simplified)"""
        answer_lower = answer.lower()
        truth_lower = truth.lower()
        
        return (
            truth_lower in answer_lower or
            answer_lower in truth_lower or
            len(set(answer_lower.split()) & set(truth_lower.split())) / max(1, len(set(truth_lower.split()))) > 0.5
        )
    
    def save_results(self, output_path: str):
        """Save benchmark results to file"""
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {output_path}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all benchmark runs"""
        if not self.results:
            return {}
        
        summary = {}
        for result in self.results:
            approach = result["approach"]
            summary[approach] = {
                "runs": len([r for r in self.results if r["approach"] == approach]),
                "avg_accuracy": result.get("accuracy"),
                "avg_latency_ms": result["avg_latency_ms"],
                "total_tokens": result["total_tokens"],
                "total_cost": result["estimated_cost"]
            }
        
        return summary


def run_default_benchmark():
    """Run default benchmark with sample questions"""
    questions = [
        "How many transactions over $10,000 occurred in the last month?",
        "Which companies have circular ownership patterns?",
        "What is the risk score for account ACC_123?",
        "Identify suspicious patterns in the transaction network",
        "Who are the beneficial owners of Global Holdings LLC?"
    ]
    
    runner = BenchmarkRunner(None, None, None)
    results = runner.run_benchmark(questions)
    
    return results


if __name__ == "__main__":
    results = run_default_benchmark()
    print(json.dumps(results, indent=2))
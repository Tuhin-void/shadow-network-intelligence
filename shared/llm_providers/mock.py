"""Mock LLM for testing"""
from typing import Dict, Any

class MockLLM:
    """Mock LLM provider for testing."""
    
    def __init__(self, model: str = "mock"):
        self.model = model
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Return mock response."""
        if "risk" in prompt.lower():
            return '{"risk_score": 0.75, "risk_level": "HIGH"}'
        if "fraud" in prompt.lower():
            return '{"is_fraud": true, "confidence": 0.85}'
        return "Based on the data analysis, this appears to be normal activity."
    
    def chat(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Return mock chat response."""
        return {
            "content": self.generate(messages[-1]["content"] if messages else ""),
            "model": self.model
        }

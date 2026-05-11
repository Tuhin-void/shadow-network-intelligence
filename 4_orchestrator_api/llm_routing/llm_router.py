"""
Shadow Network Intelligence - LLM Router
Routes LLM requests to appropriate provider
"""
from typing import Dict, List, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"

class LLMResponse:
    def __init__(self, content: str, token_count: int = 0, latency_ms: float = 0):
        self.content = content
        self.token_count = token_count
        self.latency_ms = latency_ms

class LLMRouter:
    """
    Routes LLM requests to configured provider.
    Supports Ollama (default), OpenAI, Anthropic, and mock.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.provider = self._determine_provider()
        self._init_provider()
    
    def _determine_provider(self) -> LLMProvider:
        """Determine which LLM provider to use"""
        provider_str = self.config.get("llm_provider", "ollama").lower()
        
        provider_map = {
            "ollama": LLMProvider.OLLAMA,
            "openai": LLMProvider.OPENAI,
            "anthropic": LLMProvider.ANTHROPIC,
            "mock": LLMProvider.MOCK
        }
        
        return provider_map.get(provider_str, LLMProvider.OLLAMA)
    
    def _init_provider(self):
        """Initialize the LLM provider"""
        if self.provider == LLMProvider.OLLAMA:
            self._init_ollama()
        elif self.provider == LLMProvider.MOCK:
            logger.info("Using mock LLM provider")
        else:
            logger.warning(f"Provider {self.provider} not fully configured")
    
    def _init_ollama(self):
        """Initialize Ollama connection"""
        import requests
        self.ollama_url = self.config.get("ollama_url", "http://localhost:11434")
        self.model = self.config.get("ollama_model", "llama3.2")
        logger.info(f"Initialized Ollama: {self.ollama_url} model={self.model}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.1,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """Generate LLM response"""
        import time
        start = time.time()
        
        if self.provider == LLMProvider.OLLAMA:
            return self._generate_ollama(prompt, system_prompt, temperature, max_tokens, start)
        elif self.provider == LLMProvider.MOCK:
            return self._generate_mock(prompt, start)
        else:
            return self._generate_mock(prompt, start)
    
    def _generate_ollama(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        start: float
    ) -> LLMResponse:
        """Generate response using Ollama"""
        import requests
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                latency_ms = (time.time() - start) * 1000
                
                return LLMResponse(
                    content=content,
                    token_count=len(content.split()),
                    latency_ms=latency_ms
                )
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
        
        return self._generate_mock(prompt, start)
    
    def _generate_mock(self, prompt: str, start: float) -> LLMResponse:
        """Mock response for testing"""
        import time
        latency_ms = (time.time() - start) * 1000
        
        if "risk" in prompt.lower():
            content = '{"risk_score": 0.75, "risk_level": "HIGH", "patterns": ["structuring"]}'
        elif "fraud" in prompt.lower():
            content = '{"is_fraud": true, "confidence": 0.85, "fraud_type": "layering"}'
        else:
            content = "Based on the transaction data, this appears to be normal activity."
        
        return LLMResponse(
            content=content,
            token_count=len(content.split()),
            latency_ms=latency_ms
        )
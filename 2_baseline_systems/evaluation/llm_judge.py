"""
LLM-as-Judge evaluator.
"""
import json
import logging
from ..shared.schemas import PipelineResult
from ..shared.llm_client import LLMClient

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """You are an expert evaluator of financial crime intelligence answers.
Evaluate the following answer on these dimensions (1-5 each):

1. RELEVANCE: Does the answer directly address the question?
2. ACCURACY: Are the stated facts correct based on the context?
3. COMPLETENESS: Are all relevant entities and relationships covered?
4. HALLUCINATION: Are there invented facts not in the context? (score: 5=none, 1=major hallucinations)
5. CLARITY: Is the answer well-structured and explainable?

Question: {question}
Context: {context}
Answer: {answer}

Return ONLY valid JSON (no markdown):
{{"relevance": X, "accuracy": X, "completeness": X, "hallucination": X, "clarity": X, "overall": X}}
"""


class LLMJudge:
    def __init__(self, llm_client: LLMClient, model: str = "llama3.2"):
        self.llm = llm_client
        self.model = model

    def evaluate(self, answer: str, question: str, context: str = "") -> dict:
        if not answer:
            return {"relevance": 1, "accuracy": 1, "completeness": 1, "hallucination": 1, "clarity": 1, "overall": 1}

        context = context or "No specific context provided."
        prompt = JUDGE_PROMPT.format(question=question, context=context, answer=answer)

        try:
            response = self.llm.generate(prompt, system="You are a strict evaluator. Return ONLY valid JSON.", temperature=0.0, max_tokens=500)
            text = response.text.strip()
            for start in ["```json", "```"]:
                if text.startswith(start):
                    text = text[len(start):]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())
            return {
                "relevance": max(1, min(5, float(data.get("relevance", 3)))),
                "accuracy": max(1, min(5, float(data.get("accuracy", 3)))),
                "completeness": max(1, min(5, float(data.get("completeness", 3)))),
                "hallucination": max(1, min(5, float(data.get("hallucination", 3)))),
                "clarity": max(1, min(5, float(data.get("clarity", 3)))),
                "overall": max(1, min(5, float(data.get("overall", 3)))),
            }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"LLM Judge parse error: {e}, response: {response.text[:200]}")
            return {"relevance": 3, "accuracy": 3, "completeness": 3, "hallucination": 3, "clarity": 3, "overall": 3}

    def evaluate_result(self, result: PipelineResult, context: str = "") -> dict:
        return self.evaluate(
            answer=result.answer or "",
            question=result.question,
            context=context,
        )
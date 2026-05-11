"""
Shadow Network Intelligence - Shared Prompt Templates
Prompt templates for LLM interactions
"""
from string import Template
from typing import Dict, List

FRAUD_INVESTIGATION_PROMPT = Template("""
You are a financial crime investigator analyzing transaction patterns.

CONTEXT:
- Entity: ${entity_id}
- Risk Level: ${risk_level}
- Patterns Detected: ${patterns}

TRANSACTIONS:
${transactions}

EVIDENCE:
${evidence}

TASK:
Analyze the above information and determine:
1. Is this fraud? (Yes/No with confidence)
2. What fraud patterns are present?
3. What evidence supports your conclusion?
4. Recommended next steps?

Respond in JSON format:
{
  "is_fraud": boolean,
  "confidence": float (0-1),
  "fraud_type": string,
  "evidence_summary": string,
  "recommendations": [string]
}
""")

PATTERN_EXPLANATION_PROMPT = Template("""
Explain the following fraud pattern in plain language for a compliance officer.

PATTERN: ${pattern_type}
DESCRIPTION: ${description}
SEVERITY: ${severity}
INDICATORS: ${indicators}

Provide:
1. What this pattern is
2. Why it's suspicious
3. What to look for
4. How to investigate
""")

SAR_SUMMARY_PROMPT = Template("""
Summarize this investigation into a Suspicious Activity Report narrative.

INVESTIGATION ID: ${investigation_id}
ENTITY: ${entity_id}
RISK SCORE: ${risk_score}
PATTERNS: ${patterns}

EVIDENCE:
${evidence}

Provide a narrative summary suitable for a SAR filing.
""")

BENCHMARK_PROMPT = Template("""
Compare the following three approaches for answering this question.

QUESTION: ${question}

APPROACH 1 - Pure LLM:
${pure_llm_result}

APPROACH 2 - Vector RAG:
${vector_rag_result}

APPROACH 3 - GraphRAG:
${graphrag_result}

Evaluate each approach on:
- Accuracy
- Relevance
- Completeness
- Explainability

Which approach is best for this question and why?
""")

ALERT_EXPLANATION_PROMPT = Template("""
Explain this fraud alert in simple terms.

ALERT TYPE: ${alert_type}
SEVERITY: ${severity}
ENTITY: ${entity_id}

DESCRIPTION: ${description}

What happened? Why is this suspicious? What should be done?
""")

ENTITY_SUMMARY_PROMPT = Template("""
Provide a summary of this entity's risk profile.

ENTITY ID: ${entity_id}
ENTITY TYPE: ${entity_type}
CONNECTIONS: ${connection_count}

RECENT ACTIVITY:
${recent_activity}

RISK INDICATORS:
${risk_indicators}

Provide a brief (3-5 sentence) risk summary.
""")

def format_transactions(transactions: List[Dict]) -> str:
    """Format transactions for prompt"""
    if not transactions:
        return "No transactions available"
    
    lines = []
    for t in transactions[:10]:
        lines.append(
            f"- {t.get('date', 'N/A')}: ${t.get('amount', 0):,.2f} "
            f"from {t.get('from_account', 'N/A')} to {t.get('to_account', 'N/A')}"
        )
    
    if len(transactions) > 10:
        lines.append(f"... and {len(transactions) - 10} more transactions")
    
    return "\n".join(lines)

def get_investigation_prompt(
    entity_id: str,
    risk_level: str,
    patterns: List[str],
    transactions: List[Dict],
    evidence: List[Dict]
) -> str:
    """Get formatted investigation prompt"""
    return FRAUD_INVESTIGATION_PROMPT.substitute(
        entity_id=entity_id,
        risk_level=risk_level,
        patterns=", ".join(patterns) if patterns else "None",
        transactions=format_transactions(transactions),
        evidence="\n".join([f"- {e.get('type', 'unknown')}: {e.get('id', 'N/A')}" for e in evidence]) if evidence else "None"
    )
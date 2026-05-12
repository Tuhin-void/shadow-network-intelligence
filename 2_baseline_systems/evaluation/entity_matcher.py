"""
Entity matching against ground truth.
"""
import re
from typing import List, Optional
from ..shared.schemas import EntityMatchResult, BenchmarkQuery

ENTITY_ID_PATTERN = re.compile(r'\b(P-\d+|C-\d+|A-\d+|ADDR-\d+|D-\d+|TX-\d+|T-\d+|FR-[A-Z]+-\d+)\b')


class EntityMatcher:
    def extract_entity_ids(self, text: str) -> set:
        matches = ENTITY_ID_PATTERN.findall(text)
        return {m for m in matches}

    def match(
        self,
        answer: str,
        query: BenchmarkQuery,
    ) -> EntityMatchResult:
        predicted = self.extract_entity_ids(answer or "")
        ground_truth = set(query.ground_truth_entities)

        if not ground_truth:
            return EntityMatchResult(
                true_positives=len(predicted),
                false_positives=0,
                false_negatives=0,
                precision=1.0,
                recall=1.0,
                f1=1.0,
                matched_entities=list(predicted),
            )

        tp = predicted & ground_truth
        fp = predicted - ground_truth
        fn = ground_truth - predicted

        precision = len(tp) / len(predicted) if predicted else 1.0
        recall = len(tp) / len(ground_truth) if ground_truth else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        path_coverage = 0.0
        if query.relevant_paths:
            matched_paths = 0
            for path_str in query.ground_truth_paths:
                path_entities = self.extract_entity_ids(path_str)
                if path_entities and path_entities <= predicted:
                    matched_paths += 1
            path_coverage = matched_paths / len(query.relevant_paths)

        return EntityMatchResult(
            true_positives=len(tp),
            false_positives=len(fp),
            false_negatives=len(fn),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            matched_entities=list(tp),
            missed_entities=list(fn),
            extra_entities=list(fp),
            path_coverage=round(path_coverage, 4),
        )
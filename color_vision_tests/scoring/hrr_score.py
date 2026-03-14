from __future__ import annotations

from typing import Dict, List


def score_hrr(responses: List[dict]) -> Dict[str, object]:
    total = len(responses)
    correct = sum(1 for item in responses if item['response'] == item['correct'])
    accuracy = correct / total if total else 0.0
    return {
        'total_plates': total,
        'correct_count': correct,
        'accuracy': accuracy,
        'responses': responses,
    }

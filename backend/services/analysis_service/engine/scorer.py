import logging
from typing import List, Dict, Any

logger = logging.getLogger("gap_calculator.scorer")

class GapScorer:
    def calculate_overall_score(self, weighted_score_sum: float, total_weight_sum: float) -> float:
        """
        Overall = (Sum of (individual_score * weight) / Total weight sum) * 100
        Mandatory weight = 10, Optional weight = 3
        """
        if total_weight_sum <= 0:
            return 0.0
            
        final_match = (weighted_score_sum / total_weight_sum) * 100
        return round(min(max(final_match, 0.0), 100.0), 1)

    def get_base_score(self, weighted_score_sum: float, total_weight_sum: float) -> float:
        return (weighted_score_sum / total_weight_sum * 100) if total_weight_sum > 0 else 0

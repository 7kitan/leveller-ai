
import json

class MockWeightedScorer:
    def calculate_overall_score(self, weighted_sum: float, weight_total: float) -> float:
        if weight_total <= 0: return 0.0
        return round(min(max((weighted_sum / weight_total) * 100, 0.0), 100.0), 1)

def calculate_simple_average(scores):
    return sum(scores) / len(scores) * 100 if scores else 0

if __name__ == "__main__":
    # Case: 1 Mandatory Skill matched at 100%, 5 Optional Skills missing (0%)
    # Mandatory weight = 10, Optional weight = 3
    
    mandatory_score = 1.0
    optional_scores = [0.0] * 5
    
    # SIMPLE AVERAGE
    simple_result = calculate_simple_average([mandatory_score] + optional_scores)
    
    # WEIGHTED
    weighted_sum = (mandatory_score * 10) + sum(s * 3 for s in optional_scores)
    total_weight = 10 + (5 * 3)
    
    scorer = MockWeightedScorer()
    weighted_result = scorer.calculate_overall_score(weighted_sum, total_weight)
    
    print("--- [SCORING COMPARISON TEST] ---")
    print(f"Scenario: 1 Main 기술 (Matched) + 5 Optional 기술 (Gaps)")
    print(f"Simple Average Result: {simple_result:.1f}%")
    print(f"Weighted Result:       {weighted_result:.1f}%")
    
    # Case 2: Matching a Growth Point partially (e.g. 0.33)
    # JD has 9 items: 2 growth points (0.33, 0.30 - Mandatory), 7 gaps (all Mandatory)
    growth_scores = [0.33, 0.30]
    gap_scores = [0.0] * 7
    
    simple_result_2 = calculate_simple_average(growth_scores + gap_scores)
    
    weighted_sum_2 = sum(s * 10 for s in growth_scores) + sum(s * 10 for s in gap_scores)
    total_weight_2 = (2 + 7) * 10
    weighted_result_2 = scorer.calculate_overall_score(weighted_sum_2, total_weight_2)
    
    print("\nScenario 2 (User's Screenshot): 2 Partial Mandatory + 7 Empty Mandatory")
    print(f"Simple Average Result: {simple_result_2:.1f}%")
    print(f"Weighted Result:       {weighted_result_2:.1f}%")
    
    if weighted_result > simple_result:
        print("\n✅ SUCCESS: Weighted scoring is more representative for mandatory skills.")
    else:
        print("\n❌ FAILURE: Weighted scoring did not improve representation.")

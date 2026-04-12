import json

class MockScorer:
    def calculate_overall_score(self, total_score_sum: float, requirement_count: int) -> float:
        if requirement_count <= 0:
            return 0.0
        final_match = (total_score_sum / requirement_count) * 100
        return round(min(max(final_match, 0.0), 100.0), 1)

if __name__ == "__main__":
    # Test Data
    # 4 requirements: 2 matched perfectly, 1 partial (50%), 1 missed
    scores = [1.0, 1.0, 0.5, 0.0]
    total_sum = sum(scores)
    count = len(scores)

    scorer = MockScorer()
    final_pct = scorer.calculate_overall_score(total_sum, count)

    print(f"--- [SIMPLE SCORING TEST] ---")
    print(f"Requirement Scores: {scores}")
    print(f"Total Sum: {total_sum}")
    print(f"Requirement Count: {count}")
    print(f"Calculation: ({total_sum} / {count}) * 100")
    print(f"Target Result: 62.5%")
    print(f"Actual Result: {final_pct}%")

    if final_pct == 62.5:
        print("✅ SUCCESS: Simple average scoring verified.")
    else:
        print("❌ FAILURE: Incorrect calculation.")
        exit(1)

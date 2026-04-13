import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def test_pure_vector_config():
    print("\n=== Testing AdvancedGapEngine Configuration ===")
    
    # 1. Test Pure Vector Mode
    with patch.dict(os.environ, {"GAP_MATCHING_LAYERS": "vector", "GAP_VECTOR_PURE_SCORING": "true"}):
        from services.analysis_service.engine.advanced_gap_engine import AdvancedGapEngine
        engine = AdvancedGapEngine()
        print(f"Active Layers: {engine.active_layers}")
        print(f"Pure Vector Mode: {engine.pure_vector_mode}")
        
        # Verify Tier 1 is skipped
        req = {"skill_name": "React", "target_level": "Senior", "years_required": 5, "vector": [0.1]*1536}
        user_skills_data = [{"name": "React", "level": "Junior", "years_exp": 1, "vector": [0.1]*1536}]
        cv_norm_names = ["react"]
        
        # Mock Tier 2 to return a known similarity
        with patch.object(engine, '_match_tier2_vector', return_value={"score": 0.95, "details": {"cosine_sim": 0.95}}):
            res = await engine._process_individual_req(req, user_skills_data, cv_norm_names)
            print(f"Tier Used: {res['tier']} (Expected: 2 because exact layer is disabled)")
            print(f"Score: {res['score']} (Expected: 0.95 because pure_vector_mode is true)")

    # 2. Test Hybrid Mode
    with patch.dict(os.environ, {"GAP_MATCHING_LAYERS": "exact,vector", "GAP_VECTOR_PURE_SCORING": "false"}):
        engine_h = AdvancedGapEngine()
        print(f"\nActive Layers: {engine_h.active_layers}")
        print(f"Pure Vector Mode: {engine_h.pure_vector_mode}")
        
        # Verify Tier 1 is used
        res_h = await engine_h._process_individual_req(req, user_skills_data, cv_norm_names)
        print(f"Tier Used: {res_h['tier']} (Expected: 1 for exact match)")
        print(f"Score: {res_h['score']} (Expected: 1.0 for exact/alias)")

if __name__ == "__main__":
    asyncio.run(test_pure_vector_config())

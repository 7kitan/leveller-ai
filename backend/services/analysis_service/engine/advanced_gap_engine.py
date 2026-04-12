import re
import logging
import httpx
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger("gap_calculator.advanced_engine")

class AdvancedGapEngine:
    def __init__(self):
        self.bertscore_api_url = os.getenv("BERTSCORE_API_URL")
        self.bertscore_api_key = os.getenv("BERTSCORE_API_KEY", "")
        
        # Tier 1: Alias Dictionary
        self.alias_map = {
            "nodejs": "node_js",
            "node": "node_js",
            "reactjs": "react",
            "react": "react",
            "vuejs": "vue",
            "vue": "vue",
            "golang": "go",
            "go": "go",
            "typescript": "ts",
            "typescriptjs": "ts",
            "javascript": "js",
            "js": "js",
            "mongodb": "mongo",
            "postgresql": "postgres",
            "postgres": "postgres",
            "mssql": "sqlserver",
            "aws": "amazon_web_services",
            "gcp": "google_cloud_platform",
        }

    def _normalize(self, text: str) -> str:
        """Chuẩn hóa: lowercase và xóa ký tự đặc biệt thừa."""
        if not text:
            return ""
        # Lowercase
        text = text.lower()
        # Xóa các ký tự đặc biệt thừa (., -, khoảng trắng)
        text = re.sub(r'[^a-zA-Z0-9]', '', text)
        return text

    def _get_canonical_name(self, name: str) -> str:
        """Chuyển đổi tên sang tên chuẩn thông qua Alias Dictionary."""
        norm = self._normalize(name)
        return self.alias_map.get(norm, norm)

    async def _match_tier1(self, req_name: str, cv_norm_names: List[str]) -> float:
        """Tầng 1: Exact Match & Alias Match (Khớp tuyệt đối)."""
        req_canonical = self._get_canonical_name(req_name)
        if req_canonical in cv_norm_names:
            return 1.0
        return 0.0

    async def _match_tier2(self, req_name: str, cv_skills_list: List[str]) -> float:
        """Tầng 2: Semantic/Partial Match (Khớp ngữ nghĩa/Tương đồng)."""
        if not self.bertscore_api_url or not cv_skills_list:
            return 0.0
            
        try:
            payload = {
                "cv_skills": cv_skills_list,
                "jd_skill": req_name
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.bertscore_api_url,
                    json=payload,
                    headers={"X-AI-Key": self.bertscore_api_key} if self.bertscore_api_key else {}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    score = float(data.get("score", 0))
                    
                    # Ngưỡng (Threshold) logic as requested
                    if score >= 0.85:
                        return 1.0
                    elif score >= 0.75:
                        return 0.5  # Partial Match
                    else:
                        return 0.0
        except Exception as e:
            logger.error(f"Tier 2 Semantic match failed for {req_name}: {e}")
            
        return 0.0

    async def calculate_match(self, cv_skills_list: List[str], jd_requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Tầng 3: Tính toán Skill Gap Score (Chỉ số thiếu hụt)."""
        
        # Chuẩn hóa toàn bộ list CV một lần
        cv_norm_names = [self._get_canonical_name(s) for s in cv_skills_list]
        
        must_have_results = []
        nice_to_have_results = []
        
        processed_breakdown = {"met": [], "gap": [], "partial": []}
        
        for req in jd_requirements:
            name = req.get("skill_name", "Unknown")
            is_mandatory = req.get("is_mandatory", True)
            
            # Tier 1
            score = await self._match_tier1(name, cv_norm_names)
            tier_used = 1
            
            # Tier 2 if Tier 1 failed
            if score < 1.0:
                semantic_score = await self._match_tier2(name, cv_skills_list)
                if semantic_score > score:
                    score = semantic_score
                    tier_used = 2
            
            res_item = {
                "skill": name,
                "score": score,
                "tier": tier_used,
                "is_mandatory": is_mandatory
            }
            
            if is_mandatory:
                must_have_results.append(res_item)
            else:
                nice_to_have_results.append(res_item)
                
            # Breakdown classification for frontend
            if score >= 0.85:
                processed_breakdown["met"].append({**res_item, "score": score * 100})
            elif score > 0:
                processed_breakdown["partial"].append({**res_item, "score": score * 100})
            else:
                processed_breakdown["gap"].append({**res_item, "score": 0})

        # Final Scoring logic (Tier 3)
        # Độ khớp = [ (Tổng điểm Must-have CV đạt / Tổng Must-have JD) * 0.7 ] + [ (Tổng điểm Nice CV đạt / Tổng Nice JD) * 0.3 ]
        
        must_count = len(must_have_results)
        nice_count = len(nice_to_have_results)
        
        must_match_ratio = sum(r["score"] for r in must_have_results) / must_count if must_count > 0 else 1.0
        nice_match_ratio = sum(r["score"] for r in nice_to_have_results) / nice_count if nice_count > 0 else 1.0
        
        # Nếu chỉ có 1 trong 2 loại thì dồn trọng số? 
        # User nói: 70% Must, 30% Nice. Nếu không có Nice thì tính 100% Must?
        # Thường tính theo tỷ lệ:
        if must_count > 0 and nice_count > 0:
            overall_match_pct = (must_match_ratio * 0.7 + nice_match_ratio * 0.3) * 100
        elif must_count > 0:
            overall_match_pct = must_match_ratio * 100
        elif nice_count > 0:
            overall_match_pct = nice_match_ratio * 100
        else:
            overall_match_pct = 0
            
        return {
            "overall_match_pct": round(overall_match_pct, 1),
            "breakdown": processed_breakdown,
            "must_have_score": round(must_match_ratio * 100, 1),
            "nice_to_have_score": round(nice_match_ratio * 100, 1)
        }

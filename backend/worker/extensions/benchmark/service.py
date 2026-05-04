import uuid
import time
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, List
from sqlalchemy.orm import Session

from shared.models import LLMBenchmarkSession, LLMBenchmarkResult, LLMTestSet, LLMTestCase
from .interceptor import is_benchmark_active, benchmark_data

logger = logging.getLogger("benchmark_service")

class BenchmarkService:
    def __init__(self, db: Session):
        self.db = db

    async def run_session(self, test_set_id: str, model_config: Dict[str, str], user_id: str = None):
        """
        Run a full benchmark session for a test set.
        
        Args:
            test_set_id: ID of the test set to run.
            model_config: Dictionary of model overrides (e.g. {"cv_parsing_model": "gpt-4o"}).
            user_id: ID of the admin running the benchmark.
        """
        test_set = self.db.query(LLMTestSet).filter(LLMTestSet.id == test_set_id).first()
        if not test_set:
            raise ValueError(f"Test set {test_set_id} not found")

        logger.info(f"[BENCHMARK] Starting session for test set '{test_set.name}' ({test_set.id})")

        # 1. Create Session record
        session = LLMBenchmarkSession(
            id=uuid.uuid4(),
            test_set_id=test_set.id,
            model_config=model_config,
            status="running",
            created_by=user_id
        )
        self.db.add(session)
        self.db.commit()

        try:
            total_score = 0.0
            total_latency = 0
            total_tokens = 0
            cases_count = len(test_set.test_cases)
            
            # 2. Iterate Test Cases
            for idx, case in enumerate(test_set.test_cases, 1):
                logger.info(f"[BENCHMARK] Session {session.id}: Running test case {idx}/{cases_count}")
                result = await self._run_test_case(case, model_config, session.id)
                
                if result.status == "success":
                    total_score += (result.score or 0.0)
                    total_latency += (result.latency_ms or 0)
                    total_tokens += ((result.prompt_tokens or 0) + (result.completion_tokens or 0))
            
            # 3. Finalize Session
            session.status = "completed"
            session.overall_score = (total_score / cases_count) if cases_count > 0 else 0.0
            session.total_latency_ms = total_latency
            session.total_tokens = total_tokens
            session.completed_at = datetime.now()
            self.db.commit()
            
            logger.info(f"[BENCHMARK] Session {session.id} COMPLETED | score={session.overall_score:.2f}")
            return session
            
        except Exception as e:
            logger.error(f"[BENCHMARK] Session {session.id} FAILED: {e}", exc_info=True)
            session.status = "failed"
            self.db.commit()
            raise

    async def _run_test_case(self, case: LLMTestCase, model_config: Dict[str, str], session_id: uuid.UUID):
        """
        Run a single test case within the benchmark context.
        """
        # Set thread-local context variables for the interceptor
        active_token = is_benchmark_active.set(True)
        data_token = benchmark_data.set({"calls": []})
        
        t0 = time.monotonic()
        try:
            # 1. Execute the flow based on test_set.flow_type
            flow_type = case.test_set.flow_type
            actual_output = await self._execute_flow(flow_type, case.input_data, model_config)
            
            latency = int((time.monotonic() - t0) * 1000)
            
            # 2. Evaluate output against reference using judge models
            evaluation = await self._evaluate(
                actual_output=actual_output, 
                reference_output=case.reference_output, 
                flow_type=flow_type,
                model_config=model_config  # Pass model_config for judge models
            )
            
            # 3. Gather intercepted LLM call metrics
            intercepted = benchmark_data.get()
            calls = intercepted.get("calls", [])
            
            p_tokens = sum(c.get("prompt_tokens", 0) for c in calls)
            c_tokens = sum(c.get("completion_tokens", 0) for c in calls)
            
            # 4. Create Result record
            result = LLMBenchmarkResult(
                id=uuid.uuid4(),
                session_id=session_id,
                test_case_id=case.id,
                actual_output=actual_output,
                score=evaluation.get("score", 0.0),
                metrics=evaluation.get("metrics", {}),
                latency_ms=latency,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                status="success"
            )
            
            # Aggregate tokens if captured in interceptor (simplified for now)
            # In a real implementation, we'd sum tokens from all calls
            
            self.db.add(result)
            self.db.commit()
            return result
            
        except Exception as e:
            logger.error(f"[BENCHMARK] Test case {case.id} failed: {e}")
            result = LLMBenchmarkResult(
                id=uuid.uuid4(),
                session_id=session_id,
                test_case_id=case.id,
                status="error",
                error_message=str(e)
            )
            self.db.add(result)
            self.db.commit()
            return result
        finally:
            # Clean up context variables
            is_benchmark_active.reset(active_token)
            benchmark_data.reset(data_token)

    async def _execute_flow(self, flow_type: str, input_data: Dict, model_config: Dict):
        """
        Dispatches to the correct LangGraph flow based on flow_type.
        
        Supported flow_types:
        - cv_parsing_v3: Parse CV from raw text
        - jd_parsing: Extract requirements from Job Description
        - gap_analysis_from_requirements: Gap analysis with pre-parsed JD requirements
        - gap_analysis_merged: JD extraction + gap analysis in one call
        - full_cv_to_gap: Full pipeline (CV parsing + gap analysis)
        - course_recommendation: Course recommendation based on gaps
        """
        if flow_type == "cv_parsing_v3":
            # For CV parsing, input_data should contain 'cv_id'
            from ...langgraph_agents.gap_v3.cv_parsing_graph import run_cv_parsing_pipeline
            
            cv_id = input_data.get("cv_id")
            if not cv_id:
                raise ValueError("cv_id is required for cv_parsing_v3 flow")
                
            result = await run_cv_parsing_pipeline(cv_id=cv_id, user_id="00000000-0000-0000-0000-000000000000", db=self.db)
            return result
            
        elif flow_type == "jd_parsing":
            # For JD parsing, input_data should contain 'job_id'
            # This extracts requirements from Job Description
            from shared.models import Job
            
            job_id = input_data.get("job_id")
            if not job_id:
                raise ValueError("job_id is required for jd_parsing flow")
            
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            # Check if requirements already extracted
            if job.extracted_requirements_json:
                logger.info(f"[BENCHMARK] Job {job_id} already has extracted requirements")
                return job.extracted_requirements_json
            
            # Extract requirements using skill extraction service
            from shared.skill_extraction import extract_and_save_job_skills
            result = extract_and_save_job_skills(job_id=job_id, db=self.db)
            
            # Refresh job to get updated extracted_requirements_json
            self.db.refresh(job)
            return job.extracted_requirements_json or result
            
        elif flow_type == "gap_analysis_from_requirements":
            # Gap analysis with pre-parsed JD requirements
            from ...langgraph_agents.gap_v3.orchestrator import run_gap_analysis_v3
            
            cv_id = input_data.get("cv_id")
            job_id = input_data.get("job_id")
            
            if not cv_id or not job_id:
                raise ValueError("cv_id and job_id are required for gap_analysis_from_requirements flow")
            
            # Assumes CV is already parsed and JD requirements are already extracted
            result = await run_gap_analysis_v3(cv_id=cv_id, job_id=job_id, user_id="00000000-0000-0000-0000-000000000000", db=self.db)
            return result
            
        elif flow_type == "gap_analysis_merged" or flow_type == "full_cv_to_gap":
            # Full end-to-end: CV parsing → Gap Analysis
            # Note: gap_analysis_merged is the SQL name, full_cv_to_gap is legacy name
            from ...langgraph_agents.gap_v3.cv_parsing_graph import run_cv_parsing_pipeline
            from ...langgraph_agents.gap_v3.orchestrator import run_gap_analysis_v3
            
            cv_id = input_data.get("cv_id")
            job_id = input_data.get("job_id")
            
            if not cv_id or not job_id:
                raise ValueError("cv_id and job_id are required for gap_analysis_merged flow")

            # Run CV parsing (uses existing parsed data if available)
            await run_cv_parsing_pipeline(cv_id=cv_id, user_id="00000000-0000-0000-0000-000000000000", db=self.db)
            
            # Run Gap Analysis
            result = await run_gap_analysis_v3(cv_id=cv_id, job_id=job_id, user_id="00000000-0000-0000-0000-000000000000", db=self.db)
            return result
            
        elif flow_type == "course_recommendation":
            # Course recommendation based on skill gaps
            logger.warning(f"[BENCHMARK] course_recommendation flow not yet implemented")
            # TODO: Implement course recommendation flow
            # For now, return mock data
            return {
                "selected_courses": [],
                "career_roadmap": {
                    "stages": [],
                    "total_weeks": 0,
                    "summary": "Course recommendation not yet implemented"
                }
            }

        # Unknown flow type
        raise NotImplementedError(
            f"Benchmark flow '{flow_type}' is not supported yet. "
            f"Supported: cv_parsing_v3, jd_parsing, gap_analysis_from_requirements, "
            f"gap_analysis_merged, full_cv_to_gap, course_recommendation"
        )

    async def _evaluate(self, actual_output: Any, reference_output: Any, flow_type: str, model_config: Dict) -> Dict:
        """
        Evaluates the quality of the actual output compared to the reference.
        Uses real LLM judge models to score the output.
        
        Supports:
        - single_judge: One judge model
        - dual_judge: Two judge models with aggregation
        - ensemble: Multiple judge models with weighted aggregation
        """
        evaluation_strategy = model_config.get("evaluation_strategy", "single_judge")
        
        if evaluation_strategy == "dual_judge":
            return await self._evaluate_dual_judge(actual_output, reference_output, flow_type, model_config)
        elif evaluation_strategy == "ensemble":
            return await self._evaluate_ensemble(actual_output, reference_output, flow_type, model_config)
        else:  # single_judge
            return await self._evaluate_single_judge(actual_output, reference_output, flow_type, model_config)
    
    async def _evaluate_single_judge(self, actual_output: Any, reference_output: Any, flow_type: str, model_config: Dict) -> Dict:
        """Single judge evaluation using CORE ai_service (not internal llm_helpers)"""
        judge_model = model_config.get("judge_model", "gpt-4o")
        
        judge_prompt = self._build_judge_prompt(actual_output, reference_output, flow_type)
        
        # ✅ USE CORE AI_SERVICE - Extension should not use internal functions
        from shared.ai_service import generate_completion
        import json as _json
        
        try:
            response = generate_completion(
                prompt=judge_prompt,
                system_prompt="You are an expert evaluator. Return ONLY valid JSON.",
                model=judge_model,
                json_mode=True,
                temperature=0.0,
                call_name=f"benchmark_judge_{flow_type}",
                user_id="00000000-0000-0000-0000-000000000000"
            )
            
            if not response:
                logger.warning("[BENCHMARK] Judge model returned empty result")
                return {"score": 0.0, "metrics": {}}
            
            # Parse JSON response
            result = _json.loads(response)
            
        except Exception as e:
            logger.error(f"[BENCHMARK] Judge evaluation failed: {e}")
            return {"score": 0.0, "metrics": {}}
        
        # Extract metrics
        metrics = {
            "faithfulness": result.get("faithfulness", 0.0),
            "relevancy": result.get("relevancy", 0.0),
            "completeness": result.get("completeness", 0.0),
            "reasoning": result.get("reasoning", "")
        }
        
        # Calculate overall score
        score = (
            metrics["faithfulness"] * 0.5 +
            metrics["relevancy"] * 0.3 +
            metrics["completeness"] * 0.2
        )
        
        return {
            "score": score,
            "metrics": metrics
        }
    
    async def _evaluate_dual_judge(self, actual_output: Any, reference_output: Any, flow_type: str, model_config: Dict) -> Dict:
        """Dual judge evaluation with two models using CORE ai_service"""
        judge_primary = model_config.get("judge_model_primary", "gpt-4o")
        judge_secondary = model_config.get("judge_model_secondary", "claude-3-5-sonnet-20241022")
        aggregation = model_config.get("aggregation", "average")  # average | max | min | weighted
        
        judge_prompt = self._build_judge_prompt(actual_output, reference_output, flow_type)
        
        # ✅ USE CORE AI_SERVICE - Extension should not use internal functions
        from shared.ai_service import generate_completion
        import json as _json
        import asyncio
        
        # Helper to call judge and parse JSON
        def call_judge(model: str, judge_name: str):
            try:
                response = generate_completion(
                    prompt=judge_prompt,
                    system_prompt="You are an expert evaluator. Return ONLY valid JSON.",
                    model=model,
                    json_mode=True,
                    temperature=0.0,
                    call_name=f"benchmark_judge_{judge_name}_{flow_type}",
                    user_id="00000000-0000-0000-0000-000000000000"
                )
                if not response:
                    return None
                return _json.loads(response)
            except Exception as e:
                logger.error(f"[BENCHMARK] {judge_name} judge failed: {e}")
                return None
        
        # Call both judges in parallel using thread pool (since generate_completion is sync)
        loop = asyncio.get_event_loop()
        results = await asyncio.gather(
            loop.run_in_executor(None, call_judge, judge_primary, "primary"),
            loop.run_in_executor(None, call_judge, judge_secondary, "secondary"),
            return_exceptions=True
        )
        
        result_primary, result_secondary = results
        
        # Handle errors
        if isinstance(result_primary, Exception):
            logger.error(f"[BENCHMARK] Primary judge failed: {result_primary}")
            result_primary = None
        
        if isinstance(result_secondary, Exception):
            logger.error(f"[BENCHMARK] Secondary judge failed: {result_secondary}")
            result_secondary = None
        
        if not result_primary and not result_secondary:
            logger.error("[BENCHMARK] Both judges failed")
            return {"score": 0.0, "metrics": {}}
        
        # Extract metrics from both judges
        metrics_primary = {
            "faithfulness": result_primary.get("faithfulness", 0.0) if result_primary else 0.0,
            "relevancy": result_primary.get("relevancy", 0.0) if result_primary else 0.0,
            "completeness": result_primary.get("completeness", 0.0) if result_primary else 0.0,
            "reasoning": result_primary.get("reasoning", "") if result_primary else ""
        }
        
        metrics_secondary = {
            "faithfulness": result_secondary.get("faithfulness", 0.0) if result_secondary else 0.0,
            "relevancy": result_secondary.get("relevancy", 0.0) if result_secondary else 0.0,
            "completeness": result_secondary.get("completeness", 0.0) if result_secondary else 0.0,
            "reasoning": result_secondary.get("reasoning", "") if result_secondary else ""
        }
        
        # Aggregate scores
        if aggregation == "average":
            aggregated_metrics = {
                "faithfulness": (metrics_primary["faithfulness"] + metrics_secondary["faithfulness"]) / 2,
                "relevancy": (metrics_primary["relevancy"] + metrics_secondary["relevancy"]) / 2,
                "completeness": (metrics_primary["completeness"] + metrics_secondary["completeness"]) / 2
            }
        elif aggregation == "max":
            aggregated_metrics = {
                "faithfulness": max(metrics_primary["faithfulness"], metrics_secondary["faithfulness"]),
                "relevancy": max(metrics_primary["relevancy"], metrics_secondary["relevancy"]),
                "completeness": max(metrics_primary["completeness"], metrics_secondary["completeness"])
            }
        elif aggregation == "min":
            aggregated_metrics = {
                "faithfulness": min(metrics_primary["faithfulness"], metrics_secondary["faithfulness"]),
                "relevancy": min(metrics_primary["relevancy"], metrics_secondary["relevancy"]),
                "completeness": min(metrics_primary["completeness"], metrics_secondary["completeness"])
            }
        else:  # weighted (default: 60% primary, 40% secondary)
            weight_primary = model_config.get("weight_primary", 0.6)
            weight_secondary = 1.0 - weight_primary
            
            aggregated_metrics = {
                "faithfulness": metrics_primary["faithfulness"] * weight_primary + metrics_secondary["faithfulness"] * weight_secondary,
                "relevancy": metrics_primary["relevancy"] * weight_primary + metrics_secondary["relevancy"] * weight_secondary,
                "completeness": metrics_primary["completeness"] * weight_primary + metrics_secondary["completeness"] * weight_secondary
            }
        
        # Calculate overall score
        score = (
            aggregated_metrics["faithfulness"] * 0.5 +
            aggregated_metrics["relevancy"] * 0.3 +
            aggregated_metrics["completeness"] * 0.2
        )
        
        return {
            "score": score,
            "metrics": {
                "judge_primary": metrics_primary,
                "judge_secondary": metrics_secondary,
                "aggregated": aggregated_metrics,
                "aggregation_method": aggregation
            }
        }
    
    async def _evaluate_ensemble(self, actual_output: Any, reference_output: Any, flow_type: str, model_config: Dict) -> Dict:
        """Ensemble evaluation with multiple weighted judges using CORE ai_service"""
        judge_models = model_config.get("judge_models", [
            {"model": "gpt-4o", "weight": 0.5},
            {"model": "claude-3-5-sonnet-20241022", "weight": 0.5}
        ])
        
        judge_prompt = self._build_judge_prompt(actual_output, reference_output, flow_type)
        
        # ✅ USE CORE AI_SERVICE - Extension should not use internal functions
        from shared.ai_service import generate_completion
        import json as _json
        import asyncio
        
        # Helper to call judge and parse JSON
        def call_judge(model: str, judge_name: str):
            try:
                response = generate_completion(
                    prompt=judge_prompt,
                    system_prompt="You are an expert evaluator. Return ONLY valid JSON.",
                    model=model,
                    json_mode=True,
                    temperature=0.0,
                    call_name=f"benchmark_judge_{judge_name}_{flow_type}",
                    user_id="00000000-0000-0000-0000-000000000000"
                )
                if not response:
                    return None
                return _json.loads(response)
            except Exception as e:
                logger.error(f"[BENCHMARK] Judge {judge_name} failed: {e}")
                return None
        
        # Call all judges in parallel using thread pool
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, call_judge, judge["model"], f"ensemble_{i}")
            for i, judge in enumerate(judge_models)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate with weights
        total_weight = 0.0
        weighted_faithfulness = 0.0
        weighted_relevancy = 0.0
        weighted_completeness = 0.0
        
        judge_results = []
        
        for i, (result, judge_config) in enumerate(zip(results, judge_models)):
            if isinstance(result, Exception) or not result:
                logger.warning(f"[BENCHMARK] Judge {judge_config['model']} failed")
                continue
            
            weight = judge_config["weight"]
            metrics = {
                "faithfulness": result.get("faithfulness", 0.0),
                "relevancy": result.get("relevancy", 0.0),
                "completeness": result.get("completeness", 0.0),
                "reasoning": result.get("reasoning", "")
            }
            
            judge_results.append({
                "model": judge_config["model"],
                "weight": weight,
                "metrics": metrics
            })
            
            weighted_faithfulness += metrics["faithfulness"] * weight
            weighted_relevancy += metrics["relevancy"] * weight
            weighted_completeness += metrics["completeness"] * weight
            total_weight += weight
        
        if total_weight == 0:
            logger.error("[BENCHMARK] All ensemble judges failed")
            return {"score": 0.0, "metrics": {}}
        
        # Normalize by total weight
        aggregated_metrics = {
            "faithfulness": weighted_faithfulness / total_weight,
            "relevancy": weighted_relevancy / total_weight,
            "completeness": weighted_completeness / total_weight
        }
        
        score = (
            aggregated_metrics["faithfulness"] * 0.5 +
            aggregated_metrics["relevancy"] * 0.3 +
            aggregated_metrics["completeness"] * 0.2
        )
        
        return {
            "score": score,
            "metrics": {
                "judges": judge_results,
                "aggregated": aggregated_metrics,
                "total_weight": total_weight
            }
        }
    
    def _build_judge_prompt(self, actual_output: Any, reference_output: Any, flow_type: str) -> str:
        """
        Build judge prompt based on flow type.
        
        If reference_output is None or empty, use reference-free evaluation.
        Otherwise, compare actual_output against reference_output.
        """
        import json
        
        actual_json = json.dumps(actual_output, ensure_ascii=False, indent=2)
        
        # Check if we have reference output
        has_reference = reference_output is not None and reference_output != {} and reference_output != ""
        
        if has_reference:
            reference_json = json.dumps(reference_output, ensure_ascii=False, indent=2)
        else:
            reference_json = None
        
        if flow_type == "cv_parsing_v3":
            if has_reference:
                return f"""You are an expert evaluator for CV parsing systems. Rate the quality of the actual output compared to the reference (ground truth).

## Reference Output (Ground Truth):
{reference_json}

## Actual Output:
{actual_json}

## Evaluation Criteria:

1. **Faithfulness** (0.0-1.0): How accurately does the actual output match the reference?
   - Check if extracted fields (name, skills, experience) match ground truth
   - Penalize missing or incorrect information
   - Penalize hallucinated information not in reference

2. **Relevancy** (0.0-1.0): Is the output relevant and useful?
   - Are the extracted skills relevant to the CV content?
   - Is the seniority level appropriate?
   - Are work history entries meaningful?

3. **Completeness** (0.0-1.0): Are all required fields present?
   - Check if all expected fields are extracted
   - Verify skills list is comprehensive
   - Ensure work history is complete

## Output JSON:
{{
  "faithfulness": 0.0-1.0,
  "relevancy": 0.0-1.0,
  "completeness": 0.0-1.0,
  "reasoning": "Brief explanation of scores (2-3 sentences)"
}}

Return ONLY valid JSON."""
            else:
                # Reference-free evaluation
                return f"""You are an expert evaluator for CV parsing systems. Rate the quality of the actual output (no ground truth available).

## Actual Output:
{actual_json}

## Evaluation Criteria (Reference-Free):

1. **Faithfulness** (0.0-1.0): Does the output look reasonable and well-structured?
   - Check if all required fields are present (full_name, skills, experience_years_total, etc.)
   - Penalize missing critical fields
   - Penalize obviously incorrect data (e.g., negative years, empty arrays)

2. **Relevancy** (0.0-1.0): Is the output relevant and useful?
   - Are the extracted skills reasonable for a CV?
   - Is the seniority level appropriate for the experience years?
   - Are work history entries meaningful?

3. **Completeness** (0.0-1.0): Are all required fields present and populated?
   - Check if full_name, summary, skills, work_history are present
   - Verify skills list is not empty
   - Ensure experience_years_total is reasonable

## Output JSON:
{{
  "faithfulness": 0.0-1.0,
  "relevancy": 0.0-1.0,
  "completeness": 0.0-1.0,
  "reasoning": "Brief explanation of scores (2-3 sentences)"
}}

Return ONLY valid JSON."""

        elif flow_type == "jd_parsing":
            if has_reference:
                return f"""You are an expert evaluator for Job Description parsing systems. Rate the quality of the actual output compared to the reference (ground truth).

## Reference Output (Ground Truth):
{reference_json}

## Actual Output:
{actual_json}

## Evaluation Criteria:

1. **Faithfulness** (0.0-1.0): How accurately does the actual output match the reference?
   - Check if extracted requirements match ground truth
   - Verify skill names, required levels, and years match
   - Penalize missing or incorrect requirements
   - Penalize hallucinated requirements not in reference

2. **Relevancy** (0.0-1.0): Is the output relevant and useful?
   - Are the extracted skills relevant to the job?
   - Are the required levels appropriate (Junior/Mid-level/Senior)?
   - Are the importance weights reasonable?
   - Are mandatory vs optional flags correct?

3. **Completeness** (0.0-1.0): Are all required fields present?
   - Check if all expected requirements are extracted
   - Verify skill groups are properly identified
   - Ensure alternative skills are captured for OR conditions

## Output JSON:
{{
  "faithfulness": 0.0-1.0,
  "relevancy": 0.0-1.0,
  "completeness": 0.0-1.0,
  "reasoning": "Brief explanation of scores (2-3 sentences)"
}}

Return ONLY valid JSON."""
            else:
                # Reference-free evaluation
                return f"""You are an expert evaluator for Job Description parsing systems. Rate the quality of the actual output (no ground truth available).

## Actual Output:
{actual_json}

## Evaluation Criteria (Reference-Free):

1. **Faithfulness** (0.0-1.0): Does the output look reasonable and well-structured?
   - Check if requirements array is present and non-empty
   - Verify each requirement has required fields (skill, target_level, years_required, is_mandatory, importance_weight)
   - Penalize missing critical fields
   - Check if skill groups (is_group=true) have alternative_skills array

2. **Relevancy** (0.0-1.0): Is the output relevant and useful?
   - Are the extracted skills reasonable for a job description?
   - Are the required levels appropriate (not all Senior or all Junior)?
   - Are the importance weights distributed reasonably (not all 10)?
   - Are mandatory flags used appropriately (not all true or all false)?

3. **Completeness** (0.0-1.0): Are all required fields present and populated?
   - Each requirement has: skill, target_level, years_required, is_mandatory, importance_weight
   - Skill groups have: is_group=true, group_strategy, alternative_skills
   - At least 3-5 requirements extracted (unless very simple JD)

## Output JSON:
{{
  "faithfulness": 0.0-1.0,
  "relevancy": 0.0-1.0,
  "completeness": 0.0-1.0,
  "reasoning": "Brief explanation of scores (2-3 sentences)"
}}

Return ONLY valid JSON."""

        elif flow_type in ["gap_analysis_from_requirements", "gap_analysis_merged"]:
            if has_reference:
                return f"""You are an expert evaluator for gap analysis systems. Rate the quality of the actual output compared to the reference (ground truth).

## Reference Output (Ground Truth):
{reference_json}

## Actual Output:
{actual_json}

## Evaluation Criteria:

1. **Faithfulness** (0.0-1.0): How accurately does the gap analysis match the reference?
   - Check if overall_match_pct is close to reference (within ±10%)
   - Verify identified skill gaps match ground truth
   - Check if severity levels are appropriate

2. **Relevancy** (0.0-1.0): Is the analysis relevant and actionable?
   - Are the identified gaps truly important?
   - Are the learning paths practical?
   - Is the overall assessment meaningful?

3. **Completeness** (0.0-1.0): Are all required elements present?
   - All expected gaps identified
   - Match breakdown provided
   - Strengths and weaknesses listed

## Output JSON:
{{
  "faithfulness": 0.0-1.0,
  "relevancy": 0.0-1.0,
  "completeness": 0.0-1.0,
  "reasoning": "Brief explanation of scores (2-3 sentences)"
}}

Return ONLY valid JSON."""
            else:
                # Reference-free evaluation
                return f"""You are an expert evaluator for gap analysis systems. Rate the quality of the actual output (no ground truth available).

## Actual Output:
{actual_json}

## Evaluation Criteria (Reference-Free):

1. **Faithfulness** (0.0-1.0): Does the gap analysis look reasonable?
   - Check if overall_match_pct is between 0-100
   - Verify skill_gaps are well-structured with required fields
   - Check if severity levels are appropriate (High/Medium/Low)

2. **Relevancy** (0.0-1.0): Is the analysis relevant and actionable?
   - Are the identified gaps truly important for the job?
   - Are the learning paths practical and specific?
   - Is the overall assessment meaningful?

3. **Completeness** (0.0-1.0): Are all required elements present?
   - overall_match_pct present
   - skill_gaps array present (can be empty if perfect match)
   - match_breakdown present
   - overall_assessment present

## Output JSON:
{{
  "faithfulness": 0.0-1.0,
  "relevancy": 0.0-1.0,
  "completeness": 0.0-1.0,
  "reasoning": "Brief explanation of scores (2-3 sentences)"
}}

Return ONLY valid JSON."""

        elif flow_type == "course_recommendation":
            if has_reference:
                return f"""You are an expert evaluator for course recommendation systems. Rate the quality of the actual output compared to the reference (ground truth).

## Reference Output (Ground Truth):
{reference_json}

## Actual Output:
{actual_json}

## Evaluation Criteria:

1. **Faithfulness** (0.0-1.0): How well do the recommendations match the reference?
   - Are the selected courses relevant to the gaps?
   - Is the roadmap structure similar to reference?
   - Are the timelines realistic?

2. **Relevancy** (0.0-1.0): Are the recommendations truly relevant?
   - Do selected courses teach the required skills?
   - Are there any irrelevant course selections? (penalize heavily)
   - Is the roadmap progression logical?

3. **Completeness** (0.0-1.0): Are all gaps addressed?
   - All major gaps have course recommendations
   - Roadmap covers all stages
   - Milestones are defined

## Output JSON:
{{
  "faithfulness": 0.0-1.0,
  "relevancy": 0.0-1.0,
  "completeness": 0.0-1.0,
  "reasoning": "Brief explanation of scores (2-3 sentences)"
}}

Return ONLY valid JSON."""
            else:
                # Reference-free evaluation
                return f"""You are an expert evaluator for course recommendation systems. Rate the quality of the actual output (no ground truth available).

## Actual Output:
{actual_json}

## Evaluation Criteria (Reference-Free):

1. **Faithfulness** (0.0-1.0): Does the recommendation look reasonable?
   - Are selected_courses well-structured?
   - Is career_roadmap present with stages?
   - Are timelines realistic (not too short or too long)?

2. **Relevancy** (0.0-1.0): Are the recommendations truly relevant?
   - Do selected courses match the gap_skills they claim to address?
   - Are there any obviously irrelevant selections?
   - Is the roadmap progression logical?

3. **Completeness** (0.0-1.0): Are all required elements present?
   - selected_courses array present
   - career_roadmap present with stages
   - Each stage has duration, skills_acquired, milestones

## Output JSON:
{{
  "faithfulness": 0.0-1.0,
  "relevancy": 0.0-1.0,
  "completeness": 0.0-1.0,
  "reasoning": "Brief explanation of scores (2-3 sentences)"
}}

Return ONLY valid JSON."""

        else:
            # Generic judge prompt
            if has_reference:
                return f"""You are an expert evaluator. Rate the quality of the actual output compared to the reference (ground truth).

## Reference Output (Ground Truth):
{reference_json}

## Actual Output:
{actual_json}

## Evaluation Criteria:

1. **Faithfulness** (0.0-1.0): How accurately does the actual output match the reference?
2. **Relevancy** (0.0-1.0): Is the output relevant and useful?
3. **Completeness** (0.0-1.0): Are all required elements present?

## Output JSON:
{{
  "faithfulness": 0.0-1.0,
  "relevancy": 0.0-1.0,
  "completeness": 0.0-1.0,
  "reasoning": "Brief explanation of scores (2-3 sentences)"
}}

Return ONLY valid JSON."""
            else:
                # Reference-free evaluation
                return f"""You are an expert evaluator. Rate the quality of the actual output (no ground truth available).

## Actual Output:
{actual_json}

## Evaluation Criteria (Reference-Free):

1. **Faithfulness** (0.0-1.0): Does the output look reasonable and well-structured?
2. **Relevancy** (0.0-1.0): Is the output relevant and useful?
3. **Completeness** (0.0-1.0): Are all required elements present?

## Output JSON:
{{
  "faithfulness": 0.0-1.0,
  "relevancy": 0.0-1.0,
  "completeness": 0.0-1.0,
  "reasoning": "Brief explanation of scores (2-3 sentences)"
}}

Return ONLY valid JSON."""

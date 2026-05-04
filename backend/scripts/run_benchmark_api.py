"""
Script to run LLM benchmarks via API with REAL data.
This is the RECOMMENDED way to run benchmarks (not RAGAS).

Usage:
    python -m scripts.run_benchmark_api --test-set-id <uuid>
    python -m scripts.run_benchmark_api --test-set-name "CV Parsing - Quality Benchmark"
    python -m scripts.run_benchmark_api --all

Features:
    - Uses proper LLM-as-a-judge evaluation
    - Supports multiple evaluation strategies (single_judge, dual_judge, ensemble)
    - Tracks latency, tokens, and detailed metrics
    - Exports results to CSV/JSON

Requirements:
    - Admin service must be running on http://localhost:8001
    - Worker must be running to process benchmark tasks
    - Test cases must have real CV/Job IDs (run populate_real_benchmark_data.py first)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests
import time
import argparse
from shared.database import SessionLocal
from shared.models import LLMTestSet, LLMBenchmarkSession
from datetime import datetime

# Admin API configuration
ADMIN_API_URL = os.getenv("ADMIN_API_URL", "http://localhost:8001")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@team078.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def login_admin():
    """Login and get admin token"""
    print("Logging in as admin...")
    
    response = requests.post(
        f"{ADMIN_API_URL}/admin/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return None
    
    token = response.json().get("access_token")
    print(f"✓ Logged in successfully")
    return token

def get_test_sets(token):
    """Get all test sets"""
    response = requests.get(
        f"{ADMIN_API_URL}/admin/benchmarks/test-sets",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get test sets: {response.text}")
        return []
    
    return response.json()

def run_benchmark(token, test_set_id, model_config):
    """Run benchmark for a test set"""
    print(f"\nStarting benchmark for test set: {test_set_id}")
    print(f"Model config: {model_config}")
    
    response = requests.post(
        f"{ADMIN_API_URL}/admin/benchmarks/run",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "test_set_id": test_set_id,
            "llm_config": model_config
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to start benchmark: {response.text}")
        return None
    
    result = response.json()
    session_id = result.get("session_id")
    print(f"✓ Benchmark queued. Session ID: {session_id}")
    
    return session_id

def wait_for_completion(token, session_id, timeout=600):
    """Wait for benchmark session to complete"""
    print(f"\nWaiting for session {session_id} to complete...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(
            f"{ADMIN_API_URL}/admin/benchmarks/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get session status: {response.text}")
            return None
        
        data = response.json()
        session = data.get("session")
        status = session.get("status")
        
        if status == "completed":
            print(f"✓ Benchmark completed!")
            return data
        elif status == "failed":
            print(f"❌ Benchmark failed")
            return data
        else:
            print(f"  Status: {status}... (waiting)")
            time.sleep(5)
    
    print(f"❌ Timeout waiting for benchmark to complete")
    return None

def print_results(session_data):
    """Print benchmark results"""
    session = session_data.get("session")
    results = session_data.get("results", [])
    
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)
    print(f"Session ID: {session.get('id')}")
    print(f"Test Set: {session.get('test_set', {}).get('name', 'Unknown')}")
    print(f"Status: {session.get('status')}")
    print(f"Overall Score: {session.get('overall_score', 0):.4f}")
    print(f"Total Latency: {session.get('total_latency_ms', 0)} ms")
    print(f"Total Tokens: {session.get('total_tokens', 0)}")
    print(f"Created: {session.get('created_at')}")
    print(f"Completed: {session.get('completed_at')}")
    print()
    
    print(f"Individual Test Case Results ({len(results)} cases):")
    print("-" * 80)
    
    for i, result in enumerate(results, 1):
        metrics = result.get("metrics", {})
        
        print(f"\nTest Case {i}:")
        print(f"  Score: {result.get('score', 0):.4f}")
        print(f"  Status: {result.get('status')}")
        
        if isinstance(metrics, dict):
            if "aggregated" in metrics:
                # Dual judge or ensemble
                agg = metrics["aggregated"]
                print(f"  Faithfulness: {agg.get('faithfulness', 0):.4f}")
                print(f"  Relevancy: {agg.get('relevancy', 0):.4f}")
                print(f"  Completeness: {agg.get('completeness', 0):.4f}")
            else:
                # Single judge
                print(f"  Faithfulness: {metrics.get('faithfulness', 0):.4f}")
                print(f"  Relevancy: {metrics.get('relevancy', 0):.4f}")
                print(f"  Completeness: {metrics.get('completeness', 0):.4f}")
        
        print(f"  Latency: {result.get('latency_ms', 0)} ms")
        print(f"  Tokens: {result.get('prompt_tokens', 0)} + {result.get('completion_tokens', 0)}")
        
        if result.get('error_message'):
            print(f"  Error: {result.get('error_message')}")
    
    print("\n" + "=" * 80)

def export_results(token, session_id, format="csv"):
    """Export benchmark results"""
    print(f"\nExporting results to {format.upper()}...")
    
    response = requests.get(
        f"{ADMIN_API_URL}/admin/benchmarks/sessions/{session_id}/export",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": format}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to export: {response.text}")
        return
    
    filename = f"benchmark_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
    
    with open(filename, 'wb') as f:
        f.write(response.content)
    
    print(f"✓ Results exported to: {filename}")

def main():
    parser = argparse.ArgumentParser(description="Run LLM benchmarks via API")
    parser.add_argument("--test-set-id", help="Test set UUID to run")
    parser.add_argument("--test-set-name", help="Test set name to run")
    parser.add_argument("--all", action="store_true", help="Run all active test sets")
    parser.add_argument("--model", default="gpt-4o", help="Parsing model to use (default: gpt-4o)")
    parser.add_argument("--judge", default="gpt-4o", help="Judge model to use (default: gpt-4o)")
    parser.add_argument("--strategy", default="single_judge", 
                       choices=["single_judge", "dual_judge", "ensemble"],
                       help="Evaluation strategy (default: single_judge)")
    parser.add_argument("--export", default="csv", choices=["csv", "json"],
                       help="Export format (default: csv)")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("LLM BENCHMARK RUNNER (API-based)")
    print("=" * 80)
    print()
    
    # Login
    token = login_admin()
    if not token:
        return
    
    # Get test sets
    test_sets = get_test_sets(token)
    
    if not test_sets:
        print("❌ No test sets found. Please create test sets first.")
        return
    
    print(f"\nAvailable test sets ({len(test_sets)}):")
    for ts in test_sets:
        print(f"  - {ts['id']}: {ts['name']} ({ts['flow_type']})")
    print()
    
    # Determine which test sets to run
    test_sets_to_run = []
    
    if args.all:
        test_sets_to_run = [ts for ts in test_sets if ts.get('is_active', True)]
    elif args.test_set_id:
        test_sets_to_run = [ts for ts in test_sets if ts['id'] == args.test_set_id]
    elif args.test_set_name:
        test_sets_to_run = [ts for ts in test_sets if ts['name'] == args.test_set_name]
    else:
        print("❌ Please specify --test-set-id, --test-set-name, or --all")
        return
    
    if not test_sets_to_run:
        print("❌ No matching test sets found")
        return
    
    print(f"Running {len(test_sets_to_run)} test set(s)...")
    print()
    
    # Build model config
    model_config = {
        "parsing_model": args.model,
        "judge_model": args.judge,
        "evaluation_strategy": args.strategy
    }
    
    if args.strategy == "dual_judge":
        model_config["judge_model_primary"] = args.judge
        model_config["judge_model_secondary"] = "claude-3-5-sonnet-20241022"
        model_config["aggregation"] = "average"
    elif args.strategy == "ensemble":
        model_config["judge_models"] = [
            {"model": "gpt-4o", "weight": 0.5},
            {"model": "claude-3-5-sonnet-20241022", "weight": 0.5}
        ]
    
    # Run benchmarks
    for test_set in test_sets_to_run:
        print("\n" + "=" * 80)
        print(f"Running: {test_set['name']}")
        print("=" * 80)
        
        session_id = run_benchmark(token, test_set['id'], model_config)
        
        if not session_id:
            continue
        
        # Wait for completion
        result = wait_for_completion(token, session_id, timeout=600)
        
        if result:
            print_results(result)
            export_results(token, session_id, format=args.export)
    
    print("\n" + "=" * 80)
    print("✓ All benchmarks completed!")
    print("=" * 80)

if __name__ == "__main__":
    main()

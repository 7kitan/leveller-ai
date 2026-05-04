# Benchmark System - Complete Guide

## 📖 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Enable/Disable Benchmark](#enabledisable-benchmark)
4. [Using the Benchmark UI](#using-the-benchmark-ui)
5. [Configuration Options](#configuration-options)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

---

## Overview

The Benchmark System allows you to evaluate LLM performance for CV parsing and gap analysis using **LLM-as-a-Judge** methodology.

### Key Features

- **Quick Test**: Test single CV/Job pair instantly
- **Full Benchmark**: Run systematic tests with test sets
- **Dual Judge**: Use 2 LLMs for unbiased evaluation
- **Ensemble Judge**: Use 3+ LLMs with weighted voting
- **Export Results**: CSV/JSON export for analysis

### Architecture

```
User → Benchmark UI → Admin API → Celery Worker → LLM Flow
                                        ↓
                                   Judge LLMs evaluate output
                                        ↓
                                   Results saved to DB
```

---

## Quick Start

### Prerequisites

✅ Backend services running (admin_service, worker)  
✅ At least 1 CV and 1 Job in database  
✅ API keys configured (OpenAI, Anthropic, Google)

### 5-Minute Test

1. **Access UI**: Navigate to `http://localhost:3000/admin/benchmarks`

2. **Click "⚡ Quick Test" tab**

3. **Select CV and Job** from dropdowns

4. **Configure**:
   ```
   Flow Type: Full CV → Gap Analysis
   Parsing Model: gpt-4o-mini
   Evaluation Strategy: Dual Judge
   Primary Judge: gpt-4o
   Secondary Judge: claude-3-5-sonnet-20241022
   Aggregation: Average
   ```

5. **Click "⚡ Run Quick Test"**

6. **Wait 30-60 seconds** for results

7. **See results**:
   ```
   Quick benchmark completed!
   Score: 85.3%
   Latency: 12450ms
   ```

✅ **Success!** Your benchmark system works!

---

## Enable/Disable Benchmark

### Check Status

```bash
docker logs advisor_admin_service | grep "BENCHMARK"

# Expected if enabled:
# [ADMIN] ✅ Benchmark extension ENABLED - Routes registered

# Expected if disabled:
# [ADMIN] ⚠️ Benchmark extension DISABLED
```

### Enable Benchmark

```bash
docker exec advisor_db psql -U postgres -d career_advisor -c \
  "INSERT INTO system_settings (key, value, description, created_at, updated_at) 
   VALUES ('ENABLE_BENCHMARK', 'true', 'Enable/disable LLM benchmark extension', NOW(), NOW()) 
   ON CONFLICT (key) DO UPDATE SET value = 'true', updated_at = NOW();"

# Restart services
docker restart advisor_admin_service advisor_worker_benchmark
```

### Disable Benchmark

```bash
docker exec advisor_db psql -U postgres -d career_advisor -c \
  "UPDATE system_settings SET value = 'false' WHERE key = 'ENABLE_BENCHMARK';"

# Restart services
docker restart advisor_admin_service advisor_worker_benchmark
```

**⚠️ Important**: Always disable in production to avoid accidental API costs.

---

## Using the Benchmark UI

### Tab 1: ▶️ Run Benchmark (Full Test Set)

**Purpose**: Run systematic tests with multiple test cases

**Steps**:

1. Select test set from dropdown:
   - "CV Parsing Benchmark"
   - "Full Gap Analysis Benchmark"

2. Configure models:
   ```
   Parsing Model: gpt-4o-mini (model to test)
   Evaluation Strategy: Dual Judge
   Primary Judge: gpt-4o
   Secondary Judge: claude-3-5-sonnet-20241022
   Aggregation: Average
   ```

3. (Optional) Expand "▶ Advanced Options":
   ```
   Temperature: 0.0 (deterministic)
   Max Tokens: 2000
   ```

4. Click "▶️ Run Benchmark"

5. Auto-switches to "📊 Results" tab

6. Watch real-time progress:
   ```
   Status: running → completed
   Overall Score: 87.5%
   Total Latency: 45.2s
   Total Tokens: 12,450
   ```

7. Export results: Click "📥 CSV" or "📥 JSON"

### Tab 2: ⚡ Quick Test (Single Test)

**Purpose**: Fast validation without test set setup

**Steps**:

1. Select CV from dropdown
2. Select Job from dropdown
3. Configure models (same as Full Benchmark)
4. Click "⚡ Run Quick Test"
5. See results in alert popup

**Use Cases**:
- Verify system works
- Test specific CV/Job pair
- Quick model comparison

### Tab 3: 📋 Test Sets

**Purpose**: View and manage test sets

**Features**:
- List all test sets
- View test case count
- See test set metadata

### Tab 4: 📊 Results

**Purpose**: View benchmark session results

**Features**:
- List all sessions
- Filter by test set
- View detailed metrics
- Export to CSV/JSON
- Compare sessions

---

## Configuration Options

### Evaluation Strategies

#### 1. Single Judge (Simple)

```json
{
  "evaluation_strategy": "single_judge",
  "judge_model": "gpt-4o"
}
```

**Pros**: Fast, cheap  
**Cons**: Single model bias  
**Use Case**: Quick validation

#### 2. Dual Judge (Recommended)

```json
{
  "evaluation_strategy": "dual_judge",
  "judge_model_primary": "gpt-4o",
  "judge_model_secondary": "claude-3-5-sonnet-20241022",
  "aggregation": "average"
}
```

**Pros**: Reduces bias, more reliable  
**Cons**: 2x cost  
**Use Case**: Production evaluation

**Aggregation Options**:
- `average`: Average of both judges (balanced)
- `max`: Take higher score (optimistic)
- `min`: Take lower score (conservative)
- `weighted`: Custom weights per judge

#### 3. Ensemble Judge (Advanced)

```json
{
  "evaluation_strategy": "ensemble",
  "judge_models": [
    {"model": "gpt-4o", "weight": 0.5},
    {"model": "claude-3-5-sonnet-20241022", "weight": 0.3},
    {"model": "gpt-4o-mini", "weight": 0.2}
  ]
}
```

**Pros**: Most accurate, research-grade  
**Cons**: Nx cost (N judges), slowest  
**Use Case**: Critical evaluation, research

### Model Options

**Parsing Models** (model being tested):
- `gpt-4o-mini` - Fast, cheap ($0.15/1M input tokens)
- `gpt-4o` - Balanced ($5/1M input tokens)
- `claude-3-5-sonnet-20241022` - High quality ($3/1M input tokens)
- `gemini-1.5-flash` - Very fast, cheap ($0.075/1M input tokens)

**Judge Models** (evaluation):
- `gpt-4o` - Recommended primary judge
- `claude-3-5-sonnet-20241022` - Recommended secondary judge
- `gpt-4o-mini` - Budget option for judges

### Flow Types

- **CV Parsing Only**: Test only CV parsing step
- **Full CV → Gap Analysis**: Test complete flow (CV parse + gap analysis)

---

## Troubleshooting

### Issue 1: "No test sets available"

**Cause**: Database not populated with test sets

**Solution**:
```bash
docker exec advisor_db psql -U postgres -d career_advisor \
  -f /app/scripts/migrations/populate_benchmark_test_sets.sql
```

### Issue 2: "No CVs/Jobs available in Quick Test"

**Cause**: No CVs or Jobs in database

**Solution**:
```bash
# Check if CVs exist
docker exec advisor_db psql -U postgres -d career_advisor -c \
  "SELECT COUNT(*) FROM user_cvs WHERE status='completed';"

# If empty, upload CVs via main app first
```

### Issue 3: "Benchmark routes return 404"

**Cause**: Benchmark extension is disabled

**Solution**:
```bash
# Enable benchmark (see Enable/Disable section above)
docker exec advisor_db psql -U postgres -d career_advisor -c \
  "UPDATE system_settings SET value = 'true' WHERE key = 'ENABLE_BENCHMARK';"

docker restart advisor_admin_service advisor_worker_benchmark
```

### Issue 4: "Judge evaluation returns empty result"

**Cause**: API key not configured or quota exceeded

**Solution**:
```bash
# Check API keys in .env
docker exec advisor_admin_service env | grep -E "OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY"

# Verify keys are not empty
```

### Issue 5: "Session stuck in 'running' status"

**Cause**: Worker crashed or task failed

**Solution**:
```bash
# Check worker logs
docker logs advisor_worker_benchmark --tail=100

# Restart worker
docker restart advisor_worker_benchmark

# Manually mark session as failed
docker exec advisor_db psql -U postgres -d career_advisor -c \
  "UPDATE llm_benchmark_sessions SET status = 'failed' WHERE status = 'running';"
```

### Issue 6: "Worker not found"

**Cause**: Benchmark worker not running

**Solution**:
```bash
# Check if worker is running
docker ps | grep benchmark

# If not running, start it
docker-compose up -d advisor_worker_benchmark

# Check logs
docker logs advisor_worker_benchmark -f
```

---

## Best Practices

### 1. Start Small

✅ Use Quick Test first to verify setup  
✅ Run 1-2 test cases before full benchmark  
✅ Test with cheap models (gpt-4o-mini) first

### 2. Use Dual Judge

✅ More reliable than single judge  
✅ Catches model-specific biases  
✅ Recommended: gpt-4o + claude-3-5-sonnet

### 3. Monitor Costs

✅ Each judge call costs API tokens  
✅ Dual judge = 2x cost  
✅ Ensemble = Nx cost (N judges)  
✅ Use gpt-4o-mini for judges when possible

**Cost Estimation**:
```
Single test case:
- Parsing: ~2000 tokens × $0.15/1M = $0.0003
- Judge 1: ~1000 tokens × $5/1M = $0.005
- Judge 2: ~1000 tokens × $3/1M = $0.003
Total: ~$0.008 per test case

Full benchmark (10 test cases):
- Total: ~$0.08
```

### 4. Export Results

✅ Always export after completion  
✅ CSV for spreadsheet analysis  
✅ JSON for programmatic access  
✅ Keep historical data for comparison

### 5. Disable in Production

✅ Set `ENABLE_BENCHMARK=false` in production  
✅ Only enable in dev/staging  
✅ Avoid accidental API costs

### 6. Regular Benchmarking

✅ Run benchmark after prompt changes  
✅ Track performance over time  
✅ Document findings and insights  
✅ Compare before/after scores

---

## Common Use Cases

### Use Case 1: Compare Two Models

**Goal**: Which parsing model is better: gpt-4o-mini or gpt-4o?

**Steps**:

1. Run benchmark with gpt-4o-mini:
   ```
   Test Set: CV Parsing Benchmark
   Parsing Model: gpt-4o-mini
   → Run → Note Session ID
   ```

2. Run benchmark with gpt-4o:
   ```
   Test Set: CV Parsing Benchmark (same)
   Parsing Model: gpt-4o
   → Run → Note Session ID
   ```

3. Compare results in "📊 Results" tab:
   ```
   Session 1 (gpt-4o-mini): Score 85.3%, Latency 12s, Tokens 8,500
   Session 2 (gpt-4o):      Score 92.1%, Latency 18s, Tokens 12,000
   ```

4. Export both for detailed comparison

**Conclusion**: gpt-4o has +6.8% better score but +50% higher latency and +41% more tokens

### Use Case 2: Validate Prompt Changes

**Goal**: Did my prompt change improve results?

**Steps**:

1. Run baseline benchmark (before prompt change):
   ```
   Test Set: Gap Analysis Benchmark
   → Run → Export CSV as "baseline.csv"
   ```

2. Update prompt in Admin → Prompts

3. Run benchmark again (after prompt change):
   ```
   Test Set: Gap Analysis Benchmark (same)
   → Run → Export CSV as "after_change.csv"
   ```

4. Compare:
   ```
   Baseline:     Score 78.5%
   After Change: Score 82.3%
   Improvement:  +3.8%
   ```

**Conclusion**: Prompt change improved performance by 3.8%

### Use Case 3: Cost Optimization

**Goal**: Find cheapest model that meets quality threshold (>80% score)

**Steps**:

1. Test gpt-4o-mini (cheapest):
   ```
   → Score: 85.3%, Tokens: 8,500
   → Cost: $0.085
   ```

2. Test gpt-4o (mid-tier):
   ```
   → Score: 92.1%, Tokens: 12,000
   → Cost: $0.60
   ```

3. Test claude-3-5-sonnet (premium):
   ```
   → Score: 93.5%, Tokens: 11,500
   → Cost: $0.345
   ```

**Conclusion**: gpt-4o-mini meets threshold (>80%) at 7x lower cost than gpt-4o

---

## Metrics Explained

### Overall Score (0.0 - 1.0)

Average score across all test cases. Higher is better.

| Score Range | Interpretation | Action |
|-------------|----------------|--------|
| 0.90 - 1.00 | Excellent | Production ready |
| 0.80 - 0.89 | Good | Minor improvements needed |
| 0.70 - 0.79 | Fair | Significant improvements needed |
| < 0.70 | Poor | Major prompt revision required |

### Component Metrics

- **Faithfulness**: How accurate is the output compared to ground truth? (0.0-1.0)
- **Relevancy**: How relevant is the output to the input? (0.0-1.0)
- **Completeness**: How complete is the output? (0.0-1.0)

### Performance Metrics

- **Latency (ms)**: Time taken to process
- **Tokens**: Total tokens used (prompt + completion)
- **Cost (USD)**: Estimated API cost

---

## API Reference

### Endpoints

```
GET  /admin/benchmarks/test-sets              - List test sets
POST /admin/benchmarks/run                    - Run full benchmark
POST /admin/benchmarks/quick-run              - Run quick test
GET  /admin/benchmarks/sessions               - List sessions
GET  /admin/benchmarks/sessions/{id}          - Get session details
GET  /admin/benchmarks/sessions/{id}/export   - Export results (CSV/JSON)
```

### Example: Run Benchmark via API

```bash
curl -X POST http://localhost:8001/admin/benchmarks/run \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_set_id": "00000000-0000-0000-0001-000000000001",
    "llm_config": {
      "parsing_model": "gpt-4o-mini",
      "judge_model_primary": "gpt-4o",
      "judge_model_secondary": "claude-3-5-sonnet-20241022",
      "evaluation_strategy": "dual_judge",
      "aggregation": "average"
    }
  }'
```

---

## Database Schema

### Tables

```sql
-- Test sets
llm_test_sets (id, name, description, flow_type, created_at)

-- Test cases
llm_test_cases (id, test_set_id, input_data, expected_output, metadata)

-- Benchmark sessions
llm_benchmark_sessions (id, test_set_id, model_config, status, overall_score, created_at)

-- Results
llm_benchmark_results (id, session_id, test_case_id, actual_output, score, metrics, latency_ms)
```

---

## Summary

You now know how to:

✅ Enable/disable benchmark system  
✅ Run Quick Test for fast validation  
✅ Run Full Benchmark with test sets  
✅ Use Dual Judge for reliable evaluation  
✅ Try Ensemble for advanced evaluation  
✅ Compare models and prompts  
✅ Optimize for cost vs quality  
✅ Export and analyze results  
✅ Troubleshoot common issues

**Happy Benchmarking! 🎉**

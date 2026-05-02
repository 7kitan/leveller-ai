"""
Analyze the actual prompt length from llm_utils.py
"""
import sys
import re
sys.path.insert(0, '/app')

try:
    import tiktoken
except ImportError:
    print("Installing tiktoken...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tiktoken", "-q"])
    import tiktoken

# Read the actual prompt from llm_utils.py
with open('shared/llm_utils.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract the prompt using regex
prompt_match = re.search(r'prompt = f"""(.*?)"""', content, re.DOTALL)
if not prompt_match:
    print("ERROR: Could not find prompt in llm_utils.py")
    sys.exit(1)

prompt_template = prompt_match.group(1)

# Extract system prompt
system_match = re.search(r'system_prompt = "(.*?)"', content)
system_prompt = system_match.group(1) if system_match else ""

# Count tokens
encoding = tiktoken.get_encoding('cl100k_base')

# Static prompt (without requirements)
static_prompt = prompt_template.replace("{requirements_text}", "")
static_tokens = len(encoding.encode(static_prompt))
system_tokens = len(encoding.encode(system_prompt))

print("=" * 80)
print("OPTIMIZED PROMPT ANALYSIS (Tech-to-Tech Focus)")
print("=" * 80)

print(f"\n1. PROMPT STRUCTURE:")
print(f"   Characters: {len(static_prompt):,}")
print(f"   Lines: {len(static_prompt.splitlines())}")
print(f"   Static tokens: {static_tokens}")
print(f"   System tokens: {system_tokens}")
print(f"   Total static: {static_tokens + system_tokens}")

# Sample requirements
sample_req = "Python, Django, PostgreSQL, Docker, AWS, React, Redis, Kubernetes"
req_tokens = len(encoding.encode(sample_req))
total = static_tokens + system_tokens + req_tokens

print(f"\n2. WITH TYPICAL JOB REQUIREMENTS:")
print(f"   Requirements: '{sample_req}'")
print(f"   Req tokens: {req_tokens}")
print(f"   Total tokens: {total}")

# Cost
gpt35_input = total / 1000 * 0.0015
gpt35_output = 200 / 1000 * 0.002
gpt35_total = gpt35_input + gpt35_output

print(f"\n3. COST PER EXTRACTION (GPT-3.5):")
print(f"   Input:  ${gpt35_input:.4f}")
print(f"   Output: ${gpt35_output:.4f} (est. 200 tokens)")
print(f"   Total:  ${gpt35_total:.4f}")

print(f"\n4. COST FOR 1000 JOBS:")
print(f"   GPT-3.5: ${gpt35_total * 1000:.2f}")
print(f"   GPT-4:   ${((total / 1000 * 0.03) + (200 / 1000 * 0.06)) * 1000:.2f}")

# Compare with old prompt (1399 tokens)
old_static = 1399
savings = old_static - static_tokens
savings_pct = (savings / old_static) * 100

print(f"\n5. COMPARISON WITH OLD PROMPT:")
print(f"   Old prompt: {old_static} tokens")
print(f"   New prompt: {static_tokens} tokens")
print(f"   Savings:    {savings} tokens ({savings_pct:.1f}%)")
print(f"   Cost saved per 1000 jobs: ${(savings / 1000 * 0.0015) * 1000:.2f}")

print(f"\n6. CATEGORIES:")
# Count categories in prompt
categories = re.findall(r'"([^"]+)" \(', static_prompt)
print(f"   Total categories: {len(set(categories))}")
print(f"   Categories: {', '.join(sorted(set(categories)))}")

print(f"\n7. VERDICT:")
if static_tokens < 800:
    print(f"   EXCELLENT - Prompt is well optimized ({static_tokens} tokens)")
elif static_tokens < 1000:
    print(f"   GOOD - Prompt is reasonably sized ({static_tokens} tokens)")
else:
    print(f"   NEEDS WORK - Prompt is still long ({static_tokens} tokens)")

print("\n" + "=" * 80)

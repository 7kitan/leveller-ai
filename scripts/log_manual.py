#!/usr/bin/env python3
"""
Manual AI usage logger — for ChatGPT, Gemini Web, and other tools without hooks.
"""
import json
import os
import sys
import argparse
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

VN_TZ = timezone(timedelta(hours=7))

def git(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""

def main():
    parser = argparse.ArgumentParser(description="Manual AI usage logger")
    parser.add_argument("--tool", help="AI tool name (chatgpt, gemini-web, perplexity, etc.)")
    parser.add_argument("--prompt", help="The prompt you used")
    parser.add_argument("--model", help="AI model used")
    args = parser.parse_args()

    tool = args.tool
    prompt = args.prompt
    model = args.model

    if not tool or not prompt:
        print("\n📝 [ai-log] Manual Log Entry")
        if not tool:
            tool = input("   • AI Tool (e.g. chatgpt): ").strip()
        if not prompt:
            prompt = input("   • Prompt: ").strip()
        if not model:
            model = input("   • Model (optional): ").strip()

    if not tool or not prompt:
        print("❌ Error: Tool and Prompt are required.")
        sys.exit(1)

    student = git("git config user.email") or os.environ.get("USERNAME", "unknown")
    repo = ""
    remote = git("git remote get-url origin")
    if remote:
        repo = remote.split("/")[-1].replace(".git", "")

    entry = {
        "ts": datetime.now(VN_TZ).isoformat(),
        "tool": tool.lower(),
        "event": "ManualEntry",
        "model": model,
        "repo": repo if repo else Path.cwd().name,
        "branch": git("git rev-parse --abbrev-ref HEAD"),
        "commit": git("git rev-parse --short HEAD"),
        "student": student,
        "prompt": prompt[:1000],
    }

    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "session.jsonl"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\n✅ [ai-log] Logged: [{tool}] {prompt[:50]}...")
    print(f"📁 Saved to: {log_file}")

if __name__ == "__main__":
    main()

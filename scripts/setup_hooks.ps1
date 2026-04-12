# =============================================================
# AI Log Hook — Git pre-push hook installer (Windows/PowerShell)
# Run once: powershell scripts/setup_hooks.ps1
# =============================================================

$HookFile = ".git\hooks\pre-push"

$HookContent = @"
#!/bin/bash
# =============================================================
# Pre-push hook: Enforce AI logging + scan Antigravity brain
# Installed by: scripts/setup_hooks.ps1
# =============================================================

LOG_FILE=".ai-log/session.jsonl"

echo ""
echo "🔍 [ai-log] Checking AI usage logs before push..."
echo ""

# --- Detect Python 3 ---
PY=""
for candidate in python3 python py; do
    if `$candidate --version &> /dev/null 2>&1; then
        PY_VER=`$($candidate -c "import sys; print(sys.version_info[0])" 2>/dev/null)
        if [ "`$PY_VER" = "3" ]; then
            PY="`$candidate"
            break
        fi
    fi
done

if [ -z "`$PY" ]; then
    echo "❌ [ai-log] Python 3 not found. Install Python 3 and add to PATH."
    exit 1
fi

# --- Auto-scan Antigravity sessions ---
# This part scans the internal Antigravity brain directory for conversations
# related to this repository's workspace.
if [ -f "scripts/log_antigravity.py" ]; then
    echo "🔍 [ai-log] Scanning Antigravity IDE sessions..."
    `$PY scripts/log_antigravity.py --auto 2>&1 || echo "[ai-log] ⚠️  Antigravity scan skipped."
    echo ""
fi

# --- Check 1: Log file exists and is not empty ---
if [ ! -f "`$LOG_FILE" ] || [ ! -s "`$LOG_FILE" ]; then
    echo "❌ [ai-log] BLOCKED: No AI logs found!"
    echo ""
    echo "   Bạn chưa ghi log sử dụng AI nào cho phiên làm việc này."
    echo "   Mọi thành viên đều PHẢI ghi log AI trước khi push."
    echo ""
    echo "   Cách ghi log:"
    echo "   ─────────────────────────────────────────────────"
    echo "   📌 Tool có hook tự động (Claude Code, Cursor, Codex, Copilot):"
    echo "       → (Tự động ghi khi bạn chat)"
    echo ""
    echo "   📌 Antigravity IDE:"
    echo "       → (Tự động quét khi push, hoặc: `$PY scripts/log_antigravity.py --auto)"
    echo ""
    echo "   📌 ChatGPT, Gemini Web, hoặc tool khác:"
    echo "       → `$PY scripts/log_manual.py"
    echo ""
    echo "   Sau khi ghi log, hãy thực hiện push lại."
    echo ""
    exit 1
fi

# --- Check 2: Count entries ---
ENTRY_COUNT=$(wc -l < "`$LOG_FILE" | tr -d ' ')
echo "✅ [ai-log] Found `$ENTRY_COUNT log entries."

# --- Check 3: Show summary ---
echo ""
echo "📋 AI Summary:"
`$PY -c "
import json
from collections import Counter
tools = Counter()
try:
    with open('.ai-log/session.jsonl', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                e = json.loads(line)
                tools[e.get('tool','unknown')] += 1
            except: pass
    for t, c in tools.most_common():
        print(f'   - {t}: {c} entries')
except: pass
" 2>/dev/null

# --- Submit to server ---
echo ""
echo "📤 [ai-log] Submitting logs to server..."
`$PY scripts/submit_log.py 2>&1 || echo "[ai-log] ⚠️ Submit failed — logs kept locally."

echo ""
echo "✅ [ai-log] Push allowed. Happy coding! 🚀"
exit 0
"@

# Create hooks directory if it doesn't exist
$HooksDir = Split-Path $HookFile
if (-not (Test-Path $HooksDir)) {
    New-Item -ItemType Directory -Path $HooksDir | Out-Null
}

[IO.File]::WriteAllText($HookFile, $HookContent)
Write-Host "[ai-log] ✅ Git pre-push hook installed."

# Create .ai-log directory if not exists
if (-not (Test-Path ".ai-log")) {
    New-Item -ItemType Directory -Path ".ai-log" | Out-Null
}
if (-not (Test-Path ".ai-log\.gitkeep")) {
    New-Item -ItemType File -Path ".ai-log\.gitkeep" -Force | Out-Null
}

Write-Host "[ai-log] ✅ Setup complete."
Write-Host "[ai-log] Antigravity sessions will be scanned automatically on push."

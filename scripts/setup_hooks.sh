#!/bin/bash
# =============================================================
# AI Log Hook — Git pre-push hook installer
# Chạy 1 lần trên mỗi máy: bash scripts/setup_hooks.sh
# =============================================================
set -e

HOOK_FILE=".git/hooks/pre-push"

# Check if inside a git repo
if [ ! -d ".git" ]; then
    echo "❌ [ai-log] Not a git repository. Run this from the root of your project."
    exit 1
fi

cat > "$HOOK_FILE" << 'HOOKEOF'
#!/bin/bash
# =============================================================
# Pre-push hook: Enforce AI logging + scan Antigravity brain
# Installed by: bash scripts/setup_hooks.sh
# =============================================================

LOG_FILE=".ai-log/session.jsonl"

echo ""
echo "🔍 [ai-log] Checking AI usage logs before push..."
echo ""

# --- Detect Python 3 ---
PY=""
for candidate in python3 python py; do
    if $candidate --version &> /dev/null 2>&1; then
        PY_VER=$($candidate -c "import sys; print(sys.version_info[0])" 2>/dev/null)
        if [ "$PY_VER" = "3" ]; then
            PY="$candidate"
            break
        fi
    fi
done
if [ -z "$PY" ]; then
    echo "❌ [ai-log] Python 3 not found. Install Python 3 and add to PATH."
    exit 1
fi

# --- Auto-scan Antigravity sessions ---
if [ -f "scripts/log_antigravity.py" ]; then
    echo "🔍 [ai-log] Scanning Antigravity IDE sessions..."
    $PY scripts/log_antigravity.py --auto 2>&1 || echo "[ai-log] ⚠️  Antigravity scan skipped."
    echo ""
fi

# --- Check 1: Log file exists and is not empty ---
if [ ! -f "$LOG_FILE" ] || [ ! -s "$LOG_FILE" ]; then
    echo "❌ [ai-log] BLOCKED: No AI logs found!"
    echo ""
    echo "   Bạn chưa ghi log sử dụng AI nào cho phiên làm việc này."
    echo "   Mọi thành viên đều PHẢI ghi log AI trước khi push."
    echo ""
    echo "   Cách ghi log:"
    echo "   ─────────────────────────────────────────────────"
    echo "   📌 Tool có hook tự động (Claude Code, Cursor, Codex, Gemini CLI, Copilot):"
    echo "       → (Tự động ghi khi bạn chat)"
    echo ""
    echo "   📌 Antigravity IDE:"
    echo "       → (Tự động quét khi push, hoặc: $PY scripts/log_antigravity.py --auto)"
    echo ""
    echo "   📌 ChatGPT, Gemini Web, hoặc tool khác:"
    echo "       → $PY scripts/log_manual.py"
    echo ""
    echo "   Sau khi ghi log, hãy thực hiện push lại."
    echo ""
    exit 1
fi

# --- Check 2: Count entries ---
ENTRY_COUNT=$(wc -l < "$LOG_FILE" | tr -d ' ')
echo "✅ [ai-log] Found $ENTRY_COUNT log entries."

# --- Check 3: Show summary ---
echo ""
echo "📋 AI Summary:"
$PY -c "
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
$PY scripts/submit_log.py 2>&1 || echo "[ai-log] ⚠️  Submit failed — logs kept locally."

echo ""
echo "✅ [ai-log] Push allowed. Happy coding! 🚀"
exit 0
HOOKEOF

chmod +x "$HOOK_FILE"
echo "[ai-log] ✅ Git pre-push hook installed."

# Create .ai-log directory
mkdir -p .ai-log
touch .ai-log/.gitkeep

echo "[ai-log] ✅ Setup complete."

$HookFile = ".git\hooks\pre-push"

$HookContent = @"
#!/bin/bash
# Submit AI logs to grading server before push
python scripts/submit_log.py
exit 0
"@

# Create hooks directory if it doesn't exist
$HooksDir = Split-Path $HookFile
if (-not (Test-Path $HooksDir)) {
    New-Item -ItemType Directory -Path $HooksDir | Out-Null
}

[IO.File]::WriteAllText($HookFile, $HookContent)
Write-Host "[ai-log] Git pre-push hook installed."

# Create .ai-log directory if not exists
if (-not (Test-Path ".ai-log")) {
    New-Item -ItemType Directory -Path ".ai-log" | Out-Null
}
New-Item -ItemType File -Path ".ai-log\.gitkeep" -Force | Out-Null

Write-Host "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."

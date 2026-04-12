import os
from pathlib import Path

files = [
    ".ai-log/.last_synced_commit",
    ".ai-log/session.jsonl",
    ".ai-log/.antigravity_history"
]

for f_path in files:
    p = Path(f_path)
    if p.exists():
        print(f"Fixing {f_path}...")
        try:
            content = p.read_bytes()
            # Remove UTF-16 BOM and Null bytes
            clean_content = content.replace(b'\xff\xfe', b'').replace(b'\x00', b'').strip()
            p.write_bytes(clean_content)
            print(f"Successfully cleaned {f_path}")
        except Exception as e:
            print(f"Failed to fix {f_path}: {e}")
    else:
        print(f"File {f_path} not found, skipping.")

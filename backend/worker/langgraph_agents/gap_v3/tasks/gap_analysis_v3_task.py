"""
DEPRECATED: gap_analysis_v3_task.py
════════════════════════════════════════════════════════════════════════════════
ĐÂY LÀ DEAD CODE.

Thay vì dùng task này, hãy dùng:
  worker.tasks.analysis_tasks.run_gap_analysis

Task này bị trùng với analysis_tasks.py:
  - analysis_tasks.py đã gọi gap_v3 orchestrator khi USE_LLM_GAP_AGENT_V3=true
  - gap_analysis_v3_task.py lặp lại cùng logic

Để deprecate hoàn toàn:
  1. Xóa file này
  2. Xóa khỏi celery_app.include trong celery_app.py
════════════════════════════════════════════════════════════════════════════════
"""
# This task is DEPRECATED. Use worker.tasks.analysis_tasks.run_gap_analysis instead.
# Kept for backwards compatibility only — will be removed in v4.0

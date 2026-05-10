# Quy Chuẩn Dành Cho AI Agent

Tài liệu này quy định các quy tắc bắt buộc khi sử dụng các công cụ lập trình AI (AI Coding Agents) trong dự án này.

---

## 1. Tự Động Ghi Nhật Ký Prompt (AI Prompt Logging)

Mọi prompt và phản hồi từ AI sẽ được **tự động ghi lại** thông qua các hooks khi bạn sử dụng các công cụ hỗ trợ. Bạn **không cần** phải cập nhật file `PROMPT_LOG.md` một cách thủ công.

Các công cụ được hỗ trợ và file cấu hình tương ứng:
| Công cụ | File cấu hình |
|---|---|
| Claude Code | `.claude/settings.json` |
| Cursor | `.cursor/hooks.json` |
| OpenAI Codex | `.codex/hooks.json` |
| Gemini CLI | `.gemini/settings.json` |
| GitHub Copilot | `.github/hooks/hooks.json` |
| Antigravity | `.antigravity/settings.json` |

Logs được lưu tại `.ai-log/session.jsonl` và sẽ được tự động đẩy lên khi thực hiện `git push`.

---

## 2. Thiết Lập Ban Đầu (One-time Setup)

Trước khi bắt đầu, hãy đảm bảo bạn đã cài đặt git hooks:
```bash
bash scripts/setup_hooks.sh
```
Các biến `AI_LOG_SERVER` và `AI_LOG_API_KEY` đã được thiết lập sẵn trong file `.env.example`.

---

## 3. Quy Định Về Pull Request (PR)

- **Tiêu đề**: Mô tả ngắn gọn thay đổi.
- **Mô tả**: Phải bao gồm:
  - Tóm tắt các thay đổi.
  - Danh sách các file đã chỉnh sửa.

Định dạng mô tả PR:
```markdown
## Summary
<mô tả các thay đổi>

## Changes
- <danh sách các file thay đổi>
```

---

## 4. Quy Tắc Đối Với AI Agents

Nếu bạn là một AI coding agent (Claude Code, Cursor, Copilot, Gemini...):

- **BẮT BUỘC** phải đảm bảo lệnh `bash scripts/setup_hooks.sh` đã được chạy trước khi tạo PR.
- **BẮT BUỘC** phải viết mô tả PR rõ ràng với tóm tắt và danh sách file.
- **KHÔNG ĐƯỢC** commit các file trong thư mục `.ai-log/*.jsonl` (chúng đã được gitignore).
- Việc ghi log là tự động — đừng yêu cầu người dùng ghi log thủ công.

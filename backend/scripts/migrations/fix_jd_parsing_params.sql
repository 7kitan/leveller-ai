-- Fix JD Parsing Prompt - Remove current_date parameter
UPDATE prompt_templates 
SET 
  prompt_text = 'Bạn là chuyên gia phân tích Job Description.

Phân tích Job Description sau và trích xuất thông tin theo định dạng JSON:

{{jd_text}}

Trả về JSON với các trường:
- job_title: Tên vị trí tuyển dụng
- company: Tên công ty
- location: Địa điểm làm việc
- employment_type: Loại hình (Full-time, Part-time, Contract, etc.)
- salary: {min, max, currency, period} hoặc null nếu không có
- experience_required: Số năm kinh nghiệm yêu cầu
- education_required: Trình độ học vấn yêu cầu
- job_description: Mô tả công việc
- requirements: [Danh sách yêu cầu ứng viên]
- responsibilities: [Danh sách trách nhiệm công việc]
- benefits: [Danh sách quyền lợi]
- skills_required: [{skill_name, level, is_required}]
- application_deadline: Hạn nộp hồ sơ (YYYY-MM-DD) hoặc null

Chỉ trả về JSON hợp lệ, không thêm text khác.',
  parameters = '["jd_text"]'
WHERE key = 'jd_parsing';

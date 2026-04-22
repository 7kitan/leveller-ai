export const translations = {
  vi: {
    // Common
    loading: "Đang tải...",
    error: "Lỗi",
    cancel: "Hủy",
    save: "Lưu",
    delete: "Xóa",
    back: "Quay lại",
    start_analysis: "BẮT ĐẦU PHÂN TÍCH GAP",
    
    // Navbar/Sidebar
    nav_jobs: "Việc làm",
    nav_cv: "Hồ sơ CV",
    nav_analysis: "Phân tích Gap",
    nav_recommend: "Đề xuất",
    nav_settings: "Cài đặt",
    logout: "Đăng xuất",

    // Analysis Page
    analysis_title: "Phân tích khoảng cách kỹ năng",
    select_job: "Chọn vị trí công việc",
    paste_jd: "Dán mô tả công việc (JD)",
    select_cv: "Chọn CV của bạn",
    processing: "Đang xử lý...",
    re_analyze: "Phân tích lại",
    select_other: "Chọn vị trí khác",
    
    // Recommend Page
    match_score: "Điểm tương thích",
    current_match: "Độ phù hợp hiện tại",
    strengths: "Điểm mạnh nổi bật",
    weaknesses: "Điểm cần cải thiện",
    skill_gaps: "Khoảng cách kỹ năng",
    suggested_courses: "Khóa học đề xuất",
    career_roadmap: "Lộ trình sự nghiệp",
    severity_high: "Cao",
    severity_medium: "Trung bình",
    severity_low: "Thấp",
  },
  en: {
    // Common
    loading: "Loading...",
    error: "Error",
    cancel: "Cancel",
    save: "Save",
    delete: "Delete",
    back: "Back",
    start_analysis: "START GAP ANALYSIS",

    // Navbar/Sidebar
    nav_jobs: "Jobs",
    nav_cv: "CV Profile",
    nav_analysis: "Gap Analysis",
    nav_recommend: "Recommendations",
    nav_settings: "Settings",
    logout: "Logout",

    // Analysis Page
    analysis_title: "Skill Gap Analysis",
    select_job: "Select Job Position",
    paste_jd: "Paste Job Description (JD)",
    select_cv: "Select Your CV",
    processing: "Processing...",
    re_analyze: "Re-analyze",
    select_other: "Select another position",

    // Recommend Page
    match_score: "Match Score",
    current_match: "Current Match",
    strengths: "Key Strengths",
    weaknesses: "Points for Improvement",
    skill_gaps: "Skill Gaps",
    suggested_courses: "Suggested Courses",
    career_roadmap: "Career Roadmap",
    severity_high: "High",
    severity_medium: "Medium",
    severity_low: "Low",
  }
};

export type TranslationKey = keyof typeof translations.vi;

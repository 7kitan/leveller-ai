"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Clock,
  ArrowRight,
  ShieldCheck,
  Zap,
  Sparkles,
  Award,
  ChevronRight,
  Save,
  Plus,
  Trash2,
  Briefcase,
  GraduationCap,
  BadgeCheck,
  ArrowLeft,
  BarChart3,
  X,
  Check,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./user-cv.module.css";
import { motion, AnimatePresence } from "framer-motion";

interface CVHistory {
  id: string;
  status: "processing" | "completed" | "failed";
  created_at: string;
  file_name: string;
  full_name?: string;
  error_message?: string;
}

interface ParsedCV {
  id: string;
  skills: { name: string; category: string; experience_years: number; level: string }[];
  summary: string;
  full_name?: string;
  experience_years_total?: number;
  seniority?: string;
  is_ocr?: boolean;
  is_verified?: boolean;
  ocr_confidence?: number;
  work_history?: {
    position: string;
    company: string;
    duration_years?: number;
    description?: string;
  }[];
  education?: {
    degree: string;
    institution: string;
    year?: number;
  }[];
  certifications?: string[];
}

/* -- Custom Select Component --------------------------------------------- */
interface CustomDropdownProps {
  value: string;
  options: string[];
  onChange: (val: string) => void;
  className?: string;
  style?: React.CSSProperties;
}

const CustomDropdown: React.FC<CustomDropdownProps> = ({
  value,
  options,
  onChange,
  className,
  style,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className={cn(styles.customDropdownContainer, isOpen && styles.customDropdownContainerActive)} ref={dropdownRef}>
      <button
        type="button"
        className={cn(styles.customDropdownButton, className, isOpen && styles.customDropdownButtonActive)}
        onClick={() => setIsOpen(!isOpen)}
        style={style}
      >
        <span>{value}</span>
        <ChevronDown size={14} className={cn(styles.dropdownChevron, isOpen && styles.dropdownChevronRotate)} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.98 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className={styles.customDropdownMenu}
          >
            {options.map((opt) => (
              <button
                key={opt}
                type="button"
                className={cn(
                  styles.customDropdownOption,
                  value === opt && styles.customDropdownOptionActive
                )}
                onClick={() => {
                  onChange(opt);
                  setIsOpen(false);
                }}
              >
                {opt}
                {value === opt && <Check size={12} className={styles.optionCheck} />}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const UserCVPage = () => {
  const { token } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [history, setHistory] = useState<CVHistory[]>([]);
  const [status, setStatus] = useState<"idle" | "uploading" | "processing" | "viewing">("idle");
  const [parsedData, setParsedData] = useState<ParsedCV | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);

  // --- Change Tracking ---
  const [isDirty, setIsDirty] = useState(false);
  const [showRerunModal, setShowRerunModal] = useState(false);

  // --- Gap Analysis Integration ---
  const [suggestedSkills, setSuggestedSkills] = useState<string[]>([]);
  const [analysisContext, setAnalysisContext] = useState<any>(null);
  const router = useRouter();

  const fetchHistory = async () => {
    try {
      const resp = await axios.get("/api/cv/list", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setHistory(resp.data);
    } catch (err) {
      console.error("Fetch history error:", err);
    }
  };

  useEffect(() => {
    if (token) {
      fetchHistory();
      
      // Load context (including suggested skills) from Gap Analysis
      const storedContext = sessionStorage.getItem("analysis_context");
      const targetCvId = sessionStorage.getItem("target_cv_id");

      if (storedContext) {
        const context = JSON.parse(storedContext);
        setAnalysisContext(context);
        if (context.suggested_skills) {
          setSuggestedSkills(context.suggested_skills);
        }
      }
      
      // Auto-load targeted CV for editing
      if (targetCvId) {
        handleLoadSpecificCV(targetCvId);
        sessionStorage.removeItem("target_cv_id");
      }
    }
  }, [token]);

  const handleAddSuggestedSkill = (skillName: string) => {
    if (!parsedData) return;
    const newSkill = {
      name: skillName,
      category: "Technology", // Default
      experience_years: 1,
      level: "Junior",
    };
    setParsedData({
      ...parsedData,
      skills: [...(parsedData.skills || []), newSkill],
    });
    // Remove from local state
    const remaining = suggestedSkills.filter(s => s !== skillName);
    setSuggestedSkills(remaining);
    setIsDirty(true);
  };

  const handleRerunAnalysis = () => {
    if (!analysisContext) return;

    // Clear the context to avoid showing the banner again later
    sessionStorage.removeItem("suggested_skills");
    sessionStorage.removeItem("analysis_context");
    
    // Redirect back to analysis engine
    router.push(`/user/analysis?job_id=${analysisContext.jd_id}&job_title=${encodeURIComponent(analysisContext.jd_title)}&auto_run=true`);
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus("uploading");
    setError(null);
    setSelectedHistoryId(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await axios.post("/api/cv/upload", formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data",
        },
      });

      const { parser_id, cv_id, status: uploadStatus, result: inlineResult, is_duplicate } =
        resp.data;

      // Duplicate CV đã completed → hiển thị luôn
      if (is_duplicate && uploadStatus === "completed" && inlineResult) {
        setParsedData(inlineResult);
        setStatus("viewing");
        fetchHistory();
        return;
      }

      if (uploadStatus === "completed") {
        try {
          const detailResp = await axios.get(`/api/cv/${cv_id}`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          setParsedData(detailResp.data);
          setStatus("viewing");
          fetchHistory();
        } catch (err) {
          console.error("Lỗi khi lấy chi tiết CV cũ:", err);
          setError("Không thể lấy dữ liệu CV đã tồn tại.");
          setStatus("idle");
        }
      } else if (parser_id) {
        pollStatus(parser_id, cv_id);
      } else {
        console.error("Backend did not return parser_id or completed status", resp.data);
        setError("Không nhận được ID xử lý từ hệ thống.");
        setStatus("idle");
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Lỗi khi tải file. Vui lòng thử lại.");
      setStatus("idle");
    }
  };

  const pollStatus = async (parserId: string, cvId: string) => {
    setStatus("processing");
    const interval = setInterval(async () => {
      try {
        const resp = await axios.get(`/api/cv/status/${parserId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const { status: taskStatus, result } = resp.data;

        if (taskStatus === "completed") {
          clearInterval(interval);
          if (result) {
            setParsedData(result);
          } else {
            const detailResp = await axios.get(`/api/cv/${cvId}`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            setParsedData(detailResp.data);
          }
          setStatus("viewing");
          fetchHistory();
        } else if (taskStatus === "failed") {
          clearInterval(interval);
          setError("AI gặp sự cố khi bóc tách hồ sơ này.");
          setStatus("idle");
        }
      } catch {
        clearInterval(interval);
        setStatus("idle");
      }
    }, 3000);
  };
  
  const handleLoadSpecificCV = async (cvId: string) => {
    setStatus("processing");
    setError(null);
    setSelectedHistoryId(cvId);
    try {
      const resp = await axios.get(`/api/cv/${cvId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setParsedData(resp.data);
      setStatus("viewing");
    } catch (err) {
      console.error("Auto-load CV detail error:", err);
      setError("Không thể tự động tải chi tiết CV.");
      setStatus("idle");
      setSelectedHistoryId(null);
    }
  };

  // ── Load CV from history click ────────────────────────────────────────────
  const handleHistoryClick = async (item: CVHistory) => {
    if (item.status !== "completed") return;
    setStatus("processing");
    setError(null);
    setSelectedHistoryId(item.id);
    try {
      const resp = await axios.get(`/api/cv/${item.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setParsedData(resp.data);
      setStatus("viewing");
    } catch (err) {
      console.error("Load CV detail error:", err);
      setError("Không thể tải chi tiết CV.");
      setStatus("idle");
      setSelectedHistoryId(null);
    }
  };

  const handleBack = () => {
    setStatus("idle");
    setParsedData(null);
    setSelectedHistoryId(null);
    setError(null);
  };

  const handleUpdateBasic = (field: string, value: any) => {
    if (!parsedData) return;
    setParsedData({ ...parsedData, [field]: value });
    setIsDirty(true);
  };

  const handleUpdateWork = (idx: number, field: string, value: any) => {
    if (!parsedData) return;
    const next = [...(parsedData.work_history || [])];
    if (next[idx]) {
      next[idx] = { ...next[idx], [field]: value };
      setParsedData({ ...parsedData, work_history: next });
      setIsDirty(true);
    }
  };

  const handleUpdateEdu = (idx: number, field: string, value: any) => {
    if (!parsedData) return;
    const next = [...(parsedData.education || [])];
    if (next[idx]) {
      next[idx] = { ...next[idx], [field]: value };
      setParsedData({ ...parsedData, education: next });
      setIsDirty(true);
    }
  };

  const handleUpdateCert = (idx: number, value: string) => {
    if (!parsedData) return;
    const next = [...(parsedData.certifications || [])];
    next[idx] = value;
    setParsedData({ ...parsedData, certifications: next });
    setIsDirty(true);
  };

  const handleDeleteWork = (idx: number) => {
    if (!parsedData) return;
    setParsedData({
      ...parsedData,
      work_history: (parsedData.work_history || []).filter((_, i) => i !== idx),
    });
    setIsDirty(true);
  };

  const handleDeleteEdu = (idx: number) => {
    if (!parsedData) return;
    setParsedData({
      ...parsedData,
      education: (parsedData.education || []).filter((_, i) => i !== idx),
    });
    setIsDirty(true);
  };

  const handleGoManual = () => {
    // Spec 5: Error Handling -> Alternative Paths
    setParsedData({
      id: "manual-" + Date.now(),
      full_name: "Candidate Name",
      skills: [],
      experience_years_total: 0,
      education: [],
      certifications: [],
      summary: "Manual Entry Mode"
    });
    setIsDirty(true);
    setStatus("viewing");
  };

  const handleManualAddSkill = () => {
    if (!parsedData) return;
    const newSkill = {
      name: "New Skill",
      category: "Technology",
      experience_years: 1,
      level: "Junior",
    };
    setParsedData({
      ...parsedData,
      skills: [...(parsedData.skills || []), newSkill],
    });
    setIsDirty(true);
  };

  const handleUpdateSkill = (idx: number, field: string, value: any) => {
    if (!parsedData) return;
    const nextSkills = [...(parsedData.skills || [])];
    if (nextSkills[idx]) {
      nextSkills[idx] = { ...nextSkills[idx], [field]: value };
      setParsedData({ ...parsedData, skills: nextSkills });
      setIsDirty(true);
    }
  };

  const handleDeleteSkill = (idx: number) => {
    if (!parsedData) return;
    setParsedData({
      ...parsedData,
      skills: (parsedData.skills || []).filter((_, i) => i !== idx),
    });
    setIsDirty(true);
  };

  const handleSaveMatrix = async () => {
    setSaving(true);
    
    // Duplicate check
    const skillNames = (parsedData?.skills || []).map(s => s.name.toLowerCase().trim());
    const duplicateSkills = skillNames.filter((name, index) => skillNames.indexOf(name) !== index);
    if (duplicateSkills.length > 0) {
      const uniqueDupes = Array.from(new Set(duplicateSkills));
      alert(`Phát hiện kĩ năng bị trùng lặp: ${uniqueDupes.join(", ")}. Vui lòng xóa hoặc sửa tên kĩ năng trước khi lưu.`);
      setSaving(false);
      return;
    }

    try {
      // Backend Spec 5: Payload validation
      const payload = {
        id: parsedData?.id,
        full_name: parsedData?.full_name,
        summary: parsedData?.summary,
        experience_years_total: parsedData?.experience_years_total,
        skills: parsedData?.skills,
        work_history: parsedData?.work_history,
        education: parsedData?.education,
        certifications: parsedData?.certifications,
        seniority: parsedData?.seniority || "Unknown"
      };
      await axios.post("/api/cv/finalize", payload, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (parsedData) {
        setParsedData({ ...parsedData, is_verified: true });
      }

      const wasDirty = isDirty;
      setIsDirty(false);
      
      // Update sessionStorage inside analysis_context to reflect removed skills
      if (analysisContext) {
        const updatedContext = { ...analysisContext, suggested_skills: suggestedSkills };
        sessionStorage.setItem("analysis_context", JSON.stringify(updatedContext));
        setAnalysisContext(updatedContext);
      }

      if (wasDirty && analysisContext) {
        setShowRerunModal(true);
      } else {
        alert("Hồ sơ năng lực đã được lưu thành công!");
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Lỗi khi lưu Portfolio.";
      alert(Array.isArray(msg) ? msg[0].msg : msg);
    } finally {
      setSaving(false);
    }
  };

  // ── Processing state ────────────────────────────────────────────────────────
  if (status === "processing") {
    return (
      <div className={styles.processingPanel}>
        <div className={styles.spinnerWrapper}>
          <div className={styles.spinnerRing}></div>
          <Loader2 size={48} className={styles.pulseIcon} />
        </div>
        <div>
          <h2 className={styles.processingTitle}>
            {selectedHistoryId ? "Đang tải chi tiết CV..." : "ĐANG PHÂN TÍCH CV..."}
          </h2>
          <p className={styles.processingDesc}>
            {selectedHistoryId
              ? "AI đang tải dữ liệu hồ sơ từ hệ thống."
              : "AI đang trích xuất kỹ năng từ CV của bạn."}
          </p>
        </div>
      </div>
    );
  }

  // ── Viewing state ─────────────────────────────────────────────────────────
  if (status === "viewing" && parsedData) {
    // Include the original index for accurate updates
    const skillsWithIndex = (parsedData.skills || []).map((s, i) => ({ ...s, originalIndex: i }));
    const groupedSkills = skillsWithIndex.reduce((acc: any, skill) => {
      const cat = skill.category || "Uncategorized";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(skill);
      return acc;
    }, {});

    // Filter out suggestions that are already present in the CV (case-insensitive)
    const filteredSuggestions = suggestedSkills.filter(s => 
      !parsedData.skills?.some(existing => 
        existing.name.toLowerCase().trim() === s.toLowerCase().trim()
      )
    );

    const seniorityColor = {
      Junior: "#22c55e",
      "Mid-level": "#3b82f6",
      Senior: "#a855f7",
      Expert: "#f59e0b",
      Unknown: "#9ca3af",
    };
    const sc = seniorityColor[parsedData.seniority as keyof typeof seniorityColor] || "#9ca3af";

    return (
      <motion.div
        className={styles.stackSection}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* ── Back button ──────────────────────────────────────────────── */}
        <div className={styles.backRow}>
          <button onClick={handleBack} className={styles.backBtn}>
            <ArrowLeft size={16} />
            Quay lại kho hồ sơ
          </button>
        </div>

        {/* ── Smart Suggestions Banner ───────────────────────────────── */}
        {filteredSuggestions.length > 0 && parsedData.id === analysisContext?.cv_id && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className={styles.suggestionBanner}
          >
            <div className={styles.bannerIcon}>
              <Sparkles size={20} color="#f59e0b" />
            </div>
            <div className={styles.bannerContent}>
               <div className={styles.bannerTitle}>
                  Gợi ý tối ưu CV cho: <strong>{analysisContext?.jd_title || "Vị trí đã chọn"}</strong>
               </div>
               <p className={styles.bannerSubtitle}>
                  Dựa trên phân tích Gap, bạn nên bổ sung các kỹ năng sau để tăng điểm tương thích:
               </p>
               <div className={styles.suggestedTagsGrid}>
                  {filteredSuggestions.map(skill => (
                    <button 
                      key={skill} 
                      onClick={() => handleAddSuggestedSkill(skill)}
                      className={styles.suggestedTagBtn}
                    >
                      <Plus size={12} />
                      {skill}
                    </button>
                  ))}
               </div>
            </div>
            <button 
              className={styles.closeBannerBtn} 
              onClick={() => setSuggestedSkills([])}
            >
              <X size={16} />
            </button>
          </motion.div>
        )}

        {/* ── Result Header ───────────────────────────────────────────── */}
        <div className={styles.resultHeader}>
          {parsedData.is_ocr && !parsedData.is_verified && (
            <div className={styles.verificationBanner}>
              <div className={styles.bannerIcon}>
                <AlertCircle size={20} />
              </div>
              <div className={styles.bannerText}>
                <strong>Hệ thống đã đọc xong CV của bạn thông qua OCR.</strong>
                <p>Vui lòng kiểm tra và hiệu chỉnh lại danh sách kỹ năng bên dưới để đảm bảo Lộ trình sự nghiệp được chính xác 100%.</p>
              </div>
            </div>
          )}

          <div className={styles.resultHeaderGroup}>
            <div className={styles.userBasicInfo}>
              <div className={styles.avatar}>
                <FileText size={32} />
              </div>
              <div>
                <div className={styles.nameRow}>
                  <input
                    type="text"
                    value={parsedData.full_name || ""}
                    onChange={(e) => handleUpdateBasic("full_name", e.target.value)}
                    className={styles.nameInput}
                    placeholder="Họ và tên"
                  />
                  <CustomDropdown
                    value={parsedData.seniority || "Unknown"}
                    options={["Junior", "Mid-level", "Senior", "Expert", "Unknown"]}
                    onChange={(val) => handleUpdateBasic("seniority", val)}
                    className={styles.senioritySelect}
                    style={{ color: sc, borderColor: sc + "40", background: sc + "12" }}
                  />
                </div>
                <div className={styles.metaRow}>
                  <div className={styles.userExpBadge}>
                    <Clock size={13} />
                    <input
                        type="number"
                        step="0.5"
                        value={parsedData.experience_years_total ?? 0}
                        onChange={(e) => handleUpdateBasic("experience_years_total", parseFloat(e.target.value) || 0)}
                        className={styles.inlineEditInput}
                    />
                    năm kinh nghiệm
                  </div>
                  {parsedData.is_ocr && (
                    <div className={styles.ocrBadge}>
                      <AlertCircle size={13} />
                      OCR
                    </div>
                  )}
                  <div className={cn(styles.secureBadge, styles.secureBadgeVerified)}>
                    <ShieldCheck size={13} />
                    <span className={styles.secureTextVerified}>AI Verified</span>
                  </div>
                </div>
              </div>
            </div>

            <div className={styles.ctaRow}>
              {!parsedData.is_verified && (
                <button
                  onClick={handleSaveMatrix}
                  disabled={saving}
                  className={cn(styles.uploadBtn, styles.verifyBtnGradient)}
                >
                  {saving ? (
                    <Loader2 size={18} className={styles.animateSpin} />
                  ) : (
                    <ShieldCheck size={18} />
                  )}
                  XÁC THỰC HỒ SƠ
                </button>
              )}
              <button
                onClick={handleSaveMatrix}
                disabled={saving}
                className={cn(styles.uploadBtn, styles.uploadBtnFinal)}
              >
                {saving ? (
                  <Loader2 size={18} className={styles.animateSpin} />
                ) : (
                  <Save size={18} />
                )}
                LƯU THAY ĐỔI
              </button>
            </div>
          </div>

          {parsedData.summary !== undefined && (
            <div className={styles.summarySection}>
              <h4 className={styles.summaryTitle}>AI Professional Summary</h4>
              <textarea
                value={parsedData.summary || ""}
                onChange={(e) => handleUpdateBasic("summary", e.target.value)}
                className={styles.summaryTextarea}
                placeholder="Tóm tắt mục tiêu nghề nghiệp và kinh nghiệm cốt lõi..."
              />
            </div>
          )}
        </div>

        {/* ── Three-column grid ───────────────────────────────────────── */}
        <div className={styles.detailGrid}>
          {/* Left: Skills Matrix */}
          <div className={styles.matrixPanel}>
            <h2 className={styles.matrixTitle}>
              <Sparkles size={20} className={styles.matrixTitleIcon} />
              COMPETENCY MATRIX
            </h2>

            {Object.keys(groupedSkills).length === 0 ? (
              <p className={styles.emptyText}>Chưa có kỹ năng nào được trích xuất.</p>
            ) : (
              Object.keys(groupedSkills).map((cat) => (
                <div key={cat} className={styles.catGroup}>
                  <h5 className={styles.catLabel}>{cat}</h5>
                  <div className={styles.flexWrapGap}>
                    {groupedSkills[cat].map((skill: any, idx: number) => (
                      <div key={idx} className={styles.skillItem}>
                        <input
                          type="text"
                          value={skill.name}
                          onChange={(e) =>
                            handleUpdateSkill(skill.originalIndex, "name", e.target.value)
                          }
                          className={styles.skillNameInput}
                          placeholder="Tên kĩ năng"
                        />
                        <input
                          type="number"
                          value={skill.experience_years ?? 0}
                          onChange={(e) =>
                            handleUpdateSkill(skill.originalIndex, "experience_years", parseInt(e.target.value) || 0)
                          }
                          className={styles.editInput}
                          min={0}
                        />
                        <span className={styles.yrsLabel}>YRS</span>
                        <CustomDropdown
                          value={skill.level || "Junior"}
                          options={["Junior", "Mid-level", "Senior", "Expert"]}
                          onChange={(val) => handleUpdateSkill(skill.originalIndex, "level", val)}
                          className={styles.skillLevelSelect}
                        />
                        <button
                          onClick={() => handleDeleteSkill(skill.originalIndex)}
                          className={styles.deleteSkillBtn}
                        >
                          <X size={13} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}

            <button onClick={handleManualAddSkill} className={styles.addSkillBtn}>
              <Plus size={14} />
              Bổ sung kỹ năng
            </button>
          </div>

          {/* Middle: Work History + Education */}
          <div className={styles.middleCol}>
            <div className={styles.sectionCard}>
              <h3 className={styles.sectionTitle}>
                <Briefcase size={18} className={styles.sectionTitleIcon} />
                KINH NGHIỆM LÀM VIỆC
              </h3>
              <div className={styles.timelineList}>
                {(parsedData.work_history || []).map((w, idx) => (
                  <div key={idx} className={styles.timelineItem}>
                    <div className={styles.timelineDot} />
                    <div className={styles.timelineContent}>
                      <div className={styles.timelineHeader}>
                        <input
                          type="text"
                          value={w.position || ""}
                          onChange={(e) => handleUpdateWork(idx, "position", e.target.value)}
                          className={styles.timelineInput}
                          placeholder="Vị trí"
                        />
                        <input
                          type="number"
                          step="0.1"
                          value={w.duration_years || 0}
                          onChange={(e) => handleUpdateWork(idx, "duration_years", parseFloat(e.target.value) || 0)}
                          className={styles.timelineSmallInput}
                        />
                        <span className={styles.yrsLabel}>năm</span>
                        <button onClick={() => handleDeleteWork(idx)} className={styles.itemDeleteBtn}>
                          <X size={14} />
                        </button>
                      </div>
                      <input
                        type="text"
                        value={w.company || ""}
                        onChange={(e) => handleUpdateWork(idx, "company", e.target.value)}
                        className={styles.timelineSubInput}
                        placeholder="Công ty"
                      />
                      <textarea
                        value={w.description || ""}
                        onChange={(e) => handleUpdateWork(idx, "description", e.target.value)}
                        className={styles.timelineDescTextarea}
                        placeholder="Mô tả công việc..."
                      />
                    </div>
                  </div>
                ))}
                <button
                  onClick={() => {
                    const next = [...(parsedData.work_history || []), { position: "New Pos", company: "Company", duration_years: 1, description: "" }];
                    handleUpdateBasic("work_history", next);
                  }}
                  className={styles.addItemBtn}
                >
                  <Plus size={14} /> Thêm kinh nghiệm
                </button>
              </div>
            </div>

            <div className={styles.sectionCard}>
              <h3 className={styles.sectionTitle}>
                <GraduationCap size={18} className={styles.sectionTitleIcon} />
                HỌC VẤN
              </h3>
              <div className={styles.timelineList}>
                {(parsedData.education || []).map((e, idx) => (
                  <div key={idx} className={styles.timelineItem}>
                    <div className={styles.timelineDot} />
                    <div className={styles.timelineContent}>
                      <div className={styles.timelineHeader}>
                        <input
                          type="text"
                          value={e.degree || ""}
                          onChange={(e) => handleUpdateEdu(idx, "degree", e.target.value)}
                          className={styles.timelineInput}
                          placeholder="Bằng cấp"
                        />
                        <input
                          type="text"
                          value={e.year || ""}
                          onChange={(e) => handleUpdateEdu(idx, "year", e.target.value)}
                          className={styles.timelineSmallInput}
                          placeholder="Năm"
                        />
                        <button onClick={() => handleDeleteEdu(idx)} className={styles.itemDeleteBtn}>
                          <X size={14} />
                        </button>
                      </div>
                      <input
                        type="text"
                        value={e.institution || ""}
                        onChange={(e) => handleUpdateEdu(idx, "institution", e.target.value)}
                        className={styles.timelineSubInput}
                        placeholder="Trường / Cơ sở đào tạo"
                      />
                    </div>
                  </div>
                ))}
                <button
                  onClick={() => {
                    const next = [...(parsedData.education || []), { degree: "Degree", institution: "University", year: "2024" }];
                    handleUpdateBasic("education", next);
                  }}
                  className={styles.addItemBtn}
                >
                  <Plus size={14} /> Thêm học vấn
                </button>
              </div>
            </div>

            <div className={styles.sectionCard}>
              <h3 className={styles.sectionTitle}>
                <Award size={18} className={styles.sectionTitleIcon} />
                CHỨNG CHỈ
              </h3>
              <div className={styles.certList}>
                {(parsedData.certifications || []).map((cert, idx) => (
                  <div key={idx} className={styles.certItemEditable}>
                    <BadgeCheck size={16} className={styles.certIcon} />
                    <input
                      type="text"
                      value={cert || ""}
                      onChange={(e) => handleUpdateCert(idx, e.target.value)}
                      className={styles.certInput}
                    />
                    <button
                      onClick={() => {
                        const next = (parsedData.certifications || []).filter((_, i) => i !== idx);
                        handleUpdateBasic("certifications", next);
                      }}
                      className={styles.certDeleteBtn}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => {
                    const next = [...(parsedData.certifications || []), "Chứng chỉ mới"];
                    handleUpdateBasic("certifications", next);
                  }}
                  className={styles.addItemBtn}
                >
                  <Plus size={14} /> Thêm chứng chỉ
                </button>
              </div>
            </div>
          </div>

          {/* Right: Sidebar */}
          <div className={styles.verifyPanel}>
            <h4 className={styles.scoringTitle}>Tổng quan</h4>
            <div className={styles.stackTight}>
              <div className={styles.statRow}>
                <span className={styles.statLabel}>Kỹ năng</span>
                <span className={styles.statValue}>
                  {(parsedData.skills || []).length}
                </span>
              </div>
              <div className={styles.statRow}>
                <span className={styles.statLabel}>Kinh nghiệm</span>
                <span className={styles.statValue}>
                  {parsedData.experience_years_total ?? 0} năm
                </span>
              </div>
              <div className={styles.statRow}>
                <span className={styles.statLabel}>Học vấn</span>
                <span className={styles.statValue}>
                  {(parsedData.education || []).length} bậc
                </span>
              </div>
              <div className={styles.statRow}>
                <span className={styles.statLabel}>Chứng chỉ</span>
                <span className={styles.statValue}>
                  {(parsedData.certifications || []).length} cái
                </span>
              </div>
            </div>

            <div className={styles.infoBox}>
              <p className={styles.infoText}>
                Các kỹ năng được bóc tách sẽ được sử dụng để chạy Gap Analysis trên
                5,000+ vị trí công việc.
              </p>
              <button
                onClick={handleSaveMatrix}
                className={cn(styles.uploadBtn, styles.checkBtn)}
              >
                {saving ? (
                  <Loader2 size={16} className={styles.animateSpin} />
                ) : (
                  <CheckCircle2 size={20} />
                )}
                Lưu thay đổi
              </button>
            </div>
          </div>
        </div>

        {/* ── Rerun Confirmation Modal ───────────────────────────────── */}
        <AnimatePresence>
          {showRerunModal && (
            <div className={styles.modalBackdrop}>
              <motion.div
                initial={{ opacity: 0, scale: 0.9, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: 20 }}
                className={styles.modalCard}
              >
                <div className={styles.modalGlow} />
                <div className={styles.modalHeader}>
                  <div className={styles.modalIconBox}>
                    <Zap size={24} className={styles.modalZap} />
                  </div>
                  <h2 className={styles.modalTitle}>Cập nhật CV thành công!</h2>
                </div>
                <div className={styles.modalBody}>
                  <p>
                    Bạn vừa thay đổi thông tin CV. Bạn có muốn chạy lại <strong>Phân tích Gap</strong> 
                    cho vị trí <strong>{analysisContext?.jd_title || "đã chọn"}</strong> để cập nhật điểm tương thích mới nhất không?
                  </p>
                </div>
                <div className={styles.modalFooter}>
                  <button onClick={() => setShowRerunModal(false)} className={styles.modalCancelBtn}>
                    ĐỂ SAU
                  </button>
                  <button 
                    onClick={() => {
                        setShowRerunModal(false);
                        handleRerunAnalysis();
                    }} 
                    className={styles.modalConfirmBtn}
                  >
                    CHẠY LẠI NGAY
                    <ArrowRight size={16} />
                  </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>
      </motion.div>
    );
  }

  // ── Idle / Upload state ───────────────────────────────────────────────────
  return (
    <AuthGuard requireRole="user">
      <div className={styles.pageRoot}>
        {/* Header */}
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>
              <Zap size={40} className={styles.zapIcon} />
              KHO HỒ SƠ CÁ NHÂN
            </h1>
            <p className={styles.subtitle}>
              Tải lên CV (PDF/Images) để AI tự động trích xuất và tối ưu lộ trình kỹ
              năng.
            </p>
          </div>
          <div className={styles.secureBadge}>
            <ShieldCheck size={18} className={styles.shieldIcon} />
            <span className={styles.secureText}>ISO 27001 SECURE ENCRYPTION</span>
          </div>
        </div>

        <div className={styles.uploadGrid}>
          {/* Left: Upload Area */}
          <div className={styles.uploadZone}>
            <div className={styles.uploadPanel}>
              <div className={styles.uploadGlow} />

              <div
                className={cn(
                  styles.dropZone,
                  isDragging ? styles.dropZoneActive : styles.dropZoneIdle
                )}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0]);
                }}
              >
                <div
                  className={cn(
                    styles.uploadIcon,
                    (file || isDragging) && styles.uploadIconActive
                  )}
                >
                  <UploadCloud size={48} />
                </div>

                <div className={styles.uploadTextCenter}>
                  <h3 className={styles.uploadH3}>
                    {file ? file.name : "Kéo thả hồ sơ vào đây"}
                  </h3>
                  <p className={styles.uploadP}>
                    Chấp nhận định dạng .pdf, .png, .jpg (Tối đa 10MB)
                  </p>
                </div>

                <div className={styles.loaderWrapper}>
                  <input
                    type="file"
                    className="hidden"
                    id="cv-upload"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    accept=".pdf,image/*"
                  />
                  <label htmlFor="cv-upload" className={styles.browseLabel}>
                    Hoặc duyệt từ máy tính
                  </label>
                </div>
              </div>

              {error && (
                <div className={styles.errorStack}>
                  <div className={styles.errorBox}>
                    <AlertCircle size={18} className={styles.errorIcon} />
                    {error}
                  </div>
                  <button onClick={handleGoManual} className={styles.manualEntryBtn}>
                    <Plus size={14} />
                    TỰ NHẬP KỸ NĂNG (BỎ QUA AI)
                  </button>
                </div>
              )}

              <button
                onClick={handleUpload}
                disabled={!file || status === "uploading"}
                className={styles.uploadBtn}
              >
                {status === "uploading" ? (
                  <Loader2 size={20} className={styles.animateSpin} />
                ) : (
                  <Sparkles size={20} />
                )}
                {status === "uploading" ? "AI ĐANG PHÂN TÍCH..." : "BẮT ĐẦU TRÍCH XUẤT AI"}
              </button>
            </div>
          </div>

          {/* Right: History */}
          <div className={styles.historySection}>
            <div className={styles.historyTitle}>
              LỊCH SỬ HỒ SƠ
              <div className={styles.historyTitleLine} />
            </div>

            <AnimatePresence>
              {history.map((item) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn(
                    styles.historyItem,
                    item.id === selectedHistoryId && styles.historyItemActive
                  )}
                  onClick={() => handleHistoryClick(item)}
                >
                  <div className={styles.historyItemContent}>
                    <div
                      className={cn(
                        styles.historyIcon,
                        item.status === "completed"
                          ? styles.historyIconCompleted
                          : item.status === "failed"
                          ? styles.historyIconFailed
                          : styles.historyIconProcessing
                      )}
                    >
                      {item.status === "completed" ? (
                        <CheckCircle2 size={20} />
                      ) : item.status === "failed" ? (
                        <AlertCircle size={20} />
                      ) : (
                        <Loader2 size={20} className={styles.animateSpin} />
                      )}
                    </div>
                    <div>
                      <h4 className={styles.historyFileName}>
                        {item.full_name || item.file_name || `CV ${item.id.slice(0, 8)}`}
                      </h4>
                      <p className={styles.historyDate}>
                        {item.status === "completed"
                          ? `Đã phân tích · ${new Date(item.created_at).toLocaleString("vi-VN")}`
                          : item.status === "failed"
                          ? `Lỗi phân tích · ${new Date(item.created_at).toLocaleString("vi-VN")}`
                          : `Đang xử lý · ${new Date(item.created_at).toLocaleString("vi-VN")}`}
                      </p>
                      {item.status === "failed" && item.error_message && (
                        <div className={styles.historyErrorText}>
                          <AlertCircle size={12} />
                          <span>{item.error_message}</span>
                        </div>
                      )}
                    </div>
                  </div>
                  {item.status === "completed" && (
                    <ChevronRight size={18} className={styles.historyChevron} />
                  )}
                </motion.div>
              ))}
            </AnimatePresence>

            {history.length === 0 && (
              <div className={styles.historyEmptyState}>
                <Clock size={48} className={styles.historyEmptyIcon} />
                <p className={styles.historyEmptyText}>Chưa có lịch sử</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AuthGuard>
  );
};

export default UserCVPage;

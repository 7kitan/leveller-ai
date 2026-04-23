"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import api from "@/lib/api";
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
import { useLanguage } from "@/context/LanguageContext";

const POLLING_INTERVAL = 5000;

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

const SENIORITY_LEVELS = ["Junior", "Mid-level", "Senior", "Expert", "Unknown"];
const SKILL_LEVELS = ["Junior", "Mid-level", "Senior", "Expert"];

const UserCVPage = () => {
  const { token } = useAuth();
  const { t, language } = useLanguage();

  const getSeniorityLabel = (val: string) => {
    switch (val) {
      case "Junior": return t("cv_level_junior");
      case "Mid-level": return t("cv_level_mid");
      case "Senior": return t("cv_level_senior");
      case "Expert": return t("cv_level_expert");
      case "Unknown": return t("cv_level_unknown");
      default: return val;
    }
  };
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
      const resp = await api.get("/api/cv/list");
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
      category: t("cv_skill_default_cat"),
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
    router.push(`/user/analysis?job_id=${analysisContext.jd_id}&auto_run=true`);
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus("uploading");
    setError(null);
    setSelectedHistoryId(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await api.post("/api/cv/upload", formData, {
        headers: {
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
          const detailResp = await api.get(`/api/cv/${cv_id}`);
          setParsedData(detailResp.data);
          setStatus("viewing");
          fetchHistory();
        } catch (err) {
          console.error("Lỗi khi lấy chi tiết CV cũ:", err);
          setError(t("error"));
          setStatus("idle");
        }
      } else if (parser_id) {
        pollStatus(parser_id, cv_id);
      } else {
        console.error("Backend did not return parser_id or completed status", resp.data);
        setError(t("error"));
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
        const resp = await api.get(`/api/cv/status/${parserId}`);
        const { status: taskStatus, result } = resp.data;

        if (taskStatus === "completed") {
          clearInterval(interval);
          if (result) {
            setParsedData(result);
          } else {
            const detailResp = await api.get(`/api/cv/${cvId}`);
            setParsedData(detailResp.data);
          }
          setStatus("viewing");
          fetchHistory();
        } else if (taskStatus === "failed") {
          clearInterval(interval);
          setError(t("cv_processing_ai_sub")); // Or specific error
          setStatus("idle");
        }
      } catch {
        clearInterval(interval);
        setStatus("idle");
      }
    }, POLLING_INTERVAL);
  };

  const handleLoadSpecificCV = async (cvId: string) => {
    setStatus("processing");
    setError(null);
    setSelectedHistoryId(cvId);
    try {
      const resp = await api.get(`/api/cv/${cvId}`);
      setParsedData(resp.data);
      setStatus("viewing");
    } catch (err) {
      console.error("Auto-load CV detail error:", err);
      setError(t("error"));
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
      const resp = await api.get(`/api/cv/${item.id}`);
      setParsedData(resp.data);
      setStatus("viewing");
    } catch (err) {
      console.error("Load CV detail error:", err);
      setError(t("error"));
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
      full_name: t("cv_candidate_name_placeholder"),
      skills: [],
      experience_years_total: 0,
      education: [],
      certifications: [],
      summary: t("cv_manual_entry_mode")
    });
    setIsDirty(true);
    setStatus("viewing");
  };

  const handleManualAddSkill = () => {
    if (!parsedData) return;
    const newSkill = {
      name: t("cv_skill_default_name"),
      category: t("cv_skill_default_cat"),
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

      // Auto-suggest level based on experience_years
      if (field === "experience_years") {
        const yrs = parseFloat(value) || 0;
        let suggestedLevel = "Junior";
        if (yrs >= 10) suggestedLevel = "Expert";
        else if (yrs >= 5) suggestedLevel = "Senior";
        else if (yrs >= 2) suggestedLevel = "Mid-level";
        nextSkills[idx].level = suggestedLevel;
      }

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
      alert(t("cv_duplicate_skill_error"));
      setSaving(false);
      return;
    }

    try {
      // Normalize categories to English for database consistency
      const normalizedSkills = (parsedData?.skills || []).map(skill => {
        let cat = skill.category || "Uncategorized";
        const lowerCat = cat.toLowerCase().trim();
        if (lowerCat === "công nghệ") {
          cat = "Technology";
        }
        return { ...skill, category: cat };
      });

      // Backend Spec 5: Payload validation
      const payload = {
        id: parsedData?.id,
        full_name: parsedData?.full_name,
        summary: parsedData?.summary,
        experience_years_total: parsedData?.experience_years_total,
        skills: normalizedSkills,
        work_history: parsedData?.work_history,
        education: parsedData?.education,
        certifications: parsedData?.certifications,
        seniority: parsedData?.seniority || "Unknown"
      };
      await api.post("/api/cv/finalize", payload);
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
        alert(t("cv_save_success"));
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || t("error");
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
            {selectedHistoryId ? t("cv_processing_detail") : t("cv_processing_ai")}
          </h2>
          <p className={styles.processingDesc}>
            {selectedHistoryId
              ? t("cv_processing_detail_sub")
              : t("cv_processing_ai_sub")}
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
      let cat = skill.category || "Uncategorized";
      // Normalize common categories to unify English/Vietnamese versions
      const lowerCat = cat.toLowerCase().trim();
      if (lowerCat === "technology") {
        cat = t("cv_skill_default_cat");
      }

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
            {t("cv_back_to_history")}
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
                {t("cv_optimization_suggestion")}: <strong>{analysisContext?.jd_title || t("select_job")}</strong>
              </div>
              <p className={styles.bannerSubtitle}>
                {t("cv_optimization_sub")}
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
                <strong>{t("cv_ocr_banner_title")}</strong>
                <p>{t("cv_ocr_banner_sub")}</p>
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
                    placeholder={t("cv_full_name_placeholder")}
                  />
                  <CustomDropdown
                    value={getSeniorityLabel(parsedData.seniority || "Unknown")}
                    options={SENIORITY_LEVELS.map(getSeniorityLabel)}
                    onChange={(val) => {
                      const key = SENIORITY_LEVELS.find(k => getSeniorityLabel(k) === val);
                      if (key) handleUpdateBasic("seniority", key);
                    }}
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
                    {t("cv_years_exp")}
                  </div>
                  {parsedData.is_ocr && (
                    <div className={styles.ocrBadge}>
                      <AlertCircle size={13} />
                      OCR
                    </div>
                  )}
                  <div className={cn(styles.secureBadge, styles.secureBadgeVerified)}>
                    <ShieldCheck size={13} />
                    <span className={styles.secureTextVerified}>{t("cv_ai_verified")}</span>
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
                  {t("cv_verify_profile")}
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
                {t("cv_save_changes")}
              </button>
            </div>
          </div>

          {parsedData.summary !== undefined && (
            <div className={styles.summarySection}>
              <h4 className={styles.summaryTitle}>{t("cv_professional_summary")}</h4>
              <textarea
                value={parsedData.summary || ""}
                onChange={(e) => handleUpdateBasic("summary", e.target.value)}
                className={styles.summaryTextarea}
                placeholder={t("cv_summary_placeholder")}
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
              {t("cv_competency_matrix")}
            </h2>

            {Object.keys(groupedSkills).length === 0 ? (
              <p className={styles.emptyText}>{t("cv_no_skills")}</p>
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
                          placeholder={t("cv_skill_name_placeholder")}
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
                        <span className={styles.yrsLabel}>{t("cv_years_short")}</span>
                        <CustomDropdown
                          value={getSeniorityLabel(skill.level || "Junior")}
                          options={SKILL_LEVELS.map(getSeniorityLabel)}
                          onChange={(val) => {
                            const key = SKILL_LEVELS.find(k => getSeniorityLabel(k) === val);
                            if (key) handleUpdateSkill(skill.originalIndex, "level", key);
                          }}
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
              {t("cv_add_skill")}
            </button>
          </div>

          {/* Middle: Work History + Education */}
          <div className={styles.middleCol}>
            <div className={styles.sectionCard}>
              <h3 className={styles.sectionTitle}>
                <Briefcase size={18} className={styles.sectionTitleIcon} />
                {t("cv_work_history")}
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
                          placeholder={t("cv_position_placeholder")}
                        />
                        <input
                          type="number"
                          step="0.1"
                          value={w.duration_years || 0}
                          onChange={(e) => handleUpdateWork(idx, "duration_years", parseFloat(e.target.value) || 0)}
                          className={styles.timelineSmallInput}
                        />
                        <span className={styles.yrsLabel}>{t("cv_years_short")}</span>
                        <button onClick={() => handleDeleteWork(idx)} className={styles.itemDeleteBtn}>
                          <X size={14} />
                        </button>
                      </div>
                      <input
                        type="text"
                        value={w.company || ""}
                        onChange={(e) => handleUpdateWork(idx, "company", e.target.value)}
                        className={styles.timelineSubInput}
                        placeholder={t("cv_company_placeholder")}
                      />
                      <textarea
                        value={w.description || ""}
                        onChange={(e) => handleUpdateWork(idx, "description", e.target.value)}
                        className={styles.timelineDescTextarea}
                        placeholder={t("cv_work_desc_placeholder")}
                      />
                    </div>
                  </div>
                ))}
                <button
                  onClick={() => {
                    const next = [...(parsedData.work_history || []), { position: t("cv_new_pos"), company: t("cv_new_company"), duration_years: 1, description: "" }];
                    handleUpdateBasic("work_history", next);
                  }}
                  className={styles.addItemBtn}
                >
                  <Plus size={14} /> {t("cv_add_exp")}
                </button>
              </div>
            </div>

            <div className={styles.sectionCard}>
              <h3 className={styles.sectionTitle}>
                <GraduationCap size={18} className={styles.sectionTitleIcon} />
                {t("cv_education")}
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
                          placeholder={t("cv_degree_placeholder")}
                        />
                        <input
                          type="text"
                          value={e.year || ""}
                          onChange={(e) => handleUpdateEdu(idx, "year", e.target.value)}
                          className={styles.timelineSmallInput}
                          placeholder={t("cv_year_placeholder")}
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
                        placeholder={t("cv_institution_placeholder")}
                      />
                    </div>
                  </div>
                ))}
                <button
                  onClick={() => {
                    const next = [...(parsedData.education || []), { degree: t("cv_new_degree"), institution: t("cv_new_institution"), year: "2024" }];
                    handleUpdateBasic("education", next);
                  }}
                  className={styles.addItemBtn}
                >
                  <Plus size={14} /> {t("cv_add_edu")}
                </button>
              </div>
            </div>

            <div className={styles.sectionCard}>
              <h3 className={styles.sectionTitle}>
                <Award size={18} className={styles.sectionTitleIcon} />
                {t("cv_certifications")}
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
                    const next = [...(parsedData.certifications || []), t("cv_new_cert")];
                    handleUpdateBasic("certifications", next);
                  }}
                  className={styles.addItemBtn}
                >
                  <Plus size={14} /> {t("cv_add_cert")}
                </button>
              </div>
            </div>
          </div>

          {/* Right: Sidebar */}
          <div className={styles.verifyPanel}>
            <h4 className={styles.scoringTitle}>{t("cv_overview")}</h4>
            <div className={styles.stackTight}>
              <div className={styles.statRow}>
                <span className={styles.statLabel}>{t("nav_skills")}</span>
                <span className={styles.statValue}>
                  {(parsedData.skills || []).length}
                </span>
              </div>
              <div className={styles.statRow}>
                <span className={styles.statLabel}>{t("cv_experience")}</span>
                <span className={styles.statValue}>
                  {parsedData.experience_years_total ?? 0} {t("cv_years_short")}
                </span>
              </div>
              <div className={styles.statRow}>
                <span className={styles.statLabel}>{t("cv_education")}</span>
                <span className={styles.statValue}>
                  {(parsedData.education || []).length} {t("cv_stages")}
                </span>
              </div>
              <div className={styles.statRow}>
                <span className={styles.statLabel}>{t("cv_certifications")}</span>
                <span className={styles.statValue}>
                  {(parsedData.certifications || []).length} {t("cv_items")}
                </span>
              </div>
            </div>

            <div className={styles.infoBox}>
              <p className={styles.infoText}>
                {t("cv_save_matrix_desc")}
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
                {t("cv_save_changes")}
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
                  <h2 className={styles.modalTitle}>{t("cv_update_success")}</h2>
                </div>
                <div className={styles.modalBody}>
                  <p>
                    {t("cv_rerun_desc").replace('{title}', analysisContext?.jd_title || t("selected_job"))}
                  </p>
                </div>
                <div className={styles.modalFooter}>
                  <button onClick={() => setShowRerunModal(false)} className={styles.modalCancelBtn}>
                    {t("later")}
                  </button>
                  <button
                    onClick={() => {
                      setShowRerunModal(false);
                      handleRerunAnalysis();
                    }}
                    className={styles.modalConfirmBtn}
                  >
                    {t("rerun_now")}
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
              {t("cv_repository_title")}
            </h1>
            <p className={styles.subtitle}>
              {t("cv_repository_subtitle")}
            </p>
          </div>
          <div className={styles.secureBadge}>
            <ShieldCheck size={18} className={styles.shieldIcon} />
            <span className={styles.secureText}>{t("cv_secure_iso")}</span>
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
                    {file ? file.name : t("cv_dropzone_idle")}
                  </h3>
                  <p className={styles.uploadP}>
                    {t("cv_dropzone_hint")}
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
                    {t("cv_browse_files")}
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
                    {t("cv_manual_entry")}
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
                {status === "uploading" ? t("cv_analyzing") : t("cv_start_extract")}
              </button>
            </div>
          </div>

          {/* Right: History */}
          <div className={styles.historySection}>
            <div className={styles.historyTitle}>
              {t("cv_history_title")}
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
                          ? `${t("cv_analyzed")} · ${new Date(item.created_at).toLocaleString(language === 'vi' ? "vi-VN" : "en-US")}`
                          : item.status === "failed"
                            ? `${t("cv_analysis_error")} · ${new Date(item.created_at).toLocaleString(language === 'vi' ? "vi-VN" : "en-US")}`
                            : `${t("cv_processing")} · ${new Date(item.created_at).toLocaleString(language === 'vi' ? "vi-VN" : "en-US")}`}
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
                <p className={styles.historyEmptyText}>{t("cv_no_history")}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AuthGuard>
  );
};

export default UserCVPage;

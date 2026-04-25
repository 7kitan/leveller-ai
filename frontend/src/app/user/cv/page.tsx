"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { UserRole } from "@/types/roles";
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
  Layers,
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./user-cv.module.css";
import { motion, AnimatePresence } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";
import Modal from "@/components/shared/Modal";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";

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
      const resp = await api.get("/cv/list");
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
      const resp = await api.post("/cv/upload", formData, {
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
          const detailResp = await api.get(`/cv/${cv_id}`);
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
      setError(err.response?.data?.detail || t("cv_upload_error"));
      setStatus("idle");
    }
  };

  const pollStatus = async (parserId: string, cvId: string) => {
    setStatus("processing");
    const interval = setInterval(async () => {
      try {
        const resp = await api.get(`/cv/status/${parserId}`);
        const { status: taskStatus, result } = resp.data;

        if (taskStatus === "completed") {
          clearInterval(interval);
          if (result) {
            setParsedData(result);
          } else {
            const detailResp = await api.get(`/cv/${cvId}`);
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
      const resp = await api.get(`/cv/${cvId}`);
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
      const resp = await api.get(`/cv/${item.id}`);
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
        let cat = skill.category || t('uncategorized');
        const lowerCat = cat.toLowerCase().trim();
        if (lowerCat === t('cat_technical').toLowerCase() || lowerCat === "công nghệ") {
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
      await api.post("/cv/finalize", payload);
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
      <PageContainer>
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
      </PageContainer>
    );
  }

  // ── Viewing state ─────────────────────────────────────────────────────────
  if (status === "viewing" && parsedData) {
    // Include the original index for accurate updates
    const skillsWithIndex = (parsedData.skills || []).map((s, i) => ({ ...s, originalIndex: i }));

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
      <PageContainer>
        <PageHeader 
          title={parsedData.full_name || t("cv_repository_title")}
          subtitle={t("cv_processing_ai_sub")}
        >
          <button onClick={handleBack} className={styles.backBtn}>
            <ArrowLeft size={16} />
            {t("cv_back_to_history")}
          </button>
        </PageHeader>

        <motion.div
          className={styles.pageRoot}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >

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
                    maxLength={100}
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
                      min={0}
                      max={60}
                    />
                    {t("cv_years_exp")}
                  </div>
                  {parsedData.is_ocr && (
                    <div className={styles.ocrBadge}>
                      <AlertCircle size={13} />
                      {t('ocr_label')}
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
                maxLength={2000}
              />
            </div>
          )}
        </div>

        {/* ── Skills Matrix ───────────────────────────────────────────── */}
        <div className={styles.matrixPanel}>
          <div className={styles.matrixTitle}>
            <Layers size={20} className={styles.matrixTitleIcon} />
            {t("cv_competency_matrix")}
          </div>
          <div className={styles.matrixGrid}>
            {skillsWithIndex.map((skill: any) => (
              <div key={skill.originalIndex} className={styles.skillItem}>
                <div className={styles.skillMain}>
                  <input
                    type="text"
                    value={skill.name}
                    onChange={(e) => handleUpdateSkill(skill.originalIndex, "name", e.target.value)}
                    className={styles.skillNameInput}
                    maxLength={50}
                    placeholder={t("cv_skill_default_name")}
                  />
                  <div className={styles.skillMeta}>
                    <div className={styles.skillExpGroup}>
                      <Clock size={12} />
                      <input
                        type="number"
                        step="0.5"
                        value={skill.experience_years}
                        onChange={(e) => handleUpdateSkill(skill.originalIndex, "experience_years", e.target.value)}
                        className={styles.editInput}
                        min={0}
                        max={60}
                      />
                      <span>{t("cv_years_short")}</span>
                    </div>
                    <CustomDropdown
                      value={getSeniorityLabel(skill.level)}
                      options={SKILL_LEVELS.map(getSeniorityLabel)}
                      onChange={(val) => {
                        const key = SKILL_LEVELS.find(k => getSeniorityLabel(k) === val);
                        if (key) handleUpdateSkill(skill.originalIndex, "level", key);
                      }}
                      className={styles.skillLevelSelect}
                      style={{ color: seniorityColor[skill.level as keyof typeof seniorityColor] }}
                    />
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteSkill(skill.originalIndex)}
                  className={styles.deleteSkillBtn}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            
            <button onClick={handleManualAddSkill} className={styles.addSkillBtn}>
              <div className={styles.addSkillIcon}>
                <Plus size={24} />
              </div>
              <span className={styles.addSkillText}>{t("cv_add_skill")}</span>
            </button>
          </div>
        </div>

        <div className={styles.detailGrid}>
          {/* Work History */}
          <div className={styles.sectionCard}>
            <div className={styles.sectionTitle}>
              <Briefcase size={18} className={styles.sectionTitleIcon} />
              {t("cv_work_history")}
            </div>
            <div className={styles.timelineList}>
              {(parsedData.work_history || []).map((work, i) => (
                <div key={i} className={styles.timelineItem}>
                  <div className={styles.timelineDot} />
                  <div className={styles.timelineContent}>
                    <div className={styles.timelineHeader}>
                      <input
                        type="text"
                        value={work.position}
                        onChange={(e) => handleUpdateWork(i, "position", e.target.value)}
                        className={styles.timelineInput}
                        placeholder={t("cv_position_placeholder")}
                        maxLength={100}
                      />
                      <div className={styles.timelineActions}>
                        <div className={styles.timelineDuration}>
                          <input
                            type="number"
                            step="0.5"
                            value={work.duration_years || 0}
                            onChange={(e) => handleUpdateWork(i, "duration_years", e.target.value)}
                            className={styles.timelineSmallInput}
                          />
                          <span>{t("cv_years_short")}</span>
                        </div>
                        <button onClick={() => handleDeleteWork(i)} className={styles.itemDeleteBtn}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                    <input
                      type="text"
                      value={work.company}
                      onChange={(e) => handleUpdateWork(i, "company", e.target.value)}
                      className={styles.timelineSubInput}
                      placeholder={t("cv_company_placeholder")}
                      maxLength={100}
                    />
                    <textarea
                      value={work.description || ""}
                      onChange={(e) => handleUpdateWork(i, "description", e.target.value)}
                      className={styles.timelineDescTextarea}
                      placeholder={t("cv_work_desc_placeholder")}
                      maxLength={1000}
                    />
                  </div>
                </div>
              ))}
              <button
                onClick={() => {
                  const next = [...(parsedData.work_history || [])];
                  next.unshift({ position: "", company: "" });
                  setParsedData({ ...parsedData, work_history: next });
                  setIsDirty(true);
                }}
                className={styles.addItemBtn}
              >
                <Plus size={14} />
                {t("cv_add_exp")}
              </button>
            </div>
          </div>

          {/* Education */}
          <div className={styles.sectionCard}>
            <div className={styles.sectionTitle}>
              <GraduationCap size={18} className={styles.sectionTitleIcon} />
              {t("cv_education")}
            </div>
            <div className={styles.timelineList}>
              {(parsedData.education || []).map((edu, i) => (
                <div key={i} className={styles.timelineItem}>
                  <div className={styles.timelineDot} />
                  <div className={styles.timelineContent}>
                    <div className={styles.timelineHeader}>
                      <input
                        type="text"
                        value={edu.degree}
                        onChange={(e) => handleUpdateEdu(i, "degree", e.target.value)}
                        className={styles.timelineInput}
                        placeholder={t("cv_degree_placeholder")}
                        maxLength={100}
                      />
                      <div className={styles.timelineActions}>
                        <div className={styles.timelineDuration}>
                          <input
                            type="number"
                            value={edu.year || new Date().getFullYear()}
                            onChange={(e) => handleUpdateEdu(i, "year", e.target.value)}
                            className={styles.timelineSmallInput}
                            style={{ width: '4rem' }}
                          />
                        </div>
                        <button onClick={() => handleDeleteEdu(i)} className={styles.itemDeleteBtn}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                    <input
                      type="text"
                      value={edu.institution}
                      onChange={(e) => handleUpdateEdu(i, "institution", e.target.value)}
                      className={styles.timelineSubInput}
                      placeholder={t("cv_institution_placeholder")}
                      maxLength={100}
                    />
                  </div>
                </div>
              ))}
              <button
                onClick={() => {
                  const next = [...(parsedData.education || [])];
                  next.unshift({ degree: "", institution: "" });
                  setParsedData({ ...parsedData, education: next });
                  setIsDirty(true);
                }}
                className={styles.addItemBtn}
              >
                <Plus size={14} />
                {t("cv_add_edu")}
              </button>
            </div>
          </div>
        </div>

        {/* Certifications */}
        <div className={styles.sectionCard}>
          <div className={styles.sectionTitle}>
            <BadgeCheck size={18} className={styles.sectionTitleIcon} />
            {t("cv_certifications")}
          </div>
          <div className={styles.certList}>
            {(parsedData.certifications || []).map((cert, i) => (
              <div key={i} className={styles.certItemEditable}>
                <input
                  type="text"
                  value={cert}
                  onChange={(e) => handleUpdateCert(i, e.target.value)}
                  className={styles.certInput}
                  placeholder={t("cv_new_cert")}
                  maxLength={200}
                />
                <button
                  onClick={() => {
                    const next = (parsedData.certifications || []).filter((_, j) => j !== i);
                    setParsedData({ ...parsedData, certifications: next });
                    setIsDirty(true);
                  }}
                  className={styles.itemDeleteBtn}
                >
                  <X size={14} />
                </button>
              </div>
            ))}
            <button
              onClick={() => {
                const next = [...(parsedData.certifications || [])];
                next.unshift("");
                setParsedData({ ...parsedData, certifications: next });
                setIsDirty(true);
              }}
              className={styles.addItemBtn}
            >
              <Plus size={14} />
              {t("cv_add_cert")}
            </button>
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

        {/* ── Rerun Confirmation Modal ───────────────────────────────── */}
        <Modal
          isOpen={showRerunModal}
          onClose={() => setShowRerunModal(false)}
          title={t("cv_update_success")}
          maxWidth="500px"
        >
          <div className={styles.modalBodyContent}>
            <div className={styles.modalIconBox}>
              <Zap size={32} className={styles.modalZap} />
            </div>
            <p className={styles.modalDescription}>
              {t("cv_rerun_desc").replace('{title}', analysisContext?.jd_title || t("selected_job"))}
            </p>
            <div className={styles.modalFooterActions}>
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
          </div>
        </Modal>
        </motion.div>
      </PageContainer>
    );
  }

  // ── Idle / Upload state ───────────────────────────────────────────────────
  return (
    <AuthGuard requireRole={UserRole.USER}>
      <PageContainer>
        <PageHeader 
          title={t("cv_repository_title")}
          subtitle={t("cv_repository_subtitle")}
        >
          <div className={styles.secureBadge}>
            <ShieldCheck size={18} className={styles.shieldIcon} />
            <span className={styles.secureText}>{t("cv_secure_iso")}</span>
          </div>
        </PageHeader>

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
                <div className={styles.dropZoneContent}>
                  <div className={styles.cloudIconWrapper}>
                    <UploadCloud size={48} className={styles.cloudIcon} />
                  </div>
                  <h3 className={styles.uploadTitle}>{t("cv_dropzone_idle")}</h3>
                  <p className={styles.uploadSub}>{t("cv_dropzone_hint")}</p>

                  <div className={styles.fileTypes}>
                    <span>PDF</span>
                    <span className={styles.dotSeparator}>•</span>
                    <span>DOCX</span>
                  </div>

                  <label className={styles.browseBtn}>
                    {t("cv_browse_files")}
                    <input
                      type="file"
                      hidden
                      accept=".pdf,.docx"
                      onChange={(e) => {
                        if (e.target.files?.[0]) setFile(e.target.files[0]);
                      }}
                    />
                  </label>
                </div>
              </div>

              {file && (
                <motion.div
                  className={styles.selectedFile}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <FileText className={styles.fileIcon} size={20} />
                  <span className={styles.fileName}>{file.name}</span>
                  <button onClick={() => setFile(null)} className={styles.removeFile}>
                    <X size={16} />
                  </button>
                </motion.div>
              )}

              <button
                disabled={!file || status === "uploading"}
                onClick={handleUpload}
                className={cn(styles.uploadBtn, file && styles.uploadBtnActive)}
              >
                {status === "uploading" ? (
                  <Loader2 size={20} className={styles.animateSpin} />
                ) : (
                  <Zap size={20} />
                )}
                {status === "uploading" ? t("cv_uploading") : t("cv_start_extract")}
              </button>

              <div className={styles.manualEntryHint}>
                <span>{t("cv_or_use")}</span>
                <button onClick={handleGoManual} className={styles.manualLink}>
                  {t("cv_manual_entry")}
                </button>
              </div>

              {error && (
                <div className={styles.errorBanner}>
                  <AlertCircle size={16} />
                  {error}
                </div>
              )}
            </div>
          </div>

          {/* Right: History List */}
          <div className={styles.historyZone}>
            <div className={styles.historyHeader}>
              <h3 className={styles.historyTitle}>
                <Clock size={20} />
                {t("cv_history_title")}
              </h3>
              <span className={styles.historyCount}>
                {history.length} {t("cv_files")}
              </span>
            </div>

            <div className={styles.historyList}>
              {history.length > 0 ? (
                history.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => handleHistoryClick(item)}
                    className={cn(
                      styles.historyItem,
                      item.status === "completed" ? styles.historyItemClickable : styles.historyItemDisabled,
                      selectedHistoryId === item.id && styles.historyItemActive
                    )}
                  >
                    <div className={styles.historyIcon}>
                      <FileText size={20} />
                    </div>
                    <div className={styles.historyInfo}>
                      <div className={styles.historyName}>
                        {item.full_name || item.file_name || t("cv_candidate_name_placeholder")}
                      </div>
                      <div className={styles.historyMeta}>
                        {new Date(item.created_at).toLocaleDateString(language === 'vi' ? "vi-VN" : "en-US")}
                      </div>
                    </div>
                    <div className={cn(styles.historyStatus, styles[item.status])}>
                      {item.status === "completed" && <CheckCircle2 size={16} />}
                      {item.status === "processing" && (
                        <Loader2 size={16} className={styles.animateSpin} />
                      )}
                      {item.status === "failed" && <AlertCircle size={16} />}
                    </div>
                  </div>
                ))
              ) : (
                <div className={styles.emptyHistory}>
                  <FileText size={40} className={styles.emptyIcon} />
                  <p>{t("cv_no_history")}</p>
                </div>
              )}
            </div>

            <div className={styles.historyFooter}>
              <p>{t("cv_history_footer")}</p>
            </div>
          </div>
        </div>
      </PageContainer>
    </AuthGuard>
  );
};

export default UserCVPage;



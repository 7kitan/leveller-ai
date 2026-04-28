"use client";

import React, { useState, useEffect, useCallback, memo, useMemo } from "react";
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
  Save,
  Plus,
  Trash2,
  Briefcase,
  GraduationCap,
  BadgeCheck,
  ArrowLeft,
  X,
  Layers,
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./user-cv.module.css";
import { motion } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";
import { useAlert } from "@/context/AlertContext";
import Modal from "@/components/shared/Modal";
import CustomDropdown from "@/components/shared/CustomDropdown";
import { DebouncedInput } from "@/components/common/DebouncedInput";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";
import { CVPreview } from "@/components/cv/CVPreview";

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

const SENIORITY_LEVELS = ["Junior", "Mid-level", "Senior", "Expert", "Unknown"];
const SKILL_LEVELS = ["Junior", "Mid-level", "Senior", "Expert"];

const UserCVPage = () => {
  const { user } = useAuth();
  const { t, language } = useLanguage();
  const { showSuccess, showError } = useAlert();
  const router = useRouter();

  // --- State Declarations ---
  const [file, setFile] = useState<File | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [history, setHistory] = useState<CVHistory[]>([]);
  const [status, setStatus] = useState<"idle" | "uploading" | "processing" | "viewing">("idle");
  const [parsedData, setParsedData] = useState<ParsedCV | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [showRerunModal, setShowRerunModal] = useState(false);
  const [suggestedSkills, setSuggestedSkills] = useState<string[]>([]);
  const [analysisContext, setAnalysisContext] = useState<any>(null);
  const [realTimeName, setRealTimeName] = useState("");

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

  const fetchHistory = async () => {
    try {
      const resp = await api.get("cv/list");
      setHistory(resp.data);
    } catch (err) {
      console.error("Fetch history error:", err);
    }
  };

  const handleLoadSpecificCV = useCallback(async (cvId: string) => {
    setStatus("processing");
    setError(null);
    setSelectedHistoryId(cvId);
    try {
      const resp = await api.get(`cv/${cvId}`);
      setParsedData(resp.data);
      setStatus("viewing");
    } catch (err) {
      console.error("Auto-load CV detail error:", err);
      setError(t("error"));
      setStatus("idle");
      setSelectedHistoryId(null);
    }
  }, [t]);

  useEffect(() => {
    if (user) {
      fetchHistory();

      const storedContext = sessionStorage.getItem("analysis_context");
      const targetCvId = sessionStorage.getItem("target_cv_id");

      if (storedContext) {
        const context = JSON.parse(storedContext);
        setAnalysisContext(context);
        if (context.suggested_skills) {
          setSuggestedSkills(context.suggested_skills);
        }
      }

      if (targetCvId) {
        handleLoadSpecificCV(targetCvId);
        sessionStorage.removeItem("target_cv_id");
      }
    }
  }, [ handleLoadSpecificCV]);

  useEffect(() => {
    if (parsedData?.full_name) {
      setRealTimeName(parsedData.full_name);
    }
  }, [parsedData?.id]);

  const handleAddSuggestedSkill = useCallback((skill: string) => {
    if (!parsedData) return;
    const next = [...(parsedData.skills || [])];
    next.push({ name: skill, category: t("cv_skill_default_cat"), experience_years: 1, level: "Junior" });
    setParsedData({ ...parsedData, skills: next });
    setIsDirty(true);
    setSuggestedSkills(prev => prev.filter(s => s !== skill));
  }, [parsedData, t]);

  const handleUpdateSkill = useCallback((idx: number, field: string, value: any) => {
    if (!parsedData) return;
    const next = [...(parsedData.skills || [])];
    if (next[idx]) {
      next[idx] = { ...next[idx], [field]: value };
      if (field === "experience_years") {
        const yrs = parseFloat(value) || 0;
        let suggestedLevel = "Junior";
        if (yrs >= 10) suggestedLevel = "Expert";
        else if (yrs >= 5) suggestedLevel = "Senior";
        else if (yrs >= 2) suggestedLevel = "Mid-level";
        next[idx].level = suggestedLevel;
      }
      setParsedData({ ...parsedData, skills: next });
      setIsDirty(true);
    }
  }, [parsedData]);

  const handleDeleteSkill = useCallback((idx: number) => {
    if (!parsedData) return;
    setParsedData({
      ...parsedData,
      skills: (parsedData.skills || []).filter((_, i) => i !== idx),
    });
    setIsDirty(true);
  }, [parsedData]);

  const handleManualAddSkill = useCallback(() => {
    if (!parsedData) return;
    const next = [...(parsedData.skills || [])];
    next.push({ name: t("cv_skill_default_name"), category: t("cv_skill_default_cat"), experience_years: 1, level: "Junior" });
    setParsedData({ ...parsedData, skills: next });
    setIsDirty(true);
  }, [parsedData, t]);

  const handleUpdateBasic = useCallback((field: string, value: any) => {
    if (!parsedData) return;
    setParsedData({ ...parsedData, [field]: value });
    setIsDirty(true);
  }, [parsedData]);

  const handleUpdateWork = useCallback((idx: number, field: string, value: any) => {
    if (!parsedData) return;
    const next = [...(parsedData.work_history || [])];
    if (next[idx]) {
      next[idx] = { ...next[idx], [field]: value };
      setParsedData({ ...parsedData, work_history: next });
      setIsDirty(true);
    }
  }, [parsedData]);

  const handleUpdateEdu = useCallback((idx: number, field: string, value: any) => {
    if (!parsedData) return;
    const next = [...(parsedData.education || [])];
    if (next[idx]) {
      next[idx] = { ...next[idx], [field]: value };
      setParsedData({ ...parsedData, education: next });
      setIsDirty(true);
    }
  }, [parsedData]);

  const handleUpdateCert = useCallback((idx: number, value: string) => {
    if (!parsedData) return;
    const next = [...(parsedData.certifications || [])];
    next[idx] = value;
    setParsedData({ ...parsedData, certifications: next });
    setIsDirty(true);
  }, [parsedData]);

  const handleDeleteWork = useCallback((idx: number) => {
    if (!parsedData) return;
    setParsedData({
      ...parsedData,
      work_history: (parsedData.work_history || []).filter((_, i) => i !== idx),
    });
    setIsDirty(true);
  }, [parsedData]);

  const handleDeleteEdu = useCallback((idx: number) => {
    if (!parsedData) return;
    setParsedData({
      ...parsedData,
      education: (parsedData.education || []).filter((_, i) => i !== idx),
    });
    setIsDirty(true);
  }, [parsedData]);

  const handleRerunAnalysis = useCallback(() => {
    if (!analysisContext) return;
    sessionStorage.removeItem("suggested_skills");
    sessionStorage.removeItem("analysis_context");
    router.push(`/user/analysis?job_id=${analysisContext.jd_id}&auto_run=true`);
  }, [analysisContext, router]);

  const handleSaveMatrix = useCallback(async () => {
    if (!parsedData) return;
    setSaving(true);
    
    const skillNames = (parsedData.skills || []).map(s => s.name.toLowerCase().trim());
    const duplicateSkills = skillNames.filter((name, index) => skillNames.indexOf(name) !== index);
    if (duplicateSkills.length > 0) {
      showError(t("cv_duplicate_skill_error"));
      setSaving(false);
      return;
    }

    try {
      const normalizedSkills = (parsedData.skills || []).map(skill => {
        let cat = skill.category || t('uncategorized');
        const lowerCat = cat.toLowerCase().trim();
        if (lowerCat === t('cat_technical').toLowerCase() || lowerCat === "công nghệ") {
          cat = "Technology";
        }
        return { ...skill, category: cat };
      });

      const payload = {
        id: parsedData.id,
        full_name: parsedData.full_name,
        summary: parsedData.summary,
        experience_years_total: parsedData.experience_years_total,
        skills: normalizedSkills,
        work_history: parsedData.work_history,
        education: parsedData.education,
        certifications: parsedData.certifications,
        seniority: parsedData.seniority || "Unknown"
      };
      await api.post("cv/finalize", payload);
      setParsedData({ ...parsedData, is_verified: true });
      const wasDirty = isDirty;
      setIsDirty(false);

      if (analysisContext) {
        const updatedContext = { ...analysisContext, suggested_skills: suggestedSkills };
        sessionStorage.setItem("analysis_context", JSON.stringify(updatedContext));
        setAnalysisContext(updatedContext);
      }

      if (wasDirty && analysisContext) {
        setShowRerunModal(true);
      } else {
        showSuccess(t("cv_save_success"));
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || t("error");
      showError(Array.isArray(msg) ? msg[0].msg : msg);
    } finally {
      setSaving(false);
    }
  }, [parsedData, t, isDirty, analysisContext, suggestedSkills, showSuccess, showError]);

  const handleFileSelect = async (selectedFile: File) => {
    const allowedExtensions = ['pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg'];
    const fileExtension = selectedFile.name.split('.').pop()?.toLowerCase();
    
    if (!fileExtension || !allowedExtensions.includes(fileExtension)) {
      showError(t('cv_file_type_error'));
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      showError(t('cv_file_size_error'));
      return;
    }
    setFile(selectedFile);
    setShowPreview(true);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus("uploading");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const resp = await api.post("cv/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const { parser_id, cv_id, status: uploadStatus, result: inlineResult, is_duplicate } = resp.data;

      if (is_duplicate && uploadStatus === "completed" && inlineResult) {
        setParsedData(inlineResult);
        setStatus("viewing");
        fetchHistory();
        return;
      }

      if (uploadStatus === "completed") {
        const detailResp = await api.get(`cv/${cv_id}`);
        setParsedData(detailResp.data);
        setStatus("viewing");
        fetchHistory();
      } else if (parser_id) {
        pollStatus(parser_id, cv_id);
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
        const resp = await api.get(`cv/status/${parserId}`);
        const { status: taskStatus, result, error_message } = resp.data;
        if (taskStatus === "completed") {
          clearInterval(interval);
          if (result) setParsedData(result);
          else {
            const detailResp = await api.get(`cv/${cvId}`);
            setParsedData(detailResp.data);
          }
          setStatus("viewing");
          fetchHistory();
        } else if (taskStatus === "failed") {
          clearInterval(interval);
          setError(error_message || t("cv_analysis_error"));
          showError(error_message || t("cv_analysis_error"));
          setStatus("idle");
        }
      } catch {
        clearInterval(interval);
        setStatus("idle");
      }
    }, POLLING_INTERVAL);
  };

  const handleGoManual = () => {
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

  const handleHistoryClick = async (item: CVHistory) => {
    if (item.status === "failed") {
      showError(item.error_message || t("cv_analysis_error"));
      return;
    }
    if (item.status !== "completed") return;
    handleLoadSpecificCV(item.id);
  };

  const handleBack = () => {
    setStatus("idle");
    setParsedData(null);
    setSelectedHistoryId(null);
    setError(null);
  };

  const skillsWithIndex = useMemo(() => 
    (parsedData?.skills || []).map((s, i) => ({ ...s, originalIndex: i })),
    [parsedData?.skills]
  );

  const filteredSuggestions = useMemo(() => {
    if (!parsedData?.skills) return [];
    return suggestedSkills.filter(s =>
      !parsedData.skills?.some(existing =>
        existing.name.toLowerCase().trim() === s.toLowerCase().trim()
      )
    );
  }, [suggestedSkills, parsedData?.skills]);

  const seniorityColor = useMemo(() => ({
    Junior: "#22c55e",
    "Mid-level": "#3b82f6",
    Senior: "#a855f7",
    Expert: "#f59e0b",
    Unknown: "#9ca3af",
  }), []);

  const sc = useMemo(() => 
    seniorityColor[parsedData?.seniority as keyof typeof seniorityColor] || "#9ca3af",
    [parsedData?.seniority, seniorityColor]
  );

  const mainContent = useMemo(() => {
    if (status !== "viewing" || !parsedData) return null;

    return (
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
                    value={realTimeName}
                    onChange={(e) => {
                      const val = e.target.value;
                      setRealTimeName(val);
                      handleUpdateBasic("full_name", val);
                    }}
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

            <div className={styles.ctaRowDesktop}>
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
              <DebouncedInput
                isTextarea
                value={parsedData.summary || ""}
                onChange={(val) => handleUpdateBasic("summary", val)}
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
              <MemoizedSkillItem 
                key={skill.originalIndex} 
                skill={skill} 
                onUpdate={handleUpdateSkill}
                onDelete={handleDeleteSkill}
                seniorityColor={seniorityColor}
                getSeniorityLabel={getSeniorityLabel}
                SKILL_LEVELS={SKILL_LEVELS}
              />
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
                <MemoizedWorkItem 
                  key={i} 
                  idx={i} 
                  work={work} 
                  onUpdate={handleUpdateWork} 
                  onDelete={handleDeleteWork} 
                />
              ))}
              <button
                onClick={() => {
                  const next = [...(parsedData.work_history || [])];
                  next.push({ position: "", company: "" });
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
                <MemoizedEduItem 
                  key={i} 
                  idx={i} 
                  edu={edu} 
                  onUpdate={handleUpdateEdu} 
                  onDelete={handleDeleteEdu} 
                />
              ))}
              <button
                onClick={() => {
                  const next = [...(parsedData.education || [])];
                  next.push({ degree: "", institution: "" });
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
                <DebouncedInput
                  type="text"
                  value={cert}
                  onChange={(val) => handleUpdateCert(i, val)}
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
                next.push("");
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
    );
  }, [
    status,
    parsedData, 
    saving, 
    showRerunModal, 
    filteredSuggestions, 
    analysisContext, 
    handleSaveMatrix, 
    handleUpdateSkill, 
    handleDeleteSkill, 
    handleManualAddSkill, 
    handleUpdateWork, 
    handleDeleteWork, 
    handleUpdateEdu, 
    handleDeleteEdu, 
    handleUpdateCert, 
    handleUpdateBasic,
    handleRerunAnalysis,
    t,
    sc,
    seniorityColor,
    realTimeName,
    skillsWithIndex,
    handleAddSuggestedSkill
  ]);

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
              {selectedHistoryId ? t("cv_processing_detail_sub") : t("cv_processing_ai_sub")}
            </p>
          </div>
        </div>
      </PageContainer>
    );
  }

  if (status === "viewing" && parsedData) {
    return (
      <PageContainer>
        <PageHeader 
          title={realTimeName || t("cv_repository_title")}
          subtitle={t("cv_processing_ai_sub")}
        >
          <button onClick={handleBack} className={styles.backBtn}>
            <ArrowLeft size={16} />
            {t("cv_back_to_history")}
          </button>
        </PageHeader>

        {/* Dedicated Mobile Fixed Footer */}
        <div className={styles.mobileFixedFooter}>
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
        {mainContent}
      </PageContainer>
    );
  }

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
          <div className={styles.uploadZone}>
            <div className={styles.uploadPanel}>
              <div className={styles.uploadGlow} />
              {showPreview && file ? (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={styles.previewWrapper}>
                  <CVPreview file={file} onConfirm={() => { setShowPreview(false); handleUpload(); }} onCancel={() => { setShowPreview(false); setFile(null); }} />
                </motion.div>
              ) : (
                <>
                  <div
                    className={cn(styles.dropZone, isDragging ? styles.dropZoneActive : styles.dropZoneIdle)}
                    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={(e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files?.[0]) handleFileSelect(e.dataTransfer.files[0]); }}
                  >
                    <div className={styles.dropZoneContent}>
                      <div className={styles.cloudIconWrapper}><UploadCloud size={48} className={styles.cloudIcon} /></div>
                      <h3 className={styles.uploadTitle}>{t("cv_dropzone_idle")}</h3>
                      <p className={styles.uploadSub}>{t("cv_dropzone_hint")}</p>
                      <label className={styles.browseBtn}>
                        {t("cv_browse_files")}
                        <input type="file" hidden accept=".pdf,.docx,.doc,.png,.jpg,.jpeg" onChange={(e) => { if (e.target.files?.[0]) handleFileSelect(e.target.files[0]); }} />
                      </label>
                    </div>
                  </div>
                  <div className={styles.manualEntryHint}>
                    <span>{t("cv_or_use")}</span>
                    <button onClick={handleGoManual} className={styles.manualLink}>{t("cv_manual_entry")}</button>
                  </div>
                  {error && <div className={styles.errorBanner}><AlertCircle size={16} />{error}</div>}
                </>
              )}
            </div>
          </div>

          <div className={styles.historyZone}>
            <div className={styles.historyHeader}>
              <h3 className={styles.historyTitle}><Clock size={20} />{t("cv_history_title")}</h3>
              <span className={styles.historyCount}>{history.length} {t("cv_files")}</span>
            </div>
            <div className={styles.historyList}>
              {history.length > 0 ? (
                history.map((item) => (
                  <div key={item.id} onClick={() => handleHistoryClick(item)} className={cn(styles.historyItem, (item.status === "completed" || item.status === "failed") ? styles.historyItemClickable : styles.historyItemDisabled, selectedHistoryId === item.id && styles.historyItemActive)}>
                    <div className={styles.historyIcon}><FileText size={20} /></div>
                    <div className={styles.historyInfo}>
                      <div className={styles.historyName}>{item.full_name || item.file_name || t("cv_candidate_name_placeholder")}</div>
                      <div className={styles.historyMeta}>{new Date(item.created_at).toLocaleDateString(language === 'vi' ? "vi-VN" : "en-US")}</div>
                    </div>
                    <div className={cn(styles.historyStatus, styles[item.status])}>
                      {item.status === "completed" && <CheckCircle2 size={16} />}
                      {item.status === "processing" && <Loader2 size={16} className={styles.animateSpin} />}
                      {item.status === "failed" && <AlertCircle size={16} />}
                    </div>
                  </div>
                ))
              ) : (
                <div className={styles.emptyHistory}><FileText size={40} className={styles.emptyIcon} /><p>{t("cv_no_history")}</p></div>
              )}
            </div>
          </div>
        </div>
      </PageContainer>
    </AuthGuard>
  );
};

// --- Optimized Sub-components ---
const MemoizedSkillItem = memo(({ skill, onUpdate, onDelete, seniorityColor, getSeniorityLabel, SKILL_LEVELS }: any) => {
  const { t } = useLanguage();
  return (
    <div className={styles.skillItem}>
      <div className={styles.skillMain}>
        <DebouncedInput type="text" value={skill.name} onChange={(val) => onUpdate(skill.originalIndex, "name", val)} className={styles.skillNameInput} maxLength={50} placeholder={t("cv_skill_default_name")} />
        <div className={styles.skillMeta}>
          <div className={styles.skillExpGroup}>
            <Clock size={12} />
            <input type="number" step="0.5" value={skill.experience_years} onChange={(e) => onUpdate(skill.originalIndex, "experience_years", e.target.value)} className={styles.editInput} min={0} max={60} />
            <span>{t("cv_years_short")}</span>
          </div>
          <CustomDropdown value={getSeniorityLabel(skill.level)} options={SKILL_LEVELS.map(getSeniorityLabel)} onChange={(val: string) => {
            const key = SKILL_LEVELS.find((k: string) => getSeniorityLabel(k) === val);
            if (key) onUpdate(skill.originalIndex, "level", key);
          }} className={styles.skillLevelSelect} style={{ color: seniorityColor[skill.level as keyof typeof seniorityColor] }} />
        </div>
      </div>
      <button onClick={() => onDelete(skill.originalIndex)} className={styles.deleteSkillBtn}><Trash2 size={14} /></button>
    </div>
  );
});

const MemoizedWorkItem = memo(({ idx, work, onUpdate, onDelete }: any) => {
  const { t } = useLanguage();
  return (
    <div className={styles.timelineItem}>
      <div className={styles.timelineDot} />
      <div className={styles.timelineContent}>
        <div className={styles.timelineHeader}>
          <DebouncedInput type="text" value={work.position} onChange={(val) => onUpdate(idx, "position", val)} className={styles.timelineInput} placeholder={t("cv_position_placeholder")} maxLength={100} />
          <div className={styles.timelineActions}>
            <div className={styles.timelineDuration}>
              <input type="number" step="0.5" value={work.duration_years || 0} onChange={(e) => onUpdate(idx, "duration_years", e.target.value)} className={styles.timelineSmallInput} />
              <span>{t("cv_years_short")}</span>
            </div>
            <button onClick={() => onDelete(idx)} className={styles.itemDeleteBtn}><Trash2 size={14} /></button>
          </div>
        </div>
        <DebouncedInput type="text" value={work.company} onChange={(val) => onUpdate(idx, "company", val)} className={styles.timelineSubInput} placeholder={t("cv_company_placeholder")} maxLength={100} />
        <DebouncedInput isTextarea value={work.description || ""} onChange={(val) => onUpdate(idx, "description", val)} className={styles.timelineDescTextarea} placeholder={t("cv_work_desc_placeholder")} maxLength={1000} />
      </div>
    </div>
  );
});

const MemoizedEduItem = memo(({ idx, edu, onUpdate, onDelete }: any) => {
  const { t } = useLanguage();
  return (
    <div className={styles.timelineItem}>
      <div className={styles.timelineDot} />
      <div className={styles.timelineContent}>
        <div className={styles.timelineHeader}>
          <DebouncedInput type="text" value={edu.degree} onChange={(val) => onUpdate(idx, "degree", val)} className={styles.timelineInput} placeholder={t("cv_degree_placeholder")} maxLength={100} />
          <div className={styles.timelineActions}>
            <div className={styles.timelineDuration}>
              <input type="number" value={edu.year || new Date().getFullYear()} onChange={(e) => onUpdate(idx, "year", e.target.value)} className={styles.timelineSmallInput} />
            </div>
            <button onClick={() => onDelete(idx)} className={styles.itemDeleteBtn}><Trash2 size={14} /></button>
          </div>
        </div>
        <DebouncedInput type="text" value={edu.institution} onChange={(val) => onUpdate(idx, "institution", val)} className={styles.timelineSubInput} placeholder={t("cv_institution_placeholder")} maxLength={100} />
      </div>
    </div>
  );
});

MemoizedSkillItem.displayName = "MemoizedSkillItem";
MemoizedWorkItem.displayName = "MemoizedWorkItem";
MemoizedEduItem.displayName = "MemoizedEduItem";

export default UserCVPage;

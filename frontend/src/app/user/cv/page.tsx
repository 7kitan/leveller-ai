"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
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
  skills: { name: string; category: string; experience_years: number; level?: string }[];
  summary: string;
  full_name?: string;
  experience_years_total?: number;
  seniority?: string;
  is_ocr?: boolean;
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
    if (token) fetchHistory();
  }, [token]);

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

  const handleManualAddSkill = () => {
    if (!parsedData) return;
    const newSkill = {
      name: "New Skill",
      category: "Technology",
      experience_years: 1,
    };
    setParsedData({
      ...parsedData,
      skills: [...(parsedData.skills || []), newSkill],
    });
  };

  const handleUpdateExperience = (idx: number, years: number) => {
    if (!parsedData) return;
    const nextSkills = [...(parsedData.skills || [])];
    if (nextSkills[idx]) {
      nextSkills[idx] = { ...nextSkills[idx], experience_years: years };
      setParsedData({ ...parsedData, skills: nextSkills });
    }
  };

  const handleDeleteSkill = (idx: number) => {
    if (!parsedData) return;
    setParsedData({
      ...parsedData,
      skills: (parsedData.skills || []).filter((_, i) => i !== idx),
    });
  };

  const handleSaveMatrix = async () => {
    setSaving(true);
    try {
      await axios.post("/api/cv/finalize", parsedData, {
        headers: { Authorization: `Bearer ${token}` },
      });
      alert("Portfolio đã được cập nhật thành công!");
    } catch {
      alert("Lỗi khi lưu Portfolio.");
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
    const groupedSkills = (parsedData.skills || []).reduce((acc: any, skill) => {
      const cat = skill.category || "Uncategorized";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(skill);
      return acc;
    }, {});

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

        {/* ── Result Header ───────────────────────────────────────────── */}
        <div className={styles.resultHeader}>
          <div className={styles.resultHeaderGroup}>
            <div className={styles.userBasicInfo}>
              <div className={styles.avatar}>
                <FileText size={32} />
              </div>
              <div>
                <div className={styles.nameRow}>
                  <h1 className={styles.userName}>
                    {parsedData.full_name || "Parsed Candidate"}
                  </h1>
                  {parsedData.seniority && (
                    <span
                      className={styles.seniorityBadge}
                      style={{ color: sc, borderColor: sc + "40", background: sc + "12" }}
                    >
                      {parsedData.seniority}
                    </span>
                  )}
                </div>
                <div className={styles.metaRow}>
                  <div className={styles.userExpBadge}>
                    <Clock size={13} />
                    {parsedData.experience_years_total ?? 0} năm kinh nghiệm
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
              <button onClick={handleBack} className={styles.reloadBtn}>
                Tải lại CV
              </button>
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

          {parsedData.summary && (
            <div className={styles.summarySection}>
              <h4 className={styles.summaryTitle}>Executive Insight</h4>
              <p className={styles.summaryText}>&ldquo;{parsedData.summary}&rdquo;</p>
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
                    {groupedSkills[cat].map((skill: any, idx: number) => {
                      const globalIdx = (parsedData.skills || []).findIndex(
                        (s) => s.name === skill.name
                      );
                      return (
                        <div key={idx} className={styles.skillItem}>
                          <span className={styles.skillName}>{skill.name}</span>
                          <input
                            type="number"
                            value={skill.experience_years ?? 0}
                            onChange={(e) =>
                              handleUpdateExperience(globalIdx, parseInt(e.target.value) || 0)
                            }
                            className={styles.editInput}
                            min={0}
                          />
                          <span className={styles.yrsLabel}>YRS</span>
                          <button
                            onClick={() => handleDeleteSkill(globalIdx)}
                            className={styles.deleteSkillBtn}
                          >
                            <X size={13} />
                          </button>
                        </div>
                      );
                    })}
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
            {/* Work History */}
            {(parsedData.work_history || []).length > 0 && (
              <div className={styles.sectionCard}>
                <h3 className={styles.sectionTitle}>
                  <Briefcase size={18} className={styles.sectionTitleIcon} />
                  KINH NGHIỆM LÀM VIỆC
                </h3>
                <div className={styles.timelineList}>
                  {parsedData.work_history!.map((w, idx) => (
                    <div key={idx} className={styles.timelineItem}>
                      <div className={styles.timelineDot} />
                      <div className={styles.timelineContent}>
                        <div className={styles.timelineHeader}>
                          <span className={styles.timelinePosition}>{w.position}</span>
                          {w.duration_years ? (
                            <span className={styles.timelineDuration}>
                              {w.duration_years} năm
                            </span>
                          ) : null}
                        </div>
                        <div className={styles.timelineCompany}>{w.company}</div>
                        {w.description && (
                          <p className={styles.timelineDesc}>{w.description}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Education */}
            {(parsedData.education || []).length > 0 && (
              <div className={styles.sectionCard}>
                <h3 className={styles.sectionTitle}>
                  <GraduationCap size={18} className={styles.sectionTitleIcon} />
                  HỌC VẤN
                </h3>
                <div className={styles.timelineList}>
                  {parsedData.education!.map((e, idx) => (
                    <div key={idx} className={styles.timelineItem}>
                      <div className={styles.timelineDot} />
                      <div className={styles.timelineContent}>
                        <div className={styles.timelineHeader}>
                          <span className={styles.timelinePosition}>{e.degree}</span>
                          {e.year && (
                            <span className={styles.timelineDuration}>{e.year}</span>
                          )}
                        </div>
                        <div className={styles.timelineCompany}>{e.institution}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Certifications */}
            {(parsedData.certifications || []).length > 0 && (
              <div className={styles.sectionCard}>
                <h3 className={styles.sectionTitle}>
                  <Award size={18} className={styles.sectionTitleIcon} />
                  CHỨNG CHỈ
                </h3>
                <div className={styles.certList}>
                  {parsedData.certifications!.map((cert, idx) => (
                    <div key={idx} className={styles.certItem}>
                      <BadgeCheck size={16} className={styles.certIcon} />
                      {cert}
                    </div>
                  ))}
                </div>
              </div>
            )}
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
              KHO HỒ SƠ CÁ NHÂN.
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
                <div className={styles.errorBox}>
                  <AlertCircle size={18} className={styles.errorIcon} />
                  {error}
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
                          ? `Đã phân tích · ${new Date(
                              item.created_at
                            ).toLocaleDateString("vi-VN")}`
                          : item.status === "failed"
                          ? "Phân tích thất bại"
                          : `Đang xử lý · ${new Date(
                              item.created_at
                            ).toLocaleDateString("vi-VN")}`}
                      </p>
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

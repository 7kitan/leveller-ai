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
  Cpu,
  Sparkles,
  Award,
  ChevronRight,
  Save,
  Plus,
  Trash2
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./user-cv.module.css";
import { motion, AnimatePresence } from "framer-motion";

interface CVHistory {
  id: string;
  status: 'processing' | 'completed' | 'failed';
  created_at: string;
  file_name: string;
}

interface ParsedCV {
  id: string;
  skills: { name: string; category: string; experience_years: number }[];
  summary: string;
  user_info: {
    full_name: string;
    total_exp_years: number;
  };
}

const UserCVPage = () => {
  const { token } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [history, setHistory] = useState<CVHistory[]>([]);
  const [status, setStatus] = useState<'idle' | 'uploading' | 'processing' | 'viewing'>('idle');
  const [parsedData, setParsedData] = useState<ParsedCV | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchHistory = async () => {
    try {
      const resp = await axios.get("/api/analysis/cv/history", {
        headers: { Authorization: `Bearer ${token}` }
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
    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await axios.post("/api/analysis/cv/upload", formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data" 
        }
      });
      const parserId = resp.data.parser_id;
      pollStatus(parserId);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Lỗi khi tải file. Vui lòng thử lại.");
      setStatus("idle");
    }
  };

  const pollStatus = async (parserId: string) => {
    setStatus("processing");
    const interval = setInterval(async () => {
      try {
        const resp = await axios.get(`/api/analysis/cv/status/${parserId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (resp.data.status === "completed") {
          clearInterval(interval);
          setParsedData(resp.data.result);
          setStatus("viewing");
          fetchHistory();
        } else if (resp.data.status === "failed") {
          clearInterval(interval);
          setError("AI gặp sự cố khi bóc tách hồ sơ này.");
          setStatus("idle");
        }
      } catch (err) {
        clearInterval(interval);
        setStatus("idle");
      }
    }, 3000);
  };

  const handleManualAddSkill = () => {
      if (!parsedData) return;
      const newSkill = { name: "New Skill", category: "Technology", experience_years: 1 };
      setParsedData({
          ...parsedData,
          skills: [...parsedData.skills, newSkill]
      });
  };

  const handleUpdateExperience = (idx: number, years: number) => {
      if (!parsedData) return;
      const nextSkills = [...parsedData.skills];
      nextSkills[idx].experience_years = years;
      setParsedData({ ...parsedData, skills: nextSkills });
  };

  const handleDeleteSkill = (idx: number) => {
      if (!parsedData) return;
      setParsedData({
          ...parsedData,
          skills: parsedData.skills.filter((_, i) => i !== idx)
      });
  };

  const handleSaveMatrix = async () => {
      setSaving(true);
      try {
          await axios.post("/api/analysis/cv/finalize", parsedData, {
              headers: { Authorization: `Bearer ${token}` }
          });
          alert("Portfolio đã được cập nhật thành công!");
      } catch (err) {
          alert("Lỗi khi lưu Portfolio.");
      } finally {
          setSaving(false);
      }
  };

  if (status === "processing") {
    return (
      <div className={styles.processingPanel}>
        <div className={styles.spinnerWrapper}>
          <div className={styles.spinnerRing}></div>
          <Cpu size={48} className={styles.pulseIcon} />
        </div>
        <div>
          <h2 style={{ fontSize: "2rem", fontWeight: 900, color: "white", fontStyle: "italic", marginBottom: "1rem" }}>ENGINEERING KNOWLEDGE...</h2>
          <p style={{ color: "rgba(255,255,255,0.4)", fontWeight: 500 }}>AI đang ánh xạ hồ sơ của bạn vào Global Taxonomy Graph.</p>
        </div>
      </div>
    );
  }

  if (status === "viewing" && parsedData) {
    const groupedSkills = parsedData.skills.reduce((acc: any, skill) => {
      const cat = skill.category || "Uncategorized";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(skill);
      return acc;
    }, {});

    return (
      <div className={styles.stackSection}>
        {/* Result Header */}
        <div className={styles.resultHeader}>
             <div className={styles.resultHeaderGroup}>
                <div className={styles.userBasicInfo}>
                    <div className={styles.avatar}>
                        <FileText size={40} />
                    </div>
                    <div>
                        <h1 className={styles.userName}>{parsedData.user_info.full_name || "Parsed Candidate"}</h1>
                        <div className={styles.metaRow}>
                           <div className={styles.userExpBadge}>
                              <Clock size={14} />
                              {parsedData.user_info.total_exp_years} Years Experience
                           </div>
                           <div className={styles.secureBadge} style={{ background: "rgba(129, 140, 248, 0.1)", borderColor: "rgba(129, 140, 248, 0.2)" }}>
                              <ShieldCheck size={14} style={{ color: "#818cf8" }} />
                              <span style={{ fontSize: "10px", fontWeight: 900, color: "#818cf8", textTransform: "uppercase" }}>AI Verified Portfolio</span>
                           </div>
                        </div>
                    </div>
                </div>

                <div className={styles.ctaRow}>
                    <button 
                        onClick={() => setStatus("idle")} 
                        style={{ fontSize: "10px", fontWeight: 900, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.2em" }}
                    >
                        Tải lại CV
                    </button>
                    <button 
                        onClick={handleSaveMatrix}
                        disabled={saving}
                        className={styles.uploadBtn}
                        style={{ marginTop: 0, padding: "1rem 2.5rem" }}
                    >
                        {saving ? <Loader2 size={18} className={styles.animateSpin} /> : <Save size={18} />}
                        LƯU VÀO HỆ THỐNG
                    </button>
                </div>
             </div>

             <div className={styles.summarySection}>
                <h4 className={styles.summaryTitle}>Executive Insight</h4>
                <p className={styles.summaryText}>&ldquo;{parsedData.summary}&rdquo;</p>
             </div>
        </div>

        {/* Matrix Grid */}
        <div className={styles.matrixGrid}>
           {/* Main Skills Matrix */}
           <div className={styles.matrixPanel}>
              <h2 className={styles.matrixTitle}>
                 <Sparkles size={24} style={{ color: "#818cf8", marginRight: "1rem" }} />
                 COMPETENCY MATRIX
              </h2>

              {Object.keys(groupedSkills).map((cat) => (
                <div key={cat} className={styles.catGroup}>
                   <h5 className={styles.catLabel}>{cat}</h5>
                   <div className={styles.flexWrapGap}>
                      {groupedSkills[cat].map((skill: any, idx: number) => {
                         const globalIdx = parsedData.skills.findIndex(s => s.name === skill.name);
                         return (
                            <div key={idx} className={styles.skillItem}>
                               <span style={{ marginRight: "0.75rem" }}>{skill.name}</span>
                               <input 
                                  type="number" 
                                  value={skill.experience_years} 
                                  onChange={(e) => handleUpdateExperience(globalIdx, parseInt(e.target.value))}
                                  className={styles.editInput}
                                  min={0}
                                />
                                <span style={{ marginLeft: "0.5rem", fontSize: "10px", opacity: 0.3 }}>YRS</span>
                                <button 
                                    onClick={() => handleDeleteSkill(globalIdx)}
                                    style={{ marginLeft: "1rem", color: "rgba(244, 63, 94, 0.4)" }}
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                         );
                      })}
                   </div>
                </div>
              ))}

              <button onClick={handleManualAddSkill} className={styles.addSkillBtn}>
                 <Plus size={16} /> Bổ sung kĩ năng thủ công
              </button>
           </div>

           {/* Sidebar Tools */}
           <div className={styles.verifyPanel}>
              <h4 style={{ fontSize: "11px", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.2em", color: "#06b6d4" }}>Portfolio Scoring</h4>
              <div className={styles.stackTight}>
                 <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                    <span style={{ fontSize: "10px", fontWeight: 700, opacity: 0.4 }}>Taxonomy Fit</span>
                    <span style={{ fontSize: "2rem", fontWeight: 900, fontStyle: "italic", color: "white" }}>92.4%</span>
                 </div>
                 <div style={{ width: "100%", height: "2px", background: "rgba(255,255,255,0.05)" }}>
                    <div style={{ width: "92.4%", height: "100%", background: "#06b6d4" }} />
                 </div>
              </div>

              <div style={{ marginTop: "2rem", padding: "1.5rem", background: "rgba(255,255,255,0.02)", borderRadius: "1.5rem", border: "1px solid rgba(255,255,255,0.05)" }}>
                 <p style={{ fontSize: "12px", color: "rgba(255,255,255,0.4)", lineHeight: "1.6" }}>
                    Các kĩ năng được bóc tách sẽ được sử dụng để chạy Gap Analysis trên 5,000+ vị trí công việc.
                 </p>
                 <button 
                   onClick={handleSaveMatrix}
                   className={styles.uploadBtn} 
                   style={{ width: "100%", marginTop: "1.5rem", padding: "1rem" }}
                 >
                    {saving ? <Loader2 size={16} className={styles.animateSpin} /> : <CheckCircle2 size={24} />}
                 </button>
              </div>
           </div>
        </div>
      </div>
    );
  }

  return (
    <AuthGuard requireRole="user">
      <div className={styles.pageRoot}>
        {/* Header Section */}
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>
              <Zap size={40} style={{ color: "#818cf8" }} />
              KHO HỒ SƠ CÁ NHÂN.
            </h1>
            <p className={styles.subtitle}>Tải lên CV (PDF/Images) để AI tự động trích xuất và tối ưu lộ trình kĩ năng.</p>
          </div>
          <div className={styles.secureBadge}>
            <ShieldCheck size={18} style={{ color: "#10b981" }} />
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
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0]);
                }}
              >
                <div className={cn(styles.uploadIcon, (file || isDragging) && styles.uploadIconActive)}>
                  <UploadCloud size={48} />
                </div>
                
                <div style={{ textAlign: "center" }}>
                   <h3 style={{ fontSize: "1.5rem", fontWeight: 900, color: "white", marginBottom: "0.5rem" }}>
                     {file ? file.name : "Kéo thả hồ sơ vào đây"}
                   </h3>
                   <p style={{ color: "rgba(255,255,255,0.3)", fontWeight: 500 }}>Chấp nhận định dạng .pdf, .png, .jpg (Tối đa 10MB)</p>
                </div>

                <div className={styles.loaderWrapper}>
                  <input
                    type="file"
                    className="hidden"
                    id="cv-upload"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    accept=".pdf,image/*"
                  />
                  <label htmlFor="cv-upload" style={{ cursor: "pointer", color: "#818cf8", fontWeight: 900, textTransform: "uppercase", fontSize: "10px", letterSpacing: "0.15em", textDecoration: "underline" }}>
                    Hoặc duyệt từ máy tính
                  </label>
                </div>
              </div>

              {error && (
                <div className={styles.errorBox}>
                  <AlertCircle size={18} style={{ marginRight: "0.75rem" }} />
                  {error}
                </div>
              )}

              <button 
                onClick={handleUpload}
                disabled={!file || status === "uploading"}
                className={styles.uploadBtn}
              >
                {status === "uploading" ? <Loader2 size={20} className={styles.animateSpin} /> : <Sparkles size={20} />}
                {status === "uploading" ? "AI ĐANG PHÂN TÍCH..." : "BẮT ĐẦU TRÍCH XUẤT AI"}
              </button>
            </div>
          </div>

          {/* Right: History */}
          <div className={styles.historySection}>
             <div className={styles.historyTitle}>
                HISTORY LOGS
                <div style={{ flex: 1, height: "1px", background: "rgba(255,255,255,0.05)" }} />
             </div>

             <div className={styles.historyList}>
                {history.map((item) => (
                   <div key={item.id} className={styles.historyItem}>
                      <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
                        <div className={cn(
                            styles.historyIcon,
                            item.status === 'completed' ? styles.historyIconCompleted : styles.historyIconProcessing
                        )}>
                           {item.status === 'completed' ? <CheckCircle2 size={24} /> : <Loader2 size={24} className={styles.animateSpin} />}
                        </div>
                        <div>
                           <h4 style={{ fontWeight: 900, color: "white" }}>{item.file_name}</h4>
                           <p style={{ fontSize: "10px", fontWeight: 900, color: "rgba(255,255,255,0.2)", textTransform: "uppercase", marginTop: "0.25rem" }}>
                             Processed on {new Date(item.created_at).toLocaleDateString()}
                           </p>
                        </div>
                      </div>
                      <ChevronRight size={18} style={{ color: "rgba(255,255,255,0.1)" }} />
                   </div>
                ))}
                {history.length === 0 && (
                    <div style={{ padding: "4rem 0", textAlign: "center", opacity: 0.1 }}>
                        <Clock size={48} style={{ margin: "0 auto 1.5rem" }} />
                        <p style={{ fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.2em" }}>Chưa có lịch sử</p>
                    </div>
                )}
             </div>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
};

export default UserCVPage;

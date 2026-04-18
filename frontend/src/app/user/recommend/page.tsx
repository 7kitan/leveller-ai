"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import {
  TrendingUp,
  Target,
  RefreshCcw,
  BarChart3,
  Globe,
  CheckCircle2,
  ChevronLeft,
  Loader2,
  BookOpen,
  Award,
  Clock,
  Zap,
  Layers,
  AlertCircle,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer 
} from 'recharts';
import styles from "./user-recommend.module.css";

/* ── Types ─────────────────────────────────────────────────────────────── */
interface CourseRec {
  course_id: string;
  gap_skill?: string;
  gap_severity?: string;
  gap_learning_path?: string;
  gap_estimated_months?: number;
  is_critical?: boolean;
  title: string;
  platform: string;
  url: string;
  level: string;
  provider: string;
  duration_hours: number;
  is_certification: boolean;
  cost_usd: number;
  tags: string[];
  similarity: number;
  rank_score?: number;
  selection_reason: string;
}

interface SkillGap {
  skill: string;
  required_level?: string;
  severity: string;
  is_critical?: boolean;
  estimated_months: number;
  learning_path?: string;
  gap_type?: string;
  learning_effort?: string;
}

interface GapResult {
  overall_match_pct: number;
  overall_assessment: string;
  strengths: string[];
  weaknesses: string[];
  skill_gaps: SkillGap[];
  gap_summary?: any;
  match_breakdown: Record<string, number>;
  transferable_insights: string[];
  jd_context?: string;
  top_gaps?: SkillGap[];
  course_recommendations: CourseRec[];
  career_roadmap?: {
    stages: { 
      stage: number; 
      focus: string; 
      duration_weeks: number;
      skills_acquired?: string[];
      courses_taken?: string[];
      milestones?: { week: number; milestone: string }[];
    }[];
    total_weeks: number;
    total_hours: number;
    summary: string;
  };
}

/* ── Helpers ────────────────────────────────────────────────────────────── */
function severityColor(sev: string) {
  const map: Record<string, string> = {
    HIGH: "#f43f5e",
    MEDIUM: "#f59e0b",
    LOW: "#22c55e",
  };
  return map[sev?.toUpperCase()] || "#9ca3af";
}

function levelColor(level: string) {
  const map: Record<string, string> = {
    Beginner: "#22c55e",
    Intermediate: "#3b82f6",
    "Mid-level": "#a855f7",
    Senior: "#f59e0b",
    Expert: "#f43f5e",
  };
  return map[level] || "#9ca3af";
}

const UserRecommendPage = () => {
  const { token } = useAuth();
  const router = useRouter();

  const [gapResult, setGapResult] = useState<GapResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"gaps" | "courses" | "roadmap">("gaps");

  /* ── Load gap result ─────────────────────────────────────────────────── */
  useEffect(() => {
    if (!token) return;

    // 1. Try sessionStorage first (fresh from analysis page)
    try {
      const stored = sessionStorage.getItem("gap_analysis_result");
      if (stored) {
        const parsed = JSON.parse(stored) as GapResult;
        console.log("[RECOMMEND] Loaded from sessionStorage:", parsed);
        setGapResult(parsed);
        sessionStorage.removeItem("gap_analysis_result");
        setLoading(false);
        return;
      }
    } catch (e) {
      console.warn("[RECOMMEND] sessionStorage parse failed:", e);
    }

    // 2. Fallback: fetch from backend latest analysis
    axios
      .get("/api/analysis/user/latest", {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((r) => {
        console.log("[RECOMMEND] Loaded from /analysis/user/latest");
        setGapResult(r.data as GapResult);
      })
      .catch((e) => {
        console.error("[RECOMMEND] No analysis found:", e);
        setError(
          "Không tìm thấy kết quả phân tích. Vui lòng chạy Gap Analysis trước."
        );
      })
      .finally(() => setLoading(false));
  }, [token]);

  /* ── Refresh from backend ──────────────────────────────────────────────── */
  const fetchLatest = () => {
    setLoading(true);
    setError("");
    axios
      .get("/api/analysis/user/latest", {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((r) => setGapResult(r.data as GapResult))
      .catch((e) => {
        console.error("[RECOMMEND] Refresh failed:", e);
        setError("Không thể tải lại kết quả phân tích.");
      })
      .finally(() => setLoading(false));
  };

  /* ── Loading state ────────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className={styles.loadingWrapper}>
        <div className={styles.spinner} />
        <p className={styles.loadingText}>Đang tải kết quả phân tích...</p>
      </div>
    );
  }

  /* ── Error state ──────────────────────────────────────────────────────── */
  if (error && !gapResult) {
    return (
      <AuthGuard>
        <div className={styles.pageRoot}>
          <div className={styles.header}>
            <button onClick={() => router.push("/user/jobs")} className={styles.backLink}>
              <ChevronLeft size={16} />
              Quay lại trang việc làm
            </button>
          </div>
          <div className={styles.emptyState}>
            <AlertCircle size={48} className={styles.emptyIcon} />
            <h3 className={styles.emptyTitle}>{error}</h3>
            <p className={styles.emptySub}>
              Vui lòng chọn một CV đã hoàn tất và một vị trí công việc để chạy phân tích gap.
            </p>
            <button
              onClick={() => router.push("/user/jobs")}
              className={styles.startBtn}
            >
              <Zap size={16} />
              Bắt đầu phân tích
            </button>
          </div>
        </div>
      </AuthGuard>
    );
  }

  if (!gapResult) return null;

  const { 
    overall_match_pct, 
    overall_assessment, 
    skill_gaps = [], 
    course_recommendations = [], 
    career_roadmap,
    strengths = [],
    weaknesses = [],
    match_breakdown = {}
  } = gapResult;

  const highGaps = skill_gaps.filter((g) => g.severity === "HIGH");
  const mediumGaps = skill_gaps.filter((g) => g.severity === "MEDIUM");
  const lowGaps = skill_gaps.filter((g) => g.severity === "LOW");

  const totalHours = course_recommendations.reduce((s, c) => s + (c.duration_hours || 0), 0);
  const certCourses = course_recommendations.filter((c) => c.is_certification);
  const freeCourses = course_recommendations.filter((c) => !c.is_certification && (c.cost_usd || 0) === 0);

  /* ── Tabs ──────────────────────────────────────────────────────────────── */
  const tabs = [
    { key: "gaps", label: "Khoảng cách kỹ năng", icon: Layers, count: skill_gaps.length },
    { key: "courses", label: "Khóa học đề xuất", icon: BookOpen, count: course_recommendations.length },
    { key: "roadmap", label: "Lộ trình học tập", icon: Target, count: career_roadmap?.stages?.length ?? 0 },
  ] as const;

  return (
    <AuthGuard>
      <div className={styles.pageRoot}>

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div className={styles.header}>
          <div className={styles.titleSection}>
            <div className={styles.badge}>
              <Globe size={12} />
              <span className={styles.badgeLabel}>Career Genome Results</span>
            </div>
            <h1 className={styles.titleMain}>
              KẾT QUẢ{" "}
              <span className={styles.gradientText}>PHÂN TÍCH.</span>
            </h1>
            <p className={styles.headerSubtitle}>
              Dựa trên phân tích gap — đây là lộ trình tối ưu để bạn đạt được vị trí mong muốn.
            </p>
          </div>
          <div className={styles.controlBar}>
            <button onClick={fetchLatest} className={styles.refreshBtn}>
              <RefreshCcw size={16} />
              Làm mới
            </button>
            <button onClick={() => router.push("/user/jobs")} className={styles.refreshBtn}>
              <ChevronLeft size={16} />
              Chọn vị trí khác
            </button>
          </div>
        </div>

        {/* ── Match Score Banner ───────────────────────────────────────────── */}
        <div className={styles.matchBanner}>
          <div className={styles.matchScoreBlock}>
            <span className={styles.matchScore}>{overall_match_pct ?? 0}%</span>
            <span className={styles.matchLabel}>Độ phù hợp hiện tại</span>
          </div>
          
          {/* Radar Chart Section */}
          <div className={styles.radarSection}>
             <ResponsiveContainer width="100%" height={200}>
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={
                  Object.keys(match_breakdown).length > 0 ? Object.entries(match_breakdown).map(([name, value]) => ({
                    subject: name,
                    A: value,
                    fullMark: 100,
                  })) : [
                    { subject: 'Technical', A: 0, fullMark: 100 },
                    { subject: 'Experience', A: 0, fullMark: 100 },
                    { subject: 'Soft Skills', A: 0, fullMark: 100 },
                    { subject: 'Education', A: 0, fullMark: 100 },
                    { subject: 'Domain', A: 0, fullMark: 100 },
                  ]
                }>
                  <PolarGrid stroke="#ffffff20" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar
                    name="Match"
                    dataKey="A"
                    stroke="#10b981"
                    fill="#10b981"
                    fillOpacity={0.5}
                  />
                </RadarChart>
              </ResponsiveContainer>
          </div>

          <div className={styles.matchRight}>
            <span className={styles.matchAssessment}>&ldquo;{overall_assessment || "Chưa có đánh giá tổng quan."}&rdquo;</span>
            <div className={styles.matchStats}>
              <div className={styles.matchStat}>
                <span className={styles.matchStatValue}>{skill_gaps.length}</span>
                <span className={styles.matchStatLabel}>Kỹ năng cần bổ sung</span>
              </div>
              <div className={styles.matchStat}>
                <span className={styles.matchStatValue}>{course_recommendations.length}</span>
                <span className={styles.matchStatLabel}>Khóa học gợi ý</span>
              </div>
              <div className={styles.matchStat}>
                <span className={styles.matchStatValue}>{totalHours.toFixed(1)}h</span>
                <span className={styles.matchStatLabel}>Tổng thời lượng</span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Strengths & Weaknesses ───────────────────────────────────────── */}
        <div className={styles.gridTwo}>
          <div className={styles.infoCard}>
            <h3 className={styles.infoTitle}>
              <CheckCircle2 size={18} className={styles.successIcon} />
              Điểm mạnh nổi bật
            </h3>
            <ul className={styles.infoList}>
              {strengths.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
              {strengths.length === 0 && <li>Đang phân tích dữ liệu...</li>}
            </ul>
          </div>
          <div className={styles.infoCard}>
            <h3 className={styles.infoTitle}>
              <AlertCircle size={18} className={styles.warningIcon} />
              Điểm cần cải thiện
            </h3>
            <ul className={styles.infoList}>
              {weaknesses.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
              {weaknesses.length === 0 && <li>Tất cả kỹ năng đều ổn.</li>}
            </ul>
          </div>
        </div>

        {/* ── Transferable Insights ────────────────────────────────────────── */}
        {(gapResult.transferable_insights || []).length > 0 && (
          <div className={styles.insightBox}>
            <h4 className={styles.insightTitle}>
              <Sparkles size={16} />
              Gợi ý chuyển đổi (Transferable Skills)
            </h4>
            <div className={styles.insightContent}>
              {gapResult.transferable_insights.map((ins, i) => (
                <div key={i} className={styles.insightItem}>
                  {ins}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Severity Summary ────────────────────────────────────────────── */}
        <div className={styles.severityRow}>
          <div className={styles.severityPill} style={{ color: severityColor("HIGH"), borderColor: severityColor("HIGH") + "40", background: severityColor("HIGH") + "12" }}>
            <AlertCircle size={14} />
            Cao ({highGaps.length})
          </div>
          <div className={styles.severityPill} style={{ color: severityColor("MEDIUM"), borderColor: severityColor("MEDIUM") + "40", background: severityColor("MEDIUM") + "12" }}>
            <Target size={14} />
            Trung bình ({mediumGaps.length})
          </div>
          <div className={styles.severityPill} style={{ color: severityColor("LOW"), borderColor: severityColor("LOW") + "40", background: severityColor("LOW") + "12" }}>
            <CheckCircle2 size={14} />
            Thấp ({lowGaps.length})
          </div>
        </div>

        {/* ── Tab Nav ──────────────────────────────────────────────────────── */}
        <div className={styles.tabBar}>
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(styles.tab, activeTab === tab.key && styles.tabActive)}
            >
              <tab.icon size={16} />
              {tab.label}
              <span className={styles.tabCount}>{tab.count}</span>
            </button>
          ))}
        </div>

        {/* ── Tab: Skill Gaps ────────────────────────────────────────────── */}
        {activeTab === "gaps" && (
          <div className={styles.gapGrid}>
            {skill_gaps.length === 0 ? (
              <div className={styles.emptySection}>
                <CheckCircle2 size={40} className={styles.emptyIcon} />
                <p>Không có khoảng cách kỹ năng nào được phát hiện!</p>
              </div>
            ) : (
              skill_gaps.map((gap, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className={styles.gapCard}
                  style={{ borderColor: severityColor(gap.severity) + "30" }}
                >
                  <div className={styles.gapCardTop}>
                    <span className={styles.gapSkillName}>{gap.skill}</span>
                    <span
                      className={styles.gapSeverityBadge}
                      style={{
                        color: severityColor(gap.severity),
                        background: severityColor(gap.severity) + "12",
                        borderColor: severityColor(gap.severity) + "30",
                      }}
                    >
                      {gap.severity}
                    </span>
                  </div>
                  <div className={styles.gapCardMeta}>
                    {gap.required_level && (
                      <span className={styles.gapLevel}>
                         Level: <b>{gap.required_level}</b>
                      </span>
                    )}
                    <span className={styles.gapMonths}>
                      <Clock size={12} />
                      ~{gap.estimated_months ?? 1} tháng
                    </span>
                    {gap.gap_type && <span className={styles.gapType}>{gap.gap_type}</span>}
                    {gap.is_critical && <span className={styles.criticalTag}>Critical</span>}
                  </div>

                  {gap.learning_path && (
                    <div className={styles.gapLearningPath}>
                       <Sparkles size={12} className={styles.pathIcon} />
                       <p>{gap.learning_path}</p>
                    </div>
                  )}
                </motion.div>
              ))
            )}
          </div>
        )}

        {/* ── Tab: Courses ─────────────────────────────────────────────────── */}
        {activeTab === "courses" && (
          <div className={styles.courseGrid}>
            {course_recommendations.length === 0 ? (
              <div className={styles.emptySection}>
                <BookOpen size={40} className={styles.emptyIcon} />
                <p>Chưa có khóa học nào được đề xuất.</p>
              </div>
            ) : (
              course_recommendations.map((course, idx) => (
                <motion.div
                  key={course.course_id || idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className={styles.courseCard}
                >
                  <div className={styles.courseCardTop}>
                    <div className={styles.courseTitle}>{course.title}</div>
                    {course.is_certification && (
                      <span className={styles.certBadge}>
                        <Award size={12} />
                        CERT
                      </span>
                    )}
                  </div>

                  <div className={styles.courseMeta}>
                    <span style={{ color: levelColor(course.level) }}>
                      {course.level}
                    </span>
                    <span>·</span>
                    <span>{course.platform || course.provider || "Unknown"}</span>
                    <span>·</span>
                    <span>{(course.duration_hours || 0).toFixed(1)}h</span>
                    <span>·</span>
                    <span>{course.cost_usd === 0 ? "Miễn phí" : `$${course.cost_usd}`}</span>
                  </div>

                  {course.gap_skill && (
                    <div className={styles.courseGapTag}>
                      <Zap size={12} />
                      Bổ sung: {course.gap_skill} ({course.gap_severity})
                    </div>
                  )}

                  {course.selection_reason && (
                    <p className={styles.courseReason}>
                      &ldquo;{course.selection_reason}&rdquo;
                    </p>
                  )}

                  <div className={styles.courseFooterActions}>
                    {course.url && (
                      <a
                        href={course.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.courseLink}
                      >
                        <ExternalLink size={14} />
                        Xem khóa học
                      </a>
                    )}
                    {course.similarity && (
                      <span className={styles.similarityScore}>
                         Confidence: {Math.round(course.similarity * 100)}%
                      </span>
                    )}
                  </div>
                </motion.div>
              ))
            )}
          </div>
        )}

        {/* ── Tab: Roadmap ────────────────────────────────────────────────── */}
        {activeTab === "roadmap" && (
          <div className={styles.roadmapSection}>
            {career_roadmap?.stages && career_roadmap.stages.length > 0 ? (
              <>
                <div className={styles.roadmapSummary}>
                  <Target size={20} className={styles.roadmapIcon} />
                  <p>{career_roadmap.summary}</p>
                </div>
                <div className={styles.roadmapTimeline}>
                  {career_roadmap.stages.map((stage, idx) => (
                    <div key={idx} className={styles.roadmapStage}>
                      <div className={styles.roadmapDot} />
                      <div className={styles.roadmapContent}>
                        <div className={styles.roadmapStageNum}>Giai đoạn {stage.stage}</div>
                        <div className={styles.roadmapFocus}>{stage.focus}</div>
                        <div className={styles.roadmapWeeks}>
                          <Clock size={12} />
                          {stage.duration_weeks} tuần
                        </div>
                        
                        {(stage.skills_acquired || []).length > 0 && (
                          <div className={styles.roadmapSkills}>
                            {stage.skills_acquired?.map((s, si) => (
                              <span key={si} className={styles.roadmapSkillBadge}>{s}</span>
                            ))}
                          </div>
                        )}

                        {(stage.courses_taken || []).length > 0 && (
                          <div className={styles.roadmapCoursesList}>
                             <BookOpen size={10} />
                             {stage.courses_taken?.join(", ")}
                          </div>
                        )}

                        {(stage.milestones || []).length > 0 && (
                          <div className={styles.roadmapMilestones}>
                             {stage.milestones?.map((m, mi) => (
                               <div key={mi} className={styles.roadmapMilestoneItem}>
                                  <CheckCircle2 size={10} className={styles.milestoneCheck} />
                                  <span>Week {m.week}: {m.milestone}</span>
                               </div>
                             ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className={styles.emptySection}>
                <Target size={40} className={styles.emptyIcon} />
                <p>Chưa có lộ trình học tập. Hãy chạy phân tích để nhận lộ trình cá nhân hóa.</p>
                <button onClick={() => router.push("/user/jobs")} className={styles.startBtn}>
                  <Zap size={16} />
                  Phân tích ngay
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── Footer ─────────────────────────────────────────────────────── */}
        <div className={styles.footer}>
          <h4 className={styles.footerTitle}>
            <TrendingUp size={20} className={styles.footerIcon} />
            Gợi ý từ AI
          </h4>
          <p className={styles.footerText}>
            Tập trung vào các kỹ năng có severity CAO trước để tối đa hóa điểm match trong 3-6 tháng tới.
          </p>
        </div>
      </div>
    </AuthGuard>
  );
};

export default UserRecommendPage;
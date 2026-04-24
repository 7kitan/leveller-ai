"use client";

import React, { useState, useEffect, useMemo } from "react";
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
  Save,
  Video,
  Play,
} from "lucide-react";
import CourseCard from "@/components/user/CourseCard";
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
  cv_id?: string;
  job_id?: string;
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
  potential_match_pct?: number;
  salary_growth_pct?: number;
  market_sentiment?: string;
  course_recommendations: CourseRec[];
  youtube_videos?: any[];
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

import { useLanguage } from "@/context/LanguageContext";

const UserRecommendPage = () => {
  const { token } = useAuth();
  const router = useRouter();
  const { t } = useLanguage();

  const [gapResult, setGapResult] = useState<GapResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"gaps" | "courses" | "roadmap" | "videos">("gaps");

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
        if (r.data) {
          console.log("[RECOMMEND] Loaded from /analysis/user/latest");
          setGapResult(r.data as GapResult);
        } else {
          console.log("[RECOMMEND] No analysis found (null response)");
          setError(t("error") + ": No analysis found");
        }
      })
      .catch((e) => {
        console.error("[RECOMMEND] API Error:", e);
        setError(t("error") + ": Connection failed");
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
        setError(t("error") + ": Refresh failed");
      })
      .finally(() => setLoading(false));
  };

  const youtube_videos = gapResult?.youtube_videos || [];


  /* ── Loading state ────────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className={styles.loadingWrapper}>
        <div className={styles.spinner} />
        <p className={styles.loadingText}>{t("loading")}</p>
      </div>
    );
  }

  /* ── Error state ──────────────────────────────────────────────────────── */
  if (error && !gapResult) {
    return (
        <div className={styles.pageRoot}>
          <div className={styles.header}>
            <button onClick={() => router.push("/user/jobs")} className={styles.backLink}>
              <ChevronLeft size={16} />
              {t("back")}
            </button>
          </div>
          <div className={styles.emptyState}>
            <AlertCircle size={48} className={styles.emptyIcon} />
            <h3 className={styles.emptyTitle}>{error}</h3>
            <p className={styles.emptySub}>
              {t("roadmap_empty")}
            </p>
            <button
              onClick={() => router.push("/user/jobs")}
              className={styles.startBtn}
            >
              <Zap size={16} />
              {t("start_analysis")}
            </button>
          </div>
        </div>
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

  const highGaps = skill_gaps.filter((g) => g.severity?.toUpperCase() === "HIGH");
  const mediumGaps = skill_gaps.filter((g) => g.severity?.toUpperCase() === "MEDIUM");
  const lowGaps = skill_gaps.filter((g) => g.severity?.toUpperCase() === "LOW");

  const totalHours = course_recommendations.reduce((s, c) => s + (c.duration_hours || 0), 0);
  const certCourses = course_recommendations.filter((c) => c.is_certification);
  const freeCourses = course_recommendations.filter((c) => !c.is_certification && (c.cost_usd || 0) === 0);

  /* ── Tabs ──────────────────────────────────────────────────────────────── */
  const tabs = [
    { key: "gaps", label: t("skill_gaps"), icon: Layers, count: skill_gaps.length },
    { key: "courses", label: t("suggested_courses"), icon: BookOpen, count: course_recommendations.length },
    { key: "videos", label: "Free Tutorials", icon: Video, count: youtube_videos.length },
    { key: "roadmap", label: t("career_roadmap"), icon: Target, count: career_roadmap?.stages?.length ?? 0 },
  ] as const;

  return (
    <div className={styles.pageRoot}>

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div className={styles.header}>
          <div className={styles.titleSection}>
            <div className={styles.badge}>
              <Globe size={12} />
              <span className={styles.badgeLabel}>{t("analysis_results_badge")}</span>
            </div>
            <h1 className={styles.titleMain}>
              {t("analysis_results_title_1")}{" "}
              <span className={styles.gradientText}>{t("analysis_results_title_2")}</span>
            </h1>
            <p className={styles.headerSubtitle}>
              {t("analysis_subtitle")}
            </p>
          </div>
          <div className={styles.controlBar}>
            <button 
              onClick={() => {
                const suggestedSkills = skill_gaps.map(g => g.skill);
                const context = {
                  cv_id: gapResult.cv_id,
                  jd_id: gapResult.job_id || '', 
                  jd_title: gapResult.jd_context?.split('|')[1]?.trim() || gapResult.jd_context || 'Vị trí hiện tại',
                  suggested_skills: suggestedSkills,
                };
                sessionStorage.setItem("analysis_context", JSON.stringify(context));
                if (gapResult.cv_id) {
                  sessionStorage.setItem("target_cv_id", gapResult.cv_id);
                }
                router.push("/user/cv");
              }} 
              className={cn(styles.refreshBtn, styles.accentBtn)}
            >
              <Save size={16} />
              {t("update_cv")}
            </button>
            <button onClick={fetchLatest} className={styles.refreshBtn}>
              <RefreshCcw size={16} />
              {t("refresh")}
            </button>
            <button 
              onClick={() => {
                if (gapResult.job_id) {
                  router.push(`/user/analysis?job_id=${gapResult.job_id}&auto_run=true`);
                } else {
                  router.push(`/user/analysis`);
                }
              }} 
              className={styles.refreshBtn}
            >
              <Zap size={16} />
              {t("re_analyze")}
            </button>
            <button onClick={() => router.push("/user/jobs")} className={styles.refreshBtn}>
              <ChevronLeft size={16} />
              {t("select_other")}
            </button>
          </div>
        </div>

        {/* ── Match Score Banner ───────────────────────────────────────────── */}
        <div className={styles.matchBanner}>
          <div className={styles.matchScoreBlock}>
            <span className={styles.matchScore}>{overall_match_pct ?? 0}%</span>
            <span className={styles.matchLabel}>{t("current_match")}</span>
          </div>
          
          {/* Radar Chart Section - Data Visualization (Point 3) */}
          <div className={styles.radarSection}>
              <ResponsiveContainer width="100%" height={220}>
                 <RadarChart cx="50%" cy="50%" outerRadius="75%" data={
                   Object.keys(match_breakdown).length > 0 ? Object.entries(match_breakdown).map(([name, value]) => ({
                     subject: name.replace('_', ' ').toUpperCase(),
                     A: value,
                     fullMark: 100,
                   })) : [
                     { subject: 'KY NĂNG', A: 40, fullMark: 100 },
                     { subject: 'KINH NGHIỆM', A: 65, fullMark: 100 },
                     { subject: 'CHỨNG CHỈ', A: 30, fullMark: 100 },
                     { subject: 'HỌC VẤN', A: 80, fullMark: 100 },
                     { subject: 'DOMAIN', A: 50, fullMark: 100 },
                   ]
                 }>
                   <PolarGrid stroke="var(--color-border-subtle)" strokeOpacity={0.2} />
                   <PolarAngleAxis 
                     dataKey="subject" 
                     tick={{ fill: 'var(--color-text-muted)', fontSize: 9, fontWeight: 700 }} 
                   />
                   <PolarRadiusAxis 
                     angle={30} 
                     domain={[0, 100]} 
                     tick={false} 
                     axisLine={false} 
                   />
                    <Radar
                      name={t("compatibility_label")}
                      dataKey="A"
                      stroke="var(--color-accent-primary)"
                      fill="var(--color-accent-primary)"
                      fillOpacity={0.4}
                      animationBegin={300}
                      animationDuration={1000}
                    />
                 </RadarChart>
               </ResponsiveContainer>
               
               {/* Micro-animation elements (concept) */}
               <div className={styles.radarGlow} />
          </div>

          <div className={styles.matchRight}>
            <span className={styles.matchAssessment}>&ldquo;{overall_assessment || t("no_assessment_available")}&rdquo;</span>
            <div className={styles.matchStats}>
              <div className={styles.matchStat}>
                <span className={styles.matchStatValue}>{skill_gaps.length}</span>
                <span className={styles.matchStatLabel}>{t("gap_skill_needed")}</span>
              </div>
              <div className={styles.matchStat}>
                <span className={styles.matchStatValue}>{course_recommendations.length}</span>
                <span className={styles.matchStatLabel}>{t("suggested_course_count")}</span>
              </div>
              <div className={styles.matchStat}>
                <span className={styles.matchStatValue}>{totalHours.toFixed(1)}h</span>
                <span className={styles.matchStatLabel}>{t("total_duration")}</span>
              </div>
            </div>

            {/* Growth Forecast */}
            {(gapResult.potential_match_pct || gapResult.salary_growth_pct) && (
              <div className={styles.growthForecast}>
                <div className={styles.growthItem}>
                  <div className={styles.growthLabel}>
                    <Target size={14} className="text-accent" />
                    {t("dash_potential_match")}
                  </div>
                  <div className={styles.growthValue}>
                    {gapResult.potential_match_pct}%
                    <span className={styles.growthDiff}>
                      +{ (gapResult.potential_match_pct || 0) - (overall_match_pct || 0) }%
                    </span>
                  </div>
                </div>
                <div className={styles.growthItem}>
                  <div className={styles.growthLabel}>
                    <TrendingUp size={14} className="text-success" />
                    {t("dash_salary_boost")}
                  </div>
                  <div className={styles.growthValue}>
                    +{gapResult.salary_growth_pct}%
                  </div>
                </div>
                {gapResult.market_sentiment && (
                  <div className={styles.marketInsight}>
                    <Sparkles size={14} className="text-warning" />
                    <span>{t("dash_market_sentiment")}: <strong>{gapResult.market_sentiment}</strong></span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Strengths & Weaknesses ───────────────────────────────────────── */}
        <div className={styles.gridTwo}>
          <div className={styles.infoCard}>
            <h3 className={styles.infoTitle}>
              <CheckCircle2 size={18} className={styles.successIcon} />
              {t("strengths")}
            </h3>
            <ul className={styles.infoList}>
              {strengths.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
              {strengths.length === 0 && <li>{t("analyzing_data")}</li>}
            </ul>
          </div>
          <div className={styles.infoCard}>
            <h3 className={styles.infoTitle}>
              <AlertCircle size={18} className={styles.warningIcon} />
              {t("weaknesses")}
            </h3>
            <ul className={styles.infoList}>
              {weaknesses.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
              {weaknesses.length === 0 && <li>{t("all_skills_ok")}</li>}
            </ul>
          </div>
        </div>

        {/* ── Transferable Insights ────────────────────────────────────────── */}
        {(gapResult.transferable_insights || []).length > 0 && (
          <div className={styles.insightBox}>
            <h4 className={styles.insightTitle}>
              <Sparkles size={16} />
              {t("transferable_skills")}
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
            {t("severity_high")} ({highGaps.length})
          </div>
          <div className={styles.severityPill} style={{ color: severityColor("MEDIUM"), borderColor: severityColor("MEDIUM") + "40", background: severityColor("MEDIUM") + "12" }}>
            <Target size={14} />
            {t("severity_medium")} ({mediumGaps.length})
          </div>
          <div className={styles.severityPill} style={{ color: severityColor("LOW"), borderColor: severityColor("LOW") + "40", background: severityColor("LOW") + "12" }}>
            <CheckCircle2 size={14} />
            {t("severity_low")} ({lowGaps.length})
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
                <p>{t("success")} - {t("no_gaps_detected")}</p>
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
                      {gap.severity?.toUpperCase()}
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
                      ~{gap.estimated_months ?? 1} {t("months_short")}
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
                <p>{t("no_cv_msg")}</p>
              </div>
            ) : (
              course_recommendations.map((course: any, idx: number) => (
                <CourseCard 
                  key={course.course_id || idx} 
                  course={{
                    id: course.course_id,
                    title: course.title,
                    platform: course.platform || course.provider,
                    level: course.level,
                    match: `${Math.round((course.similarity || 0) * 100)}%`,
                    skills: course.tags || [],
                    url: course.url,
                    is_certification: course.is_certification,
                    selection_reason: course.selection_reason
                  }} 
                  index={idx} 
                />
              ))
            )}
          </div>
        )}

        {/* ── Tab: YouTube Videos ────────────────────────────────────────── */}
        {activeTab === "videos" && (
          <div className={styles.videoSection}>
            <div className={styles.videoGrid}>
              {youtube_videos.length === 0 ? (
                <div className={styles.emptySection}>
                  <Video size={40} className={styles.emptyIcon} />
                  <p>No free tutorials found yet.</p>
                </div>
              ) : (
                youtube_videos.map((vid: any, idx: number) => (
                <motion.div
                  key={vid.video_id || idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className={styles.videoCard}
                >
                  <div className={styles.videoPlayer}>
                    <iframe
                      src={vid.embed_url}
                      title={vid.title}
                      frameBorder="0"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                    ></iframe>
                  </div>
                  <div className={styles.videoInfo}>
                    <div className={styles.videoTitle}>{vid.title}</div>
                    <div className={styles.videoMeta}>
                      <span>{vid.channel_name}</span>
                      {vid.gap_skill && (
                        <span className={styles.videoGapTag}>
                          <Play size={10} /> {vid.gap_skill}
                        </span>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))
            )}
          </div>
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
                        <div className={styles.roadmapStageNum}>{t("roadmap_stage")} {stage.stage}</div>
                        <div className={styles.roadmapFocus}>{stage.focus}</div>
                        <div className={styles.roadmapWeeks}>
                          <Clock size={12} />
                          {stage.duration_weeks} {t("roadmap_weeks")}
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
                <p>{t("roadmap_empty")}</p>
                <button onClick={() => router.push("/user/jobs")} className={styles.startBtn}>
                  <Zap size={16} />
                  {t("start_analysis")}
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── Footer ─────────────────────────────────────────────────────── */}
        <div className={styles.footer}>
          <h4 className={styles.footerTitle}>
            <TrendingUp size={20} className={styles.footerIcon} />
            {t("ai_suggestions")}
          </h4>
          <p className={styles.footerText}>
            {t("ai_suggestion_text")}
          </p>
        </div>
      </div>
  );
};

export default UserRecommendPage;
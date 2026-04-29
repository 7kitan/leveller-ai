"use client";

import React, { useState, useEffect, useMemo } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { useRouter, useSearchParams } from "next/navigation";
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
import { cn, formatPercent, formatNumber, formatHours } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import ReactECharts from 'echarts-for-react';
import FeedbackSection from "@/components/user/FeedbackSection";
import styles from "./user-recommend.module.css";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";
import { useLanguage } from "@/context/LanguageContext";

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
  match_impact?: number;        // NEW: % tăng match nếu học skill này
  salary_impact?: number;       // NEW: % tăng lương nếu học skill này
  market_demand?: number;       // NEW: Điểm nhu cầu thị trường (0-100)
  avg_salary_range?: {          // NEW: Mức lương trung bình cho skill này
    min: number | null;
    max: number | null;
  };
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
    method?: string;
  };
  status?: string;
  analysis_id?: string;
  has_feedback?: boolean;
  is_cached?: boolean;
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
  const { user } = useAuth();
  const { theme } = useTheme();
  const router = useRouter();
  const { t } = useLanguage();

  const isDark = theme === "dark";
  const chartTextColor = isDark ? "rgba(255, 255, 255, 0.7)" : "rgba(15, 23, 42, 0.8)";
  const chartAxisColor = isDark ? "rgba(255, 255, 255, 0.15)" : "rgba(15, 23, 42, 0.15)";
  const chartSplitLineColor = isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(15, 23, 42, 0.05)";
  const chartTooltipBg = isDark ? "rgba(0, 0, 0, 0.85)" : "rgba(255, 255, 255, 0.95)";
  const chartTooltipText = isDark ? "#fff" : "#0f172a";

  const translateRadarCategory = (name: string) => {
    const n = name.toUpperCase().trim();
    if (n.includes('TECHNICAL')) return t('cat_technical');
    if (n.includes('SOFT')) return t('cat_soft');
    if (n.includes('TOOLS') || n.includes('FRAMEWORK')) return t('cat_tools');
    if (n.includes('DOMAIN') || n.includes('KNOWLEDGE')) return t('cat_domain');
    if (n.includes('CERTIFICATION')) return t('cat_cert');
    return name;
  };

  const [gapResult, setGapResult] = useState<GapResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"gaps" | "courses" | "roadmap" | "videos">("gaps");
  const [isProcessing, setIsProcessing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [processMessage, setProcessMessage] = useState("");

  const searchParams = useSearchParams();
  const taskIdFromUrl = searchParams.get("task_id");

  /* ── Progressive Polling Logic ───────────────────────────────────────── */
  useEffect(() => {
    if (!user || !taskIdFromUrl) return;

    console.log("[RECOMMEND] Polling for progressive updates - Task ID:", taskIdFromUrl);
    setIsProcessing(true);
    
    // 0. Load partial data from sessionStorage if exists (from analysis page)
    try {
      const partial = sessionStorage.getItem("gap_analysis_partial");
      if (partial) {
        setGapResult(JSON.parse(partial));
        setLoading(false);
        sessionStorage.removeItem("gap_analysis_partial");
      }
    } catch (e) {}

    // Skip polling if task_id is invalid (cached result)
    if (taskIdFromUrl === "null" || taskIdFromUrl === "undefined") {
      console.log("[RECOMMEND] Invalid task_id, skipping status polling");
      setIsProcessing(false);
      return;
    }

    // 1. Initial fetch to check if task is already completed
    const fetchInitialStatus = async () => {
      try {
        const resp = await api.get(`analysis/status/${taskIdFromUrl}`);
        const { status, result, partial_result } = resp.data;
        
        console.log("[RECOMMEND] Initial status check:", status);
        
        if (status === "completed" && result) {
          console.log("[RECOMMEND] Task already completed, loading full result");
          setGapResult(result as GapResult);
          setIsProcessing(false);
          setLoading(false);
          return true; // Signal that we're done
        } else if (partial_result) {
          console.log("[RECOMMEND] Loading partial result");
          setGapResult(partial_result as GapResult);
          setLoading(false);
        }
        return false; // Continue polling
      } catch (e) {
        console.error("[RECOMMEND] Initial fetch error:", e);
        return false;
      }
    };

    // Start with initial fetch
    fetchInitialStatus().then(isDone => {
      if (isDone) return; // Don't start polling if already done

      // 2. Start polling for progressive updates
      const interval = setInterval(async () => {
        try {
          const resp = await api.get(`analysis/status/${taskIdFromUrl}`);
          
          const { status, result, partial_result, message } = resp.data;
          
          if (message) setProcessMessage(message);

          if (partial_result) {
            console.log("[RECOMMEND] Received partial update:", partial_result.node);
            setGapResult(prev => {
            // Deep merge to preserve all previously loaded data
            const merged = {
              ...prev,
              ...partial_result,
              // Preserve arrays - only update if new data exists
              skill_gaps: (partial_result.skill_gaps?.length ?? 0) > 0 
                ? partial_result.skill_gaps 
                : (prev?.skill_gaps || []),
              course_recommendations: (partial_result.course_recommendations?.length ?? 0) > 0 
                ? partial_result.course_recommendations 
                : (prev?.course_recommendations || []),
              youtube_videos: (partial_result.youtube_videos?.length ?? 0) > 0
                ? partial_result.youtube_videos
                : (prev?.youtube_videos || []),
              strengths: (partial_result.strengths?.length ?? 0) > 0
                ? partial_result.strengths
                : (prev?.strengths || []),
              weaknesses: (partial_result.weaknesses?.length ?? 0) > 0
                ? partial_result.weaknesses
                : (prev?.weaknesses || []),
              transferable_insights: (partial_result.transferable_insights?.length ?? 0) > 0
                ? partial_result.transferable_insights
                : (prev?.transferable_insights || []),
              // Preserve objects
              career_roadmap: partial_result.career_roadmap || prev?.career_roadmap,
              match_breakdown: partial_result.match_breakdown || prev?.match_breakdown || {},
              gap_summary: partial_result.gap_summary || prev?.gap_summary,
              // Preserve scalar values - only update if defined
              overall_match_pct: partial_result.overall_match_pct ?? prev?.overall_match_pct,
              potential_match_pct: partial_result.potential_match_pct ?? prev?.potential_match_pct,
              salary_growth_pct: partial_result.salary_growth_pct ?? prev?.salary_growth_pct,
              overall_assessment: partial_result.overall_assessment || prev?.overall_assessment,
              jd_context: partial_result.jd_context || prev?.jd_context,
              market_sentiment: partial_result.market_sentiment || prev?.market_sentiment,
            } as GapResult;
            
            return merged;
          });
          setLoading(false);
        }

        if (status === "completed") {
          console.log("[RECOMMEND] Analysis completed!");
          // Merge final result with existing partial data to avoid losing anything
          setGapResult(prev => {
            const finalResult = result as GapResult;
            return {
              ...prev,
              ...finalResult,
              // Ensure we keep the most complete version of each array
              skill_gaps: (finalResult.skill_gaps?.length ?? 0) > 0 
                ? finalResult.skill_gaps 
                : (prev?.skill_gaps || []),
              course_recommendations: (finalResult.course_recommendations?.length ?? 0) > 0 
                ? finalResult.course_recommendations 
                : (prev?.course_recommendations || []),
              youtube_videos: (finalResult.youtube_videos?.length ?? 0) > 0
                ? finalResult.youtube_videos
                : (prev?.youtube_videos || []),
              strengths: (finalResult.strengths?.length ?? 0) > 0
                ? finalResult.strengths
                : (prev?.strengths || []),
              weaknesses: (finalResult.weaknesses?.length ?? 0) > 0
                ? finalResult.weaknesses
                : (prev?.weaknesses || []),
              career_roadmap: finalResult.career_roadmap || prev?.career_roadmap,
              match_breakdown: finalResult.match_breakdown || prev?.match_breakdown || {},
              // Preserve scalar values - only update if defined
              overall_match_pct: finalResult.overall_match_pct ?? prev?.overall_match_pct,
              potential_match_pct: finalResult.potential_match_pct ?? prev?.potential_match_pct,
              salary_growth_pct: finalResult.salary_growth_pct ?? prev?.salary_growth_pct,
              overall_assessment: finalResult.overall_assessment || prev?.overall_assessment,
              jd_context: finalResult.jd_context || prev?.jd_context,
              market_sentiment: finalResult.market_sentiment || prev?.market_sentiment,
            } as GapResult;
          });
          setIsProcessing(false);
          setLoading(false);
          clearInterval(interval);
        } else if (status === "failed") {
          console.error("[RECOMMEND] Analysis task failed");
          setIsProcessing(false);
          clearInterval(interval);
        }
      } catch (e) {
        console.error("[RECOMMEND] Polling error:", e);
      }
    }, 4000);

      return () => clearInterval(interval);
    });

    return () => {};
  }, [ taskIdFromUrl]);

  /* ── Load initial gap result (if no task_id) ─────────────────────────── */
  useEffect(() => {
    if (!user || taskIdFromUrl) return;

    try {
      const stored = sessionStorage.getItem("gap_analysis_result");
      if (stored) {
        const parsed = JSON.parse(stored) as GapResult;
        setGapResult(parsed);
        sessionStorage.removeItem("gap_analysis_result");
        setLoading(false);
        return;
      }
    } catch (e) {}

    api
      .get("/analysis/user/latest")
      .then((r) => {
        if (r.data) {
          setGapResult(r.data);
        } else {
          setError(t("error_no_analysis"));
        }
      })
      .catch((e: any) => {
        setError(t("error_connection_failed"));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [user]);

  const handleRefresh = async () => {
    if (!user) return;
    setRefreshing(true);
    try {
      const resp = await api.get("analysis/user/latest");
      if (resp.data) {
        setGapResult(resp.data);
        sessionStorage.setItem("gap_analysis_result", JSON.stringify(resp.data));
      }
    } catch (e) {
      setError(t("error_refresh_failed"));
    } finally {
      setRefreshing(false);
    }
  };

  const youtube_videos = gapResult?.youtube_videos || [];

  if (loading) {
    return (
      <div className={styles.loadingWrapper}>
        <div className={styles.spinner} />
        <p className={styles.loadingText}>{t("loading")}</p>
      </div>
    );
  }

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
            <p className={styles.emptySub}>{t("roadmap_empty")}</p>
            <button onClick={() => router.push("/user/jobs")} className={styles.startBtn}>
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

  const hasImpactData = skill_gaps.length > 0 && skill_gaps.some(g => 
    g.match_impact !== undefined || g.salary_impact !== undefined
  );

  const totalHours = course_recommendations.reduce((s, c) => s + (c.duration_hours || 0), 0);
  const displayTotalHours = totalHours > 0 ? formatHours(totalHours) : t("not_available");

  const tabs = [
    { key: "gaps", label: t("skill_gaps"), icon: Layers, count: skill_gaps.length },
    { key: "courses", label: t("suggested_courses"), icon: BookOpen, count: course_recommendations.length },
    { key: "videos", label: t("free_tutorials"), icon: Video, count: youtube_videos.length },
    { key: "roadmap", label: t("career_roadmap"), icon: Target, count: career_roadmap?.stages?.length ?? 0 },
  ] as const;

  return (
    <PageContainer>
      <PageHeader 
        title={
          <>
            {t("analysis_results_title_1")}{" "}
            <span className={styles.gradientText}>{t("analysis_results_title_2")}</span>
          </>
        }
        subtitle={t("analysis_subtitle")}
      />

      <div className={styles.controlBar}>
        <button 
          onClick={() => {
            const suggestedSkills = skill_gaps.map(g => g.skill);
            const context = {
              cv_id: gapResult.cv_id,
              jd_id: gapResult.job_id || '', 
              jd_title: gapResult.jd_context?.split('|')[1]?.trim() || gapResult.jd_context || t('current_position'),
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
        <button 
          onClick={handleRefresh} 
          className={cn(styles.refreshBtn, refreshing && styles.refreshBtnDisabled)}
          disabled={refreshing}
        >
          {refreshing ? <Loader2 size={16} className={styles.spinIcon} /> : <RefreshCcw size={16} />}
          {t("refresh")}
        </button>
        <button 
          onClick={() => {
            if (gapResult.cv_id) {
              router.push(`/user/analysis?cv_id=${gapResult.cv_id}`);
            } else {
              router.push(`/user/analysis`);
            }
          }} 
          className={styles.refreshBtn}
        >
          <Target size={16} />
          {t("try_different_jd")}
        </button>
      </div>

      <div className={styles.matchBanner}>
        <div className={styles.matchScoreBlock}>
          <span className={styles.matchScore}>{formatPercent(overall_match_pct ?? 0)}</span>
          <span className={styles.matchLabel}>{t("current_match")}</span>
        </div>
        
        <div className={styles.radarSection}>
          {Object.keys(match_breakdown).length === 0 ? (
            <div className={cn(styles.skeleton, styles.skeletonChart)} style={{ width: '100%', height: '100%' }} />
          ) : (
            <ReactECharts
              key={`radar-chart-${Object.keys(match_breakdown).join('-')}-${overall_match_pct}`}
              option={{
                radar: {
                  indicator: Object.keys(match_breakdown).map((name) => ({
                    name: translateRadarCategory(name),
                    max: 100,
                  })),
                  shape: 'polygon',
                  splitNumber: 4,
                  center: ['50%', '50%'],
                  radius: '65%',
                  axisName: {
                    color: chartTextColor,
                    fontSize: 11,
                    fontWeight: 700,
                    backgroundColor: isDark ? 'rgba(0, 0, 0, 0.5)' : 'rgba(255, 255, 255, 0.7)',
                    borderRadius: 4,
                    padding: [4, 8],
                  },
                  splitLine: { lineStyle: { color: chartSplitLineColor, width: 1 } },
                  splitArea: {
                    show: true,
                    areaStyle: {
                      color: isDark ? ['rgba(79, 70, 229, 0.03)', 'rgba(79, 70, 229, 0.01)'] : ['rgba(79, 70, 229, 0.05)', 'rgba(79, 70, 229, 0.02)'],
                    },
                  },
                  axisLine: { lineStyle: { color: chartAxisColor } },
                },
                series: [{
                  type: 'radar',
                  data: [{
                    value: Object.values(match_breakdown),
                    name: t('match_level'),
                    areaStyle: {
                      color: {
                        type: 'radial', x: 0.5, y: 0.5, r: 0.5,
                        colorStops: [
                          { offset: 0, color: 'rgba(79, 70, 229, 0.4)' },
                          { offset: 0.5, color: 'rgba(14, 165, 233, 0.3)' },
                          { offset: 1, color: 'rgba(16, 185, 129, 0.2)' },
                        ],
                      },
                      shadowColor: 'rgba(79, 70, 229, 0.3)', shadowBlur: 20,
                    },
                    lineStyle: { color: '#4f46e5', width: 2 },
                    label: {
                      show: true, 
                      formatter: (params: any) => {
                        // For radar charts, params.value can be an array. 
                        // If so, we don't show the label on the points to avoid clutter, 
                        // as the radar axes already show labels or we use tooltips.
                        return ''; 
                      },
                    },
                    itemStyle: { color: '#4f46e5', borderColor: '#fff', borderWidth: 2 },
                  }],
                }],
                tooltip: {
                  trigger: 'item',
                  backgroundColor: 'rgba(0, 0, 0, 0.85)',
                  borderColor: '#4f46e5',
                  borderWidth: 1,
                  textStyle: { color: '#fff', fontSize: 12 },
                  formatter: (params: any) => {
                    if (!params || !params.value || !Array.isArray(params.value)) return '';
                    const indicators = Object.keys(match_breakdown);
                    let res = `<div style="padding: 8px 12px; min-width: 150px;">`;
                    res += `<div style="margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 4px;"><strong style="color: #818cf8; font-size: 13px;">${params.name}</strong></div>`;
                    indicators.forEach((name, i) => {
                      const val = params.value[i];
                      res += `<div style="display: flex; justify-content: space-between; gap: 20px; margin-bottom: 4px;">
                        <span style="color: rgba(255,255,255,0.7);">${translateRadarCategory(name)}</span>
                        <strong style="color: #fff;">${formatNumber(Number(val))}%</strong>
                      </div>`;
                    });
                    res += `</div>`;
                    return res;
                  }
                },
              }}
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'svg' }}
              notMerge={true}
              lazyUpdate={true}
            />
          )}
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
              <span className={styles.matchStatValue}>{displayTotalHours}</span>
              <span className={styles.matchStatLabel}>{t("total_duration")}</span>
            </div>
          </div>

          {(!!gapResult.potential_match_pct || !!gapResult.salary_growth_pct) ? (
            <div className={styles.growthForecast}>
              <div className={styles.growthItem}>
                <div className={styles.growthLabel}>
                  <Target size={14} className="text-accent" />
                  {t("dash_potential_match")}
                </div>
                <div className={styles.growthValue}>
                  {formatPercent(gapResult.potential_match_pct || 0)}
                  <span className={styles.growthDiff}>
                    +{formatPercent((gapResult.potential_match_pct || 0) - (overall_match_pct || 0))}
                  </span>
                </div>
              </div>
              <div className={styles.growthItem}>
                <div className={styles.growthLabel}>
                  <TrendingUp size={14} className="text-success" />
                  {t("dash_salary_boost")}
                </div>
                <div className={styles.growthValue}>
                  +{formatPercent(gapResult.salary_growth_pct || 0)}
                </div>
              </div>
              {gapResult.market_sentiment && (
                <div className={styles.marketInsight}>
                  <Sparkles size={14} className="text-warning" />
                  <span>{t("dash_market_sentiment")}: <strong>{gapResult.market_sentiment}</strong></span>
                </div>
              )}
            </div>
          ) : isProcessing ? (
            <div className={styles.growthForecast}>
              <div className={cn(styles.skeleton, styles.skeletonText)} style={{ height: '3rem', marginBottom: '0.75rem' }} />
              <div className={cn(styles.skeleton, styles.skeletonText)} style={{ height: '3rem' }} />
            </div>
          ) : null}
        </div>
      </div>

      <div className={styles.gridTwo}>
        <div className={styles.infoCard}>
          <h3 className={styles.infoTitle}>
            <CheckCircle2 size={18} className={styles.successIcon} />
            {t("strengths")}
          </h3>
          {isProcessing && strengths.length === 0 ? (
            <div className={styles.infoList}>
              <div className={cn(styles.skeleton, styles.skeletonText)} />
              <div className={cn(styles.skeleton, styles.skeletonText, styles.skeletonTextMedium)} />
            </div>
          ) : (
            <ul className={styles.infoList}>
              {strengths.map((s, i) => <li key={i}>{s}</li>)}
              {strengths.length === 0 && <li>{t("analyzing_data")}</li>}
            </ul>
          )}
        </div>
        <div className={styles.infoCard}>
          <h3 className={styles.infoTitle}>
            <AlertCircle size={18} className={styles.warningIcon} />
            {t("weaknesses")}
          </h3>
          {isProcessing && weaknesses.length === 0 ? (
            <div className={styles.infoList}>
              <div className={cn(styles.skeleton, styles.skeletonText)} />
              <div className={cn(styles.skeleton, styles.skeletonText, styles.skeletonTextShort)} />
            </div>
          ) : (
            <ul className={styles.infoList}>
              {weaknesses.map((w, i) => <li key={i}>{w}</li>)}
              {weaknesses.length === 0 && <li>{t("all_skills_ok")}</li>}
            </ul>
          )}
        </div>
      </div>

      {(gapResult.transferable_insights || []).length > 0 && (
        <div className={styles.insightBox}>
          <h4 className={styles.insightTitle}>
            <Sparkles size={16} />
            {t("transferable_skills")}
          </h4>
          <div className={styles.insightContent}>
            {gapResult.transferable_insights.map((ins, i) => (
              <div key={i} className={styles.insightItem}>{ins}</div>
            ))}
          </div>
        </div>
      )}

      <div className={styles.severityRow}>
        <div className={styles.severityPill} style={{ color: severityColor("HIGH"), borderColor: severityColor("HIGH") + "40", background: severityColor("HIGH") + "12" }}>
          <AlertCircle size={14} /> {t("severity_high")} ({highGaps.length})
        </div>
        <div className={styles.severityPill} style={{ color: severityColor("MEDIUM"), borderColor: severityColor("MEDIUM") + "40", background: severityColor("MEDIUM") + "12" }}>
          <Target size={14} /> {t("severity_medium")} ({mediumGaps.length})
        </div>
        <div className={styles.severityPill} style={{ color: severityColor("LOW"), borderColor: severityColor("LOW") + "40", background: severityColor("LOW") + "12" }}>
          <CheckCircle2 size={14} /> {t("severity_low")} ({lowGaps.length})
        </div>
      </div>

      {isProcessing && (
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className={styles.processingIndicator}>
          <Loader2 className={styles.spinIcon} size={16} />
          <span className={styles.processingText}>{processMessage || t('ai_searching')}</span>
        </motion.div>
      )}

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

      {activeTab === "gaps" && (
        <div className={styles.gapGrid}>
          {skill_gaps.length > 0 && (
            <div className={styles.impactChartSection} style={{ gridColumn: '1 / -1' }}>
              <div className={styles.impactChartHeader}>
                <h3 className={styles.impactChartTitle}><BarChart3 size={18} /> {t('skill_impact_analysis')}</h3>
              </div>
              <div className={styles.impactChartContainer}>
                {hasImpactData ? (
                  <ReactECharts
                    key={`impact-chart-${skill_gaps.map(g => g.skill).join('-')}-${skill_gaps.length}`}
                    option={{
                      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: chartTooltipBg, borderColor: '#4f46e5', borderWidth: 1, textStyle: { color: chartTooltipText } },
                      legend: { data: [t('match_impact'), t('salary_impact')], textStyle: { color: chartTextColor, fontSize: 10 }, top: 0 },
                      grid: { left: '3%', right: '4%', bottom: '3%', top: '40px', containLabel: true },
                      xAxis: { type: 'value', axisLabel: { color: chartTextColor, fontSize: 10 }, splitLine: { lineStyle: { color: chartSplitLineColor } } },
                      yAxis: { type: 'category', data: skill_gaps.map(g => g.skill).reverse(), axisLabel: { color: chartTextColor, fontSize: 11, width: 100, overflow: 'truncate' }, axisLine: { lineStyle: { color: chartAxisColor } } },
                      series: [
                        { name: t('match_impact'), type: 'bar', data: skill_gaps.map(g => parseFloat(formatNumber(g.match_impact || 0))).reverse(), itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#4f46e5' }, { offset: 1, color: '#0ea5e9' }] }, borderRadius: [0, 4, 4, 0] }, barWidth: '30%' },
                        { name: t('salary_impact'), type: 'bar', data: skill_gaps.map(g => parseFloat(formatNumber(g.salary_impact || 0))).reverse(), itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#10b981' }, { offset: 1, color: '#34d399' }] }, borderRadius: [0, 4, 4, 0] }, barWidth: '30%' }
                      ]
                    }}
                    style={{ height: '100%', width: '100%' }}
                    opts={{ renderer: 'svg' }}
                    notMerge={true}
                  />
                ) : <div className={cn(styles.skeleton, styles.skeletonChart)} />}
              </div>
            </div>
          )}
          
          {skill_gaps.length === 0 && !isProcessing ? (
            <div className={styles.emptySection}>
              <CheckCircle2 size={40} className={styles.emptyIcon} />
              <p>{t("success")} - {t("no_gaps_detected")}</p>
            </div>
          ) : (
            skill_gaps.map((gap, idx) => (
              <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }} className={styles.gapCard} style={{ borderColor: severityColor(gap.severity) + "30" }}>
                <div className={styles.gapCardTop}>
                  <span className={styles.gapSkillName}>{gap.skill}</span>
                  <span className={styles.gapSeverityBadge} style={{ color: severityColor(gap.severity), background: severityColor(gap.severity) + "12", borderColor: severityColor(gap.severity) + "30" }}>
                    {t(`severity_${gap.severity?.toLowerCase()}` as any)}
                  </span>
                </div>
                <div className={styles.gapCardMeta}>
                  {gap.required_level && <span className={styles.gapLevel}>{t('level_label')} <b>{t(`level_${gap.required_level?.toLowerCase()}` as any).startsWith('level_') ? gap.required_level : t(`level_${gap.required_level?.toLowerCase()}` as any)}</b></span>}
                  <span className={styles.gapMonths}><Clock size={12} /> ~{gap.estimated_months ?? 1} {t("months_short")}</span>
                  {gap.gap_type && <span className={styles.gapType}>{gap.gap_type}</span>}
                  {gap.is_critical && <span className={styles.criticalTag}>{t('critical')}</span>}
                </div>
                {(!!gap.match_impact || !!gap.salary_impact) && (
                  <div className={styles.gapImpact}>
                    {!!gap.match_impact && <span className={styles.impactBadge} style={{ background: 'rgba(79, 70, 229, 0.1)', color: '#4f46e5' }}><Target size={12} /> +{formatNumber(gap.match_impact)}% {t('match')}</span>}
                    {!!gap.salary_impact && <span className={styles.impactBadge} style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}><TrendingUp size={12} /> +{formatNumber(gap.salary_impact)}% {t('salary_text')}</span>}
                  </div>
                )}
                {gap.learning_path && <div className={styles.gapLearningPath}><Sparkles size={12} className={styles.pathIcon} /><p>{gap.learning_path}</p></div>}
              </motion.div>
            ))
          )}
        </div>
      )}

      {activeTab === "courses" && (
        <div className={styles.courseGrid}>
          {course_recommendations.length === 0 ? (
            <div className={styles.emptySection}><BookOpen size={40} className={styles.emptyIcon} /><p>{t("no_cv_msg")}</p></div>
          ) : (
            course_recommendations.map((course: any, idx: number) => (
              <CourseCard key={course.course_id || idx} course={{ id: course.course_id, title: course.title, platform: course.platform || course.provider, level: course.level, match: `${Math.round((course.similarity || 0) * 100)}%`, skills: course.tags || [], url: course.url, is_certification: course.is_certification, selection_reason: course.selection_reason }} index={idx} />
            ))
          )}
        </div>
      )}

      {activeTab === "videos" && (
        <div className={styles.videoSection}>
          <div className={styles.videoGrid}>
            {youtube_videos.length === 0 ? (
              <div className={styles.emptySection}><Video size={40} className={styles.emptyIcon} /><p>{t('no_tutorials')}</p></div>
            ) : (
              youtube_videos.map((vid: any, idx: number) => (
                <motion.div key={vid.video_id || idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }} className={styles.videoCard}>
                  <div className={styles.videoPlayer}><iframe src={vid.embed_url} title={vid.title} frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen></iframe></div>
                  <div className={styles.videoInfo}>
                    <div className={styles.videoTitle}>{vid.title}</div>
                    <div className={styles.videoMeta}><span>{vid.channel_name}</span>{vid.gap_skill && <span className={styles.videoGapTag}><Play size={10} /> {vid.gap_skill}</span>}</div>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </div>
      )}

      {activeTab === "roadmap" && (
        <div className={styles.roadmapSection}>
          {career_roadmap?.stages && career_roadmap.stages.length > 0 ? (
            <>
              <div className={styles.roadmapSummary}><Target size={20} className={styles.roadmapIcon} /><p>{career_roadmap.summary}</p></div>
              <div className={styles.roadmapTimeline}>
                {career_roadmap.stages.map((stage, idx) => (
                  <div key={idx} className={styles.roadmapStage}>
                    <div className={styles.roadmapDot} />
                    <div className={styles.roadmapContent}>
                      <div className={styles.roadmapStageNum}>{t("roadmap_stage")} {stage.stage}</div>
                      <div className={styles.roadmapFocus}>{stage.focus}</div>
                      <div className={styles.roadmapWeeks}><Clock size={12} /> {stage.duration_weeks} {t("roadmap_weeks")}</div>
                      {(stage.skills_acquired || []).length > 0 && <div className={styles.roadmapSkills}>{stage.skills_acquired?.map((s, si) => <span key={si} className={styles.roadmapSkillBadge}>{s}</span>)}</div>}
                      {(stage.courses_taken || []).length > 0 && <div className={styles.roadmapCoursesList}><BookOpen size={10} /> {stage.courses_taken?.join(", ")}</div>}
                      {(stage.milestones || []).length > 0 && <div className={styles.roadmapMilestones}>{stage.milestones?.map((m, mi) => <div key={mi} className={styles.roadmapMilestoneItem}><CheckCircle2 size={10} className={styles.milestoneCheck} /><span>{t('week_text')} {m.week}: {m.milestone}</span></div>)}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className={styles.emptySection}><Target size={40} className={styles.emptyIcon} /><p>{t("roadmap_empty")}</p><button onClick={() => router.push("/user/jobs")} className={styles.startBtn}><Zap size={16} /> {t("start_analysis")}</button></div>
          )}
        </div>
      )}

      <div className={styles.footer}>
        <h4 className={styles.footerTitle}><TrendingUp size={20} className={styles.footerIcon} /> {t("ai_suggestions")}</h4>
        <p className={styles.footerText}>{t("ai_suggestion_text")}</p>
      </div>

      {gapResult && gapResult.analysis_id && (
        <FeedbackSection analysisId={gapResult.analysis_id} hasFeedback={gapResult.has_feedback} isCached={gapResult.is_cached} />
      )}
    </PageContainer>
  );
};

export default UserRecommendPage;

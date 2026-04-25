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
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import ReactECharts from 'echarts-for-react';
import FeedbackSection from "@/components/user/FeedbackSection";
import styles from "./user-recommend.module.css";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";

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

import { useLanguage } from "@/context/LanguageContext";

const UserRecommendPage = () => {
  const { token } = useAuth();
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
    if (!token || !taskIdFromUrl) return;

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

    const interval = setInterval(async () => {
      try {
        const resp = await api.get(`analysis/status/${taskIdFromUrl}`);
        
        const { status, result, partial_result, message } = resp.data;
        
        if (message) setProcessMessage(message);

        if (partial_result) {
          console.log("[RECOMMEND] Received partial update:", partial_result.node);
          setGapResult(prev => ({
            ...prev,
            ...partial_result,
            // Merge specialized arrays to avoid losing data
            course_recommendations: partial_result.course_recommendations?.length > 0 
                ? partial_result.course_recommendations 
                : (prev?.course_recommendations || [])
          } as GapResult));
          setLoading(false);
        }

        if (status === "completed") {
          console.log("[RECOMMEND] Analysis completed!");
          setGapResult(result as GapResult);
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
  }, [token, taskIdFromUrl]);

  /* ── Load initial gap result (if no task_id) ─────────────────────────── */
  useEffect(() => {
    if (!token || taskIdFromUrl) return;

    // 1. Try sessionStorage first
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
    api
      .get("/analysis/user/latest")
      .then((r) => {
        if (r.data) {
          console.log("[RECOMMEND] Loaded from /analysis/user/latest");
          setGapResult(r.data);
        } else {
          console.log("[RECOMMEND] No analysis found (null response)");
          setError(t("error_no_analysis"));
        }
      })
      .catch((e: any) => {
        console.error("[RECOMMEND] API Error:", e);
        setError(t("error_connection_failed"));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token]);

  const handleRefresh = async () => {
    if (!token) return;
    setRefreshing(true);
    try {
      const resp = await api.get("analysis/user/latest");
      if (resp.data) {
        console.log("[RECOMMEND] Refreshed data:", resp.data);
        setGapResult(resp.data);
        sessionStorage.setItem("gap_analysis_result", JSON.stringify(resp.data));
      }
    } catch (e) {
      console.error("[RECOMMEND] Refresh failed:", e);
      setError(t("error_refresh_failed"));
    } finally {
      setRefreshing(false);
    }
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
  const validDurationCount = course_recommendations.filter((c) => c.duration_hours && c.duration_hours > 0).length;
  const displayTotalHours = totalHours > 0 ? `${totalHours.toFixed(1)}h` : t("not_available");
  const certCourses = course_recommendations.filter((c) => c.is_certification);
  const freeCourses = course_recommendations.filter((c) => !c.is_certification && (c.cost_usd || 0) === 0);

  /* ── Tabs ──────────────────────────────────────────────────────────────── */
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
            if (gapResult.job_id) {
              router.push(`/user/analysis?job_id=${gapResult.job_id}&auto_run=true`);
            } else {
              router.push(`/user/analysis`);
            }
          }} 
          className={styles.refreshBtn}
        >
          <Zap size={16} />
          {t("reanalyze")}
        </button>
      </div>

        {/* ── Match Score Banner ───────────────────────────────────────────── */}
        <div className={styles.matchBanner}>
          <div className={styles.matchScoreBlock}>
            <span className={styles.matchScore}>{overall_match_pct ?? 0}%</span>
            <span className={styles.matchLabel}>{t("current_match")}</span>
          </div>
          
          {/* Radar Chart - Gap Analysis */}
          <div className={styles.radarSection}>
            <ReactECharts
              option={{
                radar: {
                  indicator: (Object.keys(match_breakdown).length > 0 
                    ? Object.keys(match_breakdown).map((name) => ({
                        name: translateRadarCategory(name),
                        max: 100,
                      }))
                    : [
                        { name: t('cat_technical'), max: 100 },
                        { name: t('cat_soft'), max: 100 },
                        { name: t('cat_tools'), max: 100 },
                        { name: t('cat_domain'), max: 100 },
                        { name: t('cat_cert'), max: 100 },
                      ]
                  ),
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
                  splitLine: {
                    lineStyle: {
                      color: chartSplitLineColor,
                      width: 1,
                    },
                  },
                  splitArea: {
                    show: true,
                    areaStyle: {
                      color: isDark ? [
                        'rgba(79, 70, 229, 0.03)',
                        'rgba(79, 70, 229, 0.01)',
                      ] : [
                        'rgba(79, 70, 229, 0.05)',
                        'rgba(79, 70, 229, 0.02)',
                      ],
                    },
                  },
                  axisLine: {
                    lineStyle: {
                      color: chartAxisColor,
                    },
                  },
                },
                series: [
                  {
                    type: 'radar',
                    data: [
                      {
                        value: Object.keys(match_breakdown).length > 0
                          ? Object.values(match_breakdown).map((score: any) => score)
                          : [80, 70, 75, 60, 40],
                        name: t('match_level'),
                        areaStyle: {
                          color: {
                            type: 'radial',
                            x: 0.5,
                            y: 0.5,
                            r: 0.5,
                            colorStops: [
                              { offset: 0, color: 'rgba(79, 70, 229, 0.4)' },
                              { offset: 0.5, color: 'rgba(14, 165, 233, 0.3)' },
                              { offset: 1, color: 'rgba(16, 185, 129, 0.2)' },
                            ],
                          },
                          shadowColor: 'rgba(79, 70, 229, 0.3)',
                          shadowBlur: 20,
                        },
                        lineStyle: {
                          color: '#4f46e5',
                          width: 2,
                          shadowColor: 'rgba(79, 70, 229, 0.5)',
                          shadowBlur: 10,
                        },
                        label: {
                          show: true,
                          formatter: (params: any) => `${params.value}%`,
                          color: '#fff',
                          fontSize: 11,
                          fontWeight: 900,
                          distance: 10,
                          backgroundColor: 'rgba(79, 70, 229, 0.9)',
                          borderRadius: 4,
                          padding: [3, 6],
                        },
                        itemStyle: {
                          color: '#4f46e5',
                          borderColor: '#fff',
                          borderWidth: 2,
                          shadowColor: 'rgba(79, 70, 229, 0.6)',
                          shadowBlur: 8,
                        },
                        emphasis: {
                          label: {
                            show: true,
                            fontSize: 13,
                            fontWeight: 900,
                          },
                          areaStyle: {
                            color: 'rgba(79, 70, 229, 0.85)',
                            shadowBlur: 30,
                          },
                          lineStyle: {
                            width: 3,
                          },
                          itemStyle: {
                            borderWidth: 3,
                            shadowBlur: 15,
                          },
                        },
                      },
                    ],
                    animationDuration: 1500,
                    animationEasing: 'elasticOut',
                    animationDelay: 300,
                  },
                ],
                tooltip: {
                  trigger: 'item',
                  backgroundColor: 'rgba(0, 0, 0, 0.85)',
                  borderColor: '#4f46e5',
                  borderWidth: 1,
                  textStyle: {
                    color: '#fff',
                    fontSize: 12,
                  },
                  formatter: (params: any) => {
                    if (!params || !params.value) return '';
                    const indicator = params.name;
                    const value = Array.isArray(params.value) ? params.value : [params.value];
                    return `<div style="padding: 6px 10px;">
                      <strong style="color: #4f46e5;">${indicator}</strong><br/>
                      <span style="font-size: 14px;">${value[0]}%</span>
                    </div>`;
                  },
                },
              }}
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'svg' }}
              notMerge={true}
              lazyUpdate={true}
            />
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

            {/* Growth Forecast */}
            {(!!gapResult.potential_match_pct || !!gapResult.salary_growth_pct) && (
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

        {/* ── Processing Indicator (Progressive Loading) ──────────────────── */}
        {isProcessing && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className={styles.processingIndicator}
          >
            <Loader2 className={styles.spinIcon} size={16} />
            <span className={styles.processingText}>
              {processMessage || t('ai_searching')}
            </span>
          </motion.div>
        )}

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
            {skill_gaps.length > 0 && (
              <div className={styles.impactChartSection} style={{ gridColumn: '1 / -1' }}>
                <div className={styles.impactChartHeader}>
                  <h3 className={styles.impactChartTitle}>
                    <BarChart3 size={18} />
                    {t('skill_impact_analysis')}
                  </h3>
                </div>
                <div className={styles.impactChartContainer}>
                  <ReactECharts
                    option={{
                      tooltip: {
                        trigger: 'axis',
                        axisPointer: { type: 'shadow' },
                        backgroundColor: chartTooltipBg,
                        borderColor: '#4f46e5',
                        borderWidth: 1,
                        textStyle: { color: chartTooltipText }
                      },
                      legend: {
                        data: [t('match_impact'), t('salary_impact')],
                        textStyle: { color: chartTextColor, fontSize: 10 },
                        top: 0
                      },
                      grid: {
                        left: '3%',
                        right: '4%',
                        bottom: '3%',
                        top: '40px',
                        containLabel: true
                      },
                      xAxis: {
                        type: 'value',
                        axisLabel: { color: chartTextColor, fontSize: 10 },
                        splitLine: { lineStyle: { color: chartSplitLineColor } }
                      },
                      yAxis: {
                        type: 'category',
                        data: skill_gaps.map(g => g.skill).reverse(),
                        axisLabel: { 
                          color: chartTextColor, 
                          fontSize: 11,
                          width: 100,
                          overflow: 'truncate'
                        },
                        axisLine: { lineStyle: { color: chartAxisColor } }
                      },
                      series: [
                        {
                          name: t('match_impact'),
                          type: 'bar',
                          data: skill_gaps.map(g => g.match_impact || 0).reverse(),
                          itemStyle: {
                            color: {
                              type: 'linear',
                              x: 0, y: 0, x2: 1, y2: 0,
                              colorStops: [
                                { offset: 0, color: '#4f46e5' },
                                { offset: 1, color: '#0ea5e9' }
                              ]
                            },
                            borderRadius: [0, 4, 4, 0]
                          },
                          barWidth: '30%'
                        },
                        {
                          name: t('salary_impact'),
                          type: 'bar',
                          data: skill_gaps.map(g => g.salary_impact || 0).reverse(),
                          itemStyle: {
                            color: {
                              type: 'linear',
                              x: 0, y: 0, x2: 1, y2: 0,
                              colorStops: [
                                { offset: 0, color: '#10b981' },
                                { offset: 1, color: '#34d399' }
                              ]
                            },
                            borderRadius: [0, 4, 4, 0]
                          },
                          barWidth: '30%'
                        }
                      ]
                    }}
                    style={{ height: '100%', width: '100%' }}
                    opts={{ renderer: 'svg' }}
                    notMerge={true}
                    lazyUpdate={true}
                  />
                </div>
              </div>
            )}
            
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
                      {t(`severity_${gap.severity?.toLowerCase()}` as any)}
                    </span>
                  </div>
                  <div className={styles.gapCardMeta}>
                    {gap.required_level && (
                      <span className={styles.gapLevel}>
                         {t('level_label')} <b>{
                           t(`level_${gap.required_level?.toLowerCase()}` as any).startsWith('level_') 
                           ? gap.required_level 
                           : t(`level_${gap.required_level?.toLowerCase()}` as any)
                         }</b>
                      </span>
                    )}
                    <span className={styles.gapMonths}>
                      <Clock size={12} />
                      ~{gap.estimated_months ?? 1} {t("months_short")}
                    </span>
                    {gap.gap_type && <span className={styles.gapType}>{gap.gap_type}</span>}
                    {gap.is_critical && <span className={styles.criticalTag}>{t('critical')}</span>}
                  </div>

                  {/* Impact Values - NEW */}
                  {(!!gap.match_impact || !!gap.salary_impact) && (
                    <div className={styles.gapImpact}>
                      {!!gap.match_impact && (
                        <span className={styles.impactBadge} style={{ background: 'rgba(79, 70, 229, 0.1)', color: '#4f46e5' }}>
                          <Target size={12} />
                          +{gap.match_impact}% {t('match')}
                        </span>
                      )}
                      {!!gap.salary_impact && (
                        <span className={styles.impactBadge} style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}>
                          <TrendingUp size={12} />
                          +{gap.salary_impact}% {t('salary_text')}
                        </span>
                      )}
                    </div>
                  )}

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
                  <p>{t('no_tutorials')}</p>
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
                                  <span>{t('week_text')} {m.week}: {m.milestone}</span>
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

        {/* ── Feedback Section ────────────────────────────────────────────── */}
        {gapResult && gapResult.analysis_id && (
          <FeedbackSection 
            analysisId={gapResult.analysis_id} 
            hasFeedback={gapResult.has_feedback}
            isCached={gapResult.is_cached}
          />
        )}
      </PageContainer>
  );
};

export default UserRecommendPage;

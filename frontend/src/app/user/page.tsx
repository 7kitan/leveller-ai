"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { UserRole } from "@/types/roles";
import {
  UploadCloud,
  TrendingUp,
  Award,
  BowArrow,
  ArrowRight,
  AppWindow,
  Layers,
  Rocket,
  Network,
  ChevronRight as ChevronRightIcon,
  Target,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { cn, formatPercent } from "@/lib/utils";
import styles from "./user-dashboard.module.css";
import { motion } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";
import CourseCard from "@/components/user/CourseCard";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";
import { 
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, 
  CartesianGrid, Tooltip as RechartsTooltip, Cell, Legend
} from "recharts";

const icons = [BowArrow, AppWindow, Layers, Rocket, Network];

const UserDashboard = () => {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [marketData, setMarketData] = useState<any>(null);
  const [latestAnalysis, setLatestAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [iconIndex, setIconIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setIconIndex((prev) => (prev + 1) % icons.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const [period, setPeriod] = useState("month");

  useEffect(() => {
    if (!user) return;
    const fetchData = async () => {
      try {
        const [marketFitRes, latestRes] = await Promise.all([
          api.get(`analysis/market-fit?period=${period}`),
          api.get("analysis/user/latest"),
        ]);
        setMarketData(marketFitRes.data);
        setLatestAnalysis(latestRes.data);
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [ period]);

  interface JobCard {
    id: number;
    title: string;
    company: string;
    location: string;
    match: string;
    skills: string[];
  }

  const Sparkline = ({ data }: { data: any[] }) => {
    if (!data || data.length < 2) return null;
    const maxDemand = Math.max(...data.map(d => d.demand)) || 100;
    const minDemand = Math.min(...data.map(d => d.demand)) || 0;
    const range = maxDemand - minDemand || 1;
    
    const points = data.map((d, i) => {
      const x = (i / (data.length - 1)) * 100;
      const y = 100 - ((d.demand - minDemand) / range) * 80 - 10; // 10% padding
      return `${x},${y}`;
    }).join(" ");

    return (
      <svg className={styles.sparkline} viewBox="0 0 100 100" preserveAspectRatio="none">
        <polyline
          fill="none"
          stroke="var(--color-accent-primary)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points}
          style={{ opacity: 0.6 }}
        />
      </svg>
    );
  };

  // Map API courses to job card format
  const rawCourses = marketData?.courses?.length > 0 
    ? marketData.courses 
    : (latestAnalysis?.course_recommendations || []);

  const courses = rawCourses.map((c: any, i: number) => ({
    id: i + 1,
    title: c.title || t("nav_courses"),
    platform: c.platform || t("platform_default"),
    match: c.similarity
      ? `${Math.round(parseFloat(c.similarity) * 100)}%`
      : `${Math.round(parseFloat(c.rank_score || 0) * 100)}%`,
    skills: (c.tags || c.skills || []).slice(0, 3),
    url: c.url,
    level: c.level,
    is_certification: c.is_certification,
  }));

  const stats = [
    {
      label: t("dash_suggested_courses"),
      value: loading ? "..." : String(marketData?.matched_jobs ?? "0"),
      icon: Target,
    },
    {
      label: t("cv_match_score"),
      value: loading ? "..." : formatPercent(marketData?.market_fit_pct || 0),
      icon: TrendingUp,
    },
  ];

  const topGaps = (latestAnalysis?.skill_gaps || []).slice(0, 4);

  return (
    <AuthGuard requireRole={UserRole.USER}>
      <PageContainer>
        <PageHeader 
          title={t("dash_hub_title")}
          subtitle={t("dash_hub_subtitle")}
        />

        {/* Bento Grid Top Layer */}
        <div className={styles.bentoGrid}>
          {/* CV Section */}
          <div className={cn(styles.card, styles.uploadCard)}>
            <div className={styles.uploadIcon}>
              <UploadCloud size={32} />
            </div>
            <p className={styles.headerSubtitle} style={{ textAlign: "center", marginBottom: "1rem" }}>
              {t("dash_cv_subtitle")}
            </p>
            <Link href="/user/cv" className={styles.uploadBtn}>
              {t("dash_cv_btn")}
            </Link>
          </div>

          {/* Gap Analysis Summary */}
          <div className={cn(styles.card, styles.statsSection)}>
            <div className={styles.sectionHeader}>
              <h3 className="text-subheading">{t("dash_gap_analysis_title")}</h3>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <Link href="/user/analysis" className={styles.viewAllLink}>
                  {t("dash_view_details")} <ArrowRight size={16} />
                </Link>
              </div>
            </div>

            <div className={styles.gapGrid}>
              {topGaps.length > 0 ? (
                topGaps.map((gap: any) => (
                  <div key={gap.skill} className={styles.gapMiniCard}>
                    <div className={styles.gapMiniTitle}>{gap.skill}</div>
                    <div className={styles.gapMiniMeta}>
                      <span 
                        className={styles.miniSeverity}
                        style={{
                          color: severityColor(gap.severity),
                          backgroundColor: `${severityColor(gap.severity)}15`,
                          borderColor: `${severityColor(gap.severity)}30`,
                        }}
                      >
                        ● {t(`severity_${gap.severity?.toLowerCase()}` as any)}
                      </span>
                      <span className={styles.learningEffort}>
                        · {gap.learning_effort} {t("learning_effort")}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className={styles.emptyStateCenter}>
                  <Target size={40} className={styles.emptyIcon} />
                  <p>{t("dash_no_gaps")}</p>
                </div>
              )}
            </div>

            {/* Growth Forecast Section */}
            {(marketData?.potential_match_pct > 0 || marketData?.salary_growth_pct > 0) && (
              <div className={styles.forecastSection}>
                <div className={styles.forecastDivider} />
                <div className={styles.forecastGrid}>
                  <div className={styles.forecastItem}>
                    <div className={styles.forecastLabel}>
                      <Target size={14} className="text-accent" />
                      {t("dash_potential_match")}
                    </div>
                    <div className={styles.forecastValue}>
                      {formatPercent(marketData.potential_match_pct)}
                      <span className={styles.growthBadge}>
                        +{formatPercent(marketData.potential_match_pct - (marketData.market_fit_pct || 0))}
                      </span>
                    </div>
                  </div>
                  <div className={styles.forecastItem}>
                    <div className={styles.forecastLabel}>
                      <TrendingUp size={14} className="text-success" />
                      {t("dash_salary_boost")}
                    </div>
                    <div className={styles.forecastValue}>
                      +{formatPercent(marketData.salary_growth_pct)}
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className={styles.bottomStats}>
              {stats.map((stat) => (
                <div key={stat.label} className={styles.bottomStatItem}>
                  <div className={styles.bottomStatValue}>{stat.value}</div>
                  <div className={styles.bottomStatLabel}>{stat.label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className={cn(styles.card, styles.trendsCard)}>
            <div className={styles.trendHeader}>
              <h3 className="text-subheading">{t("dash_market_trends")}</h3>
              <div className={styles.periodSelector}>
                {['day', 'week', 'month'].map((p) => (
                  <button 
                    key={p} 
                    className={cn(styles.periodBtn, period === p && styles.active)}
                    onClick={() => setPeriod(p)}
                  >
                    {t(`period_${p === 'day' ? '24h' : p === 'week' ? '7d' : '30d'}` as any)}
                  </button>
                ))}
              </div>
            </div>

            <div className={styles.marketSnapshot}>
              <div className={styles.snapshotItem}>
                <div className={styles.snapshotLabel}>{t("nav_jobs")}</div>
                <div className={styles.snapshotValue}>{loading ? "..." : (marketData?.total_jobs?.toLocaleString() || "0")}</div>
              </div>
              <div className={styles.snapshotItem}>
                <div className={styles.snapshotLabel}>{t("dash_hot_trend")}</div>
                <div className={cn(styles.snapshotValue, "text-success")}>{loading ? "..." : (marketData?.market_trends?.summary?.top_gainer || t("not_available"))}</div>
              </div>
            </div>
            <div className={styles.barChartContainer} style={{ height: '400px', width: '100%', marginTop: '2rem' }}>
              {(marketData?.market_trends?.trends || []).length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart 
                    data={(() => {
                      const trends = marketData.market_trends.trends.slice(0, 5);
                      // Pivot data for Recharts: array of { date, skillA, skillB, ... }
                      const dates = Array.from(new Set(trends.flatMap((t: any) => (t.history || []).map((h: any) => h.date)))).sort();
                      return dates.map(date => {
                        const entry: any = { date };
                        trends.forEach((t: any) => {
                          const h = (t.history || []).find((hi: any) => hi.date === date);
                          if (h) entry[t.name] = h.demand;
                        });
                        return entry;
                      });
                    })()} 
                    margin={{ top: 20, right: 20, left: 0, bottom: 0 }}
                  >
                    <defs>
                      {[
                        { id: 'Emerald', color: '#10b981' },
                        { id: 'Indigo', color: '#6366f1' },
                        { id: 'Amber', color: '#f59e0b' },
                        { id: 'Sky', color: '#0ea5e9' },
                        { id: 'Pink', color: '#ec4899' }
                      ].map(g => (
                        <linearGradient key={g.id} id={`color${g.id}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={g.color} stopOpacity={0.2}/>
                          <stop offset="95%" stopColor={g.color} stopOpacity={0}/>
                        </linearGradient>
                      ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                    <XAxis 
                      dataKey="date" 
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: 'var(--color-text-muted)', fontSize: 10, fontWeight: 'bold' }}
                      minTickGap={40}
                    />
                    <YAxis 
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: 'var(--color-text-muted)', fontSize: 10, fontWeight: 'bold' }}
                    />
                    <Legend 
                      verticalAlign="top" 
                      align="right" 
                      height={36} 
                      iconType="circle"
                      wrapperStyle={{ fontSize: '12px', fontWeight: 'bold', opacity: 0.8 }}
                    />
                    <RechartsTooltip 
                      contentStyle={{ 
                        backgroundColor: 'rgba(0,0,0,0.85)', 
                        borderRadius: '16px', 
                        border: 'none',
                        backdropFilter: 'blur(10px)',
                        boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
                        color: '#fff'
                      }}
                    />
                    {(marketData.market_trends.trends || []).slice(0, 5).map((skill: any, idx: number) => {
                      const palettes = [
                        { id: 'Emerald', color: '#10b981' },
                        { id: 'Indigo', color: '#6366f1' },
                        { id: 'Amber', color: '#f59e0b' },
                        { id: 'Sky', color: '#0ea5e9' },
                        { id: 'Pink', color: '#ec4899' }
                      ];
                      const p = palettes[idx % palettes.length];
                      return (
                        <Area 
                          key={skill.name}
                          type="monotone" 
                          dataKey={skill.name} 
                          stroke={p.color} 
                          strokeWidth={3}
                          fillOpacity={1} 
                          fill={`url(#color${p.id})`} 
                          animationDuration={1500}
                        />
                      );
                    })}
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', opacity: 0.5 }}>
                  <p>{t("loading")}...</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Course Grid Layer */}
        <div className={styles.verticalStack8}>
          <div className={styles.jobListHeader}>
            <h2 className={styles.jobListTitle}>{t("dash_suggested_courses")}</h2>
            <Link href="/user/recommend" className={styles.viewAllLink}>
              {t("dash_view_all")} <ArrowRight size={16} />
            </Link>
          </div>

          <div className={styles.jobGrid}>
            {loading ? (
              <div className={styles.jobCard} style={{ gridColumn: 'span 3', alignItems: 'center', justifyContent: 'center', opacity: 0.3 }}>
                <p>{t("loading")}...</p>
              </div>
            ) : courses.length > 0 ? (
              courses.slice(0, 6).map((course: any, idx: number) => (
                <CourseCard key={course.id} course={course} index={idx} />
              ))
            ) : (
              <div className={styles.jobCard} style={{ gridColumn: 'span 3', alignItems: 'center', justifyContent: 'center', opacity: 0.5 }}>
                <p>{t("dash_no_courses")}</p>
              </div>
            )}
          </div>
        </div>

        {/* CTA Section */}
        <div className={cn(styles.card, styles.ctaCard)}>
          <div className={styles.ctaContent}>
            <h2 className={styles.ctaTitle}>
              {t("dash_cta_title")}
            </h2>
            <p className={styles.headerSubtitle} style={{ color: "inherit", opacity: 0.8 }}>
              {t("dash_cta_sub")}
            </p>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
              <Link href="/user/analysis" className={styles.ctaMainBtn}>
                {t("dash_cta_btn")} <ArrowRight size={20} />
              </Link>
            </div>
          </div>

          <div className={styles.radarContainer}>
            <div className={styles.radarScan} />
            <div className={styles.bowArrowIcon}>
              <motion.div
                key={iconIndex}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.5 }}
              >
                {React.createElement(icons[iconIndex])}
              </motion.div>
            </div>
          </div>
        </div>
      </PageContainer>
    </AuthGuard>
  );
};

/* -- Helpers ------------------------------------------------------------- */
function severityColor(sev: string) {
  const map: Record<string, string> = {
    HIGH: "#f43f5e",
    MEDIUM: "#f59e0b",
    LOW: "#10b981",
  };
  return map[sev?.toUpperCase()] || "#9ca3af";
}

export default UserDashboard;




"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
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
import { cn } from "@/lib/utils";
import styles from "./user-dashboard.module.css";
import { motion } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";
import CourseCard from "@/components/user/CourseCard";

const icons = [BowArrow, AppWindow, Layers, Rocket, Network];

const UserDashboard = () => {
  const { token } = useAuth();
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

  useEffect(() => {
    if (!token) return;
    const fetchData = async () => {
      try {
        const [marketRes, latestRes] = await Promise.all([
          axios.get("/api/analysis/market-fit", { headers: { Authorization: `Bearer ${token}` } }),
          axios.get("/api/analysis/user/latest", { headers: { Authorization: `Bearer ${token}` } }),
        ]);
        setMarketData(marketRes.data);
        setLatestAnalysis(latestRes.data);
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  interface JobCard {
    id: number;
    title: string;
    company: string;
    location: string;
    match: string;
    skills: string[];
  }

  // Map API courses to job card format
  const rawCourses = marketData?.courses?.length > 0 
    ? marketData.courses 
    : (latestAnalysis?.course_recommendations || []);

  const courses = rawCourses.map((c: any, i: number) => ({
    id: i + 1,
    title: c.title || t("nav_courses"),
    platform: c.platform || "E-learning",
    match: c.rank_score
      ? `${Math.round(parseFloat(c.rank_score) * 100)}%`
      : `${Math.round(parseFloat(c.similarity || 0) * 100)}%`,
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
      value: loading ? "..." : `${marketData?.market_fit_pct || 0}%`,
      icon: TrendingUp,
    },
    {
      label: t("nav_jobs"),
      value: loading ? "..." : String(marketData?.total_jobs || "0"),
      icon: Award,
    },
  ];

  const topGaps = (latestAnalysis?.skill_gaps || []).slice(0, 4);

  return (
    <AuthGuard requireRole="user">
      <div className={styles.pageRoot}>
        {/* Header */}
        <div className={styles.headerSection}>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h1 className={styles.headerTitle}>{t("dash_hub_title")}</h1>
            <p className={styles.headerSubtitle}>
              {t("dash_hub_subtitle")}
            </p>
          </motion.div>
        </div>

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
                      <span className={cn(styles.miniSeverity, styles[gap.severity?.toLowerCase()])}>
                        ● {gap.severity}
                      </span>
                      <span>· {gap.learning_effort} {t("learning_effort")}</span>
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
                      {marketData.potential_match_pct}%
                      <span className={styles.growthBadge}>
                        +{marketData.potential_match_pct - (marketData.market_fit_pct || 0)}%
                      </span>
                    </div>
                  </div>
                  <div className={styles.forecastItem}>
                    <div className={styles.forecastLabel}>
                      <TrendingUp size={14} className="text-success" />
                      {t("dash_salary_boost")}
                    </div>
                    <div className={styles.forecastValue}>
                      +{marketData.salary_growth_pct}%
                    </div>
                  </div>
                </div>
                {marketData.market_sentiment && (
                  <div className={styles.sentimentBox}>
                    <Sparkles size={14} className="text-warning" />
                    <span>{t("dash_market_sentiment")}: <strong>{marketData.market_sentiment}</strong></span>
                  </div>
                )}
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

          {/* Market Trends Section */}
          <div className={cn(styles.card, styles.trendsCard)}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 className="text-subheading">{t("dash_market_trends")}</h3>
              <Sparkles size={20} className="text-accent" />
            </div>
            <div className={styles.trendsList}>
              {(marketData?.top_trending_skills || []).length > 0 ? (
                (marketData.top_trending_skills).map((skill: any) => (
                  <div key={skill.name} className={styles.trendItem}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div className={styles.trendSkillInfo}>
                        <span className="font-label">{skill.name}</span>
                        <span className={styles.trendSalary}>
                          ~{(skill.growth * 2 + 20).toFixed(0)}M VND
                        </span>
                      </div>
                      <span className={styles.trendGrowthBadge}>
                        +{skill.growth}%
                      </span>
                    </div>
                    <div className={styles.progressBar}>
                      <div 
                        className={styles.progressFill} 
                        style={{ width: `${skill.demand}%` }} 
                      />
                    </div>
                  </div>
                ))
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
      </div>
    </AuthGuard>
  );
};

export default UserDashboard;

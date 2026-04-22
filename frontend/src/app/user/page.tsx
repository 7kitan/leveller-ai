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
  const courses = (marketData?.courses || []).map((c: any, i: number) => ({
    id: i + 1,
    title: c.title || t("nav_courses"),
    platform: c.platform || "E-learning",
    match: c.rank_score
      ? `${Math.round(parseFloat(c.rank_score) * 100)}%`
      : `${Math.round(parseFloat(c.similarity || 0) * 100)}%`,
    skills: (c.tags || []).slice(0, 3),
    url: c.url,
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
          <div className={cn(styles.card, styles.statsSection)} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 className="text-subheading">{t("dash_gap_analysis_title")}</h3>
              <Link href="/user/analysis" className={styles.viewAllLink}>
                {t("dash_view_details")} <ArrowRight size={16} />
              </Link>
            </div>

            {topGaps.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                {topGaps.map((gap: any) => (
                  <div key={gap.skill} style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '1rem', border: '1px solid var(--color-border-subtle)' }}>
                    <div className="font-label" style={{ marginBottom: '0.25rem' }}>{gap.skill}</div>
                    <div className="font-meta">
                      <span style={{ color: gap.severity === 'HIGH' ? 'var(--color-danger)' : 'var(--color-warning)' }}>
                        ● {gap.severity}
                      </span>
                      <span>· {gap.learning_effort} {t("learning_effort")}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', opacity: 0.5 }}>
                <Target size={40} style={{ marginBottom: '1rem' }} />
                <p>{t("dash_no_gaps")}</p>
              </div>
            )}

            <div className={styles.statsGrid}>
              {stats.map((stat) => (
                <div key={stat.label} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <div className={styles.statValue}>{stat.value}</div>
                  <div className={styles.statLabel}>{stat.label}</div>
                </div>
              ))}
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
            {courses.length > 0 ? (
              courses.slice(0, 6).map((course: any) => (
                <div key={course.id} className={styles.jobCard}>
                  <div className={styles.platformBadge}>{course.platform}</div>
                  <h3 className={styles.jobTitle}>{course.title}</h3>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: 'auto' }}>
                    {course.skills.map((s: string) => (
                      <span key={s} className={styles.skillBadge}>{s}</span>
                    ))}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span className="font-micro">{t("dash_match_score")}</span>
                      <span style={{ color: 'var(--color-success)', fontWeight: 800 }} className="text-subheading">{course.match}</span>
                    </div>
                    {course.url && (
                      <a href={course.url} target="_blank" rel="noopener noreferrer" className={styles.viewAllLink} style={{ color: 'inherit' }}>
                        {t("dash_learn_now")} <ArrowRight size={14} />
                      </a>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className={styles.jobCard} style={{ gridColumn: 'span 3', alignItems: 'center', justifyContent: 'center', opacity: 0.5 }}>
                <p>{t("dash_no_courses")}</p>
              </div>
            )
            }
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

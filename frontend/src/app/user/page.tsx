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
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import styles from "./user-dashboard.module.css";
import { motion } from "framer-motion";

const icons = [BowArrow, AppWindow, Layers, Rocket, Network];

const UserDashboard = () => {
  const { token } = useAuth();
  const [marketData, setMarketData] = useState<any>(null);
  const [loadingMarket, setLoadingMarket] = useState(true);
  const [iconIndex, setIconIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setIconIndex((prev) => (prev + 1) % icons.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!token) return;
    const fetchMarketFit = async () => {
      try {
        const res = await axios.get("/api/analysis/market-fit", {
          headers: { Authorization: `Bearer ${token}` },
        });
        setMarketData(res.data);
      } catch (err) {
        console.error("Market Fit error:", err);
      } finally {
        setLoadingMarket(false);
      }
    };
    fetchMarketFit();
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
  const matchedJobs: JobCard[] = (marketData?.courses || []).map((c: any, i: number) => ({
    id: i + 1,
    title: c.title || "Khóa học kỹ năng",
    company: c.platform || "E-learning",
    location: c.level || "Online",
    match: c.rank_score
      ? `${Math.round(parseFloat(c.rank_score) * 100)}%`
      : `${Math.round(parseFloat(c.similarity || 0) * 100)}%`,
    skills: (c.tags || []).slice(0, 4),
  }));

  // Fallback: show placeholder if no courses
  const displayJobs =
    matchedJobs.length > 0
      ? matchedJobs
      : [
          {
            id: 1,
            title: "Chưa có khóa học được gợi ý",
            company: "Phân tích CV để nhận gợi ý",
            location: "",
            match: "—",
            skills: ["Upload CV để bắt đầu"],
          },
        ];

  const stats = [
    {
      label: "Khóa học gợi ý",
      value: loadingMarket ? "..." : String(marketData?.matched_jobs ?? "0"),
      icon: Target,
    },
    {
      label: "CV Match Score",
      value: loadingMarket ? "..." : `${marketData?.market_fit_pct || 0}%`,
      icon: TrendingUp,
    },
    {
      label: "Tổng việc làm",
      value: loadingMarket ? "..." : String(marketData?.total_jobs || "0"),
      icon: Award,
    },
  ];

  return (
    <AuthGuard requireRole="user">
      <div className={styles.pageRoot}>
        {/* Header */}
        <div className={styles.headerSection}>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h1 className={styles.headerTitle}>User Hub.</h1>
            <p className={styles.headerSubtitle}>
              Giải mã khoảng trống kỹ năng và kết nối với cơ hội tương xứng trên quy mô toàn cầu.
            </p>
          </motion.div>
        </div>

        {/* Bento Grid Top Layer */}
        <div className={styles.bentoGrid}>
          {/* CV Card */}
          <div className={cn(styles.card, styles.uploadCard)}>
            <div className={styles.uploadIcon}>
              <UploadCloud size={32} />
            </div>
            <h3 className={styles.uploadTitle}>CV Insight</h3>
            <p className={styles.headerSubtitle} style={{ fontSize: "0.9rem", textAlign: "center", marginBottom: "1rem" }}>
              Cập nhật hồ sơ để nhận phân tích mới nhất.
            </p>
            <Link href="/user/cv" className={styles.uploadBtn}>
              PHÂN TÍCH CV
            </Link>
          </div>

          {/* Stats Section */}
          <div className={cn(styles.card, styles.statsSection)}>
            <div className={styles.statsGrid}>
              {stats.map((stat) => (
                <div key={stat.label} className={styles.statCard}>
                  <stat.icon size={24} color="var(--color-accent-primary)" />
                  <div>
                    <div className={styles.statValue}>{stat.value}</div>
                    <div className={styles.statLabel}>{stat.label}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Course Grid Layer */}
        <div className={styles.verticalStack8}>
          <div className={styles.jobListHeader}>
            <h2 className={styles.jobListTitle}>Khóa học gợi ý</h2>
            <Link href="/user/analysis" className={styles.viewAllLink}>
              Phân tích gap ngay
            </Link>
          </div>

          <div className={styles.jobGrid}>
            {displayJobs.map((job) => (
              <div key={job.id} className={styles.jobCard}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <h3 className={styles.jobTitle}>{job.title}</h3>
                  <span style={{ color: "var(--color-success)", fontWeight: 800 }}>{job.match}</span>
                </div>

                <div style={{ display: "flex", gap: "1rem", fontSize: "0.8rem", opacity: 0.6 }}>
                  <span>{job.company}</span>
                  <span>{job.location}</span>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                  {job.skills.map((s: string) => (
                    <span key={s} className={styles.skillBadge}>{s}</span>
                  ))}
                </div>

                <Link
                  href="/user/analysis"
                  style={{ marginTop: "auto", display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 700, fontSize: "0.9rem" }}
                >
                  Gap Analysis <ArrowRight size={16} />
                </Link>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className={cn(styles.card, styles.ctaCard)}>
          <div className={styles.ctaContent}>
            <h2 className={styles.ctaTitle}>
              Thấu hiểu bản thân.<br />Làm chủ lộ trình.
            </h2>
            <p className={styles.headerSubtitle} style={{ color: "inherit", opacity: 0.8 }}>
              Sử dụng AI để so sánh hàng nghìn tham số giữa hồ sơ của bạn và yêu cầu thực tế từ thị trường.
            </p>
            <Link href="/user/analysis" className={styles.ctaMainBtn}>
              Thử phân tích ngay <ChevronRightIcon size={20} />
            </Link>
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

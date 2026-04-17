"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import {
  UploadCloud,
  TrendingUp,
  Award,
  Sparkles,
  ArrowRight,
  ChevronRight as ChevronRightIcon,
  Target,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import styles from "./user-dashboard.module.css";
import { motion } from "framer-motion";

const UserDashboard = () => {
  const { token } = useAuth();
  const [marketData, setMarketData] = useState<any>(null);
  const [loadingMarket, setLoadingMarket] = useState(true);

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

  const matchedJobs = [
    { id: 1, title: "Senior Backend Engineer", company: "Aura Tech", location: "Hồ Chí Minh", match: "92%", skills: ["FastAPI", "Neo4j", "Docker"] },
    { id: 2, title: "DevOps Architect", company: "Cloud Nexus", location: "Hà Nội", match: "85%", skills: ["Kubernetes", "AWS", "Terraform"] },
    { id: 3, title: "Fullstack Developer", company: "Nexus AI", location: "Remote", match: "78%", skills: ["Next.js", "Python", "Redis"] },
  ];

  const stats = [
    { label: "Jobs Matched",      value: loadingMarket ? "..." : (marketData?.matched_jobs    || "0"),    icon: Target },
    { label: "Market Fit Ratio",  value: loadingMarket ? "..." : `${marketData?.market_fit_pct || 0}%`,  icon: TrendingUp },
    { label: "Database Coverage", value: loadingMarket ? "..." : (marketData?.total_jobs     || "0"),   icon: Award },
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
            <p className={styles.headerSubtitle} style={{fontSize: "0.9rem", textAlign: "center", marginBottom: "1rem"}}>Cập nhật hồ sơ để nhận phân tích mới nhất.</p>
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

        {/* Job Grid Layer */}
        <div className={styles.verticalStack8}>
          <div className={styles.jobListHeader}>
            <h2 className={styles.jobListTitle}>Top Matches</h2>
            <Link href="/user/jobs" className={styles.viewAllLink}>Xem tất cả</Link>
          </div>

          <div className={styles.jobGrid}>
            {matchedJobs.map((job) => (
              <div key={job.id} className={styles.jobCard}>
                <div style={{display: "flex", justifyContent: "space-between", alignItems: "flex-start"}}>
                   <h3 className={styles.jobTitle}>{job.title}</h3>
                   <span style={{color: "var(--color-success)", fontWeight: 800}}>{job.match}</span>
                </div>
                
                <div style={{display: "flex", gap: "1rem", fontSize: "0.8rem", opacity: 0.6}}>
                   <span>{job.company}</span>
                   <span>{job.location}</span>
                </div>
                
                <div style={{display: "flex", flexWrap: "wrap", gap: "0.5rem"}}>
                  {job.skills.map((s) => (
                    <span key={s} className={styles.skillBadge}>{s}</span>
                  ))}
                </div>

                <Link href="/user/analysis" style={{marginTop: "auto", display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 700, fontSize: "0.9rem"}}>
                   Gap Analysis <ArrowRight size={16} />
                </Link>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className={cn(styles.card, styles.ctaCard)}>
          <div className={styles.ctaContent}>
            <h2 className={styles.ctaTitle}>Thấu hiểu bản thân.<br/>Làm chủ lộ trình.</h2>
            <p className={styles.headerSubtitle} style={{color: "inherit", opacity: 0.8}}>
               Sử dụng AI để so sánh hàng nghìn tham số giữa hồ sơ của bạn và yêu cầu thực tế từ thị trường.
            </p>
            <Link href="/user/analysis" className={styles.ctaMainBtn}>
              Thử phân tích ngay <ChevronRightIcon size={20} />
            </Link>
          </div>

          <div className={styles.radarContainer}>
            <div className={styles.radarScan} />
            <motion.div 
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ repeat: Infinity, duration: 4 }}
              style={{ color: "var(--color-accent-primary)" }}
            >
              <Sparkles size={120} />
            </motion.div>
          </div>
        </div>

      </div>
    </AuthGuard>
  );
};

export default UserDashboard;

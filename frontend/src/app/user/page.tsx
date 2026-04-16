"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import {
  UploadCloud,
  MapPin,
  Briefcase,
  TrendingUp,
  Award,
  BarChart3,
  Flame,
  Sparkles,
  LineChart,
  ArrowRight,
  ChevronRight as ChevronRightIcon,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import styles from "./user-dashboard.module.css";
import { motion } from "framer-motion";

// ─── Stat icon helper ─────────────────────────────────────────────────────────
const Target = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
  </svg>
);

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
    { label: "Jobs Matched",      value: loadingMarket ? "..." : (marketData?.matched_jobs    || "0"),    icon: Target,     badge: "accent2" },
    { label: "Market Fit Ratio",  value: loadingMarket ? "..." : `${marketData?.market_fit_pct || 0}%`,  icon: TrendingUp, badge: "success" },
    { label: "Database Coverage", value: loadingMarket ? "..." : (marketData?.total_jobs     || "0"),   icon: Award,     badge: "danger"  },
  ];

  return (
    <AuthGuard requireRole="user">
       <div className={styles.pageRoot}>

        {/* ── Header + CV Upload ────────────────────────────────────────── */}
        <div className={styles.headerSection}>
          <div>
            <h1 className={styles.headerTitle}>User Hub.</h1>
            <p className={styles.headerSubtitle}>
              Giải mã khoảng trống kỹ năng và kết nối với cơ hội tương xứng trên quy mô toàn cầu.
            </p>
          </div>

          <div className={styles.uploadCard}>
            <div className={styles.centeredContent}>
              <div className={styles.uploadIcon}>
                <UploadCloud size={32} />
              </div>
              <h3 className={styles.uploadTitle}>Cập nhật CV mới nhất</h3>
              <p className={styles.uploadSub}>Kéo thả hoặc bấm để upload file (PDF hoặc Ảnh)</p>
              <Link href="/user/cv" className={styles.uploadBtn}>
                TẢI LÊN CV &amp; PHÂN TÍCH
              </Link>
            </div>
          </div>
        </div>

        {/* ── Stats ─────────────────────────────────────────────────────── */}
        <div className={styles.statsGrid}>
          {stats.map((stat) => (
            <div key={stat.label} className={styles.statCard}>
              <div className={styles.statIconWrapper}>
                <div className={cn(styles.statIconBox, styles[`statIconBox_${stat.badge}`])}>
                  <stat.icon size={24} />
                </div>
                <BarChart3 size={16} className={styles.statDecorativeIcon} />
              </div>
              <div className={styles.statValue}>{stat.value}</div>
              <div className={styles.statLabel}>{stat.label}</div>
            </div>
          ))}
        </div>

        {/* ── Hot Job Matches ─────────────────────────────────────────── */}
        <div className={styles.verticalStack8}>
          <div className={styles.jobListHeader}>
            <h2 className={styles.jobListTitle}>
              <Flame size={24} className={styles.iconRose} />
              Hot Job Matches
            </h2>
            <Link href="/user/jobs" className={styles.viewAllLink}>
              Xem tất cả
            </Link>
          </div>

          <div className={styles.jobGrid}>
            {matchedJobs.map((job) => (
              <div key={job.id} className={styles.jobCard}>
                <div className={styles.matchOverlay}>
                    <div className={styles.matchValue}>{job.match}</div>
                    <div className={styles.matchLabel}>Match</div>
                </div>

                <div>
                   <h3 className={styles.jobTitle}>{job.title}</h3>
                   <div className={styles.jobMeta}>
                     <span className={styles.metaItem}>
                       <Briefcase size={10} className={styles.iconIndigo} />
                       {job.company}
                     </span>
                     <span className={styles.metaItem}>
                       <MapPin size={10} className={styles.iconIndigo} />
                       {job.location}
                     </span>
                   </div>
                </div>
                
                <div className={styles.skillList}>
                  {job.skills.map((s) => (
                    <span key={s} className={styles.skillBadge}>{s}</span>
                  ))}
                </div>

                <Link href="/user/analysis" className={styles.jobActionBtn}>
                  <span>GAP ANALYSIS</span>
                  <ArrowRight size={14} className={styles.iconIndigo} />
                </Link>
              </div>
            ))}
          </div>
        </div>

        {/* ── Gap Analysis CTA ─────────────────────────────────────────── */}
        <div className={styles.ctaCard}>
          <div className={styles.ctaGlow} />

          <div className={styles.pingDecoration}>
            <div className={styles.pingCircle} />
            <div className={styles.pingCircle} style={{ animationDelay: "1s" }} />
          </div>

          <div className={styles.ctaContent}>
            <div className={styles.ctaBadge}>
              <Sparkles size={14} /> AI Powered Gap Engine
            </div>
            <h2 className={styles.ctaTitle}>
              Thấu hiểu điểm mạnh,<br/>làm chủ lộ trình.
            </h2>
            <div className={styles.ctaDesc}>
              Công cụ Gap Analysis so sánh hàng nghìn tham số giữa hồ sơ của bạn và yêu cầu thực tế từ thị trường để gợi ý các kỹ năng "chốt hạ".
              {marketData?.top_matching_roles?.length > 0 && (
                <span className={styles.ctaRoleMatch}>
                  Vai trò phù hợp nhất: {marketData.top_matching_roles.join(", ")}
                </span>
              )}
            </div>
            <Link href="/user/analysis" className={styles.ctaMainBtn}>
              Thử phân tích ngay <ChevronRightIcon size={20} />
            </Link>
          </div>

          <div className={styles.radarContainer}>
            <div className={styles.radarScan} />
            <div className={styles.radarRing} style={{ inset: "10%" }} />
            <div className={styles.radarRing} style={{ inset: "25%" }} />
            <div className={styles.radarRing} style={{ inset: "40%" }} />
            <div className={cn(styles.radarPoint, styles.iconEmerald)} style={{ top: "20%", left: "30%" }} />
            <div className={cn(styles.radarPoint, styles.iconIndigo)} style={{ top: "40%", right: "25%" }} />
            <div className={cn(styles.radarPoint, styles.iconAmber)} style={{ bottom: "30%", left: "40%" }} />
            
            <div className={styles.radarCenter}>
                <LineChart size={80} />
            </div>

            <div className={styles.radarStatus} style={{ top: "5%", right: "10%" }}>
              <span className={styles.radarStatusPulse}>Scanning...</span>
            </div>
            <div className={styles.radarStatus} style={{ bottom: "5%", left: "10%" }}>
              Matched 92%
            </div>
          </div>
        </div>

      </div>
    </AuthGuard>
  );
};

export default UserDashboard;

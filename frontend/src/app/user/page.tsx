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

// ─── Stat icon helper ─────────────────────────────────────────────────────────
const Target = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
  </svg>
);

// ─── Page ──────────────────────────────────────────────────────────────────────
import styles from "./user-dashboard.module.css";

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
    { label: "Jobs Matched",      value: loadingMarket ? "..." : (marketData?.matched_jobs    || "0"),    icon: Target,     badge: "accent-2" },
    { label: "Market Fit Ratio",  value: loadingMarket ? "..." : `${marketData?.market_fit_pct || 0}%`,  icon: TrendingUp, badge: "success" },
    { label: "Database Coverage", value: loadingMarket ? "..." : (marketData?.total_jobs     || "0"),   icon: Award,     badge: "danger"  },
  ];

  return (
    <AuthGuard requireRole="user">
       <div className={styles.pageRoot}>

        {/* ── Header + CV Upload ────────────────────────────────────────── */}
        <div className={styles.headerSection}>
          <div className="space-y-2">
            <h1 className={styles.headerTitle}>User Hub.</h1>
            <p className={styles.headerSubtitle}>
              Giải mã khoảng trống kỹ năng và kết nối với cơ hội tương xứng.
            </p>
          </div>

          <div className={styles.uploadCard}>
            <div className="flex flex-col items-center justify-center space-y-4 relative z-10">
              <div className={styles.uploadIcon}>
                <UploadCloud className="w-8 h-8" />
              </div>
              <div className="text-center">
                <h3 className="text-lg font-bold mb-1">Cập nhật CV mới nhất</h3>
                <p className="text-xs font-medium text-[hsl(var(--text-muted))]">Kéo thả hoặc bấm để upload file (PDF hoặc Ảnh)</p>
              </div>
              <Link href="/user/cv" className="btn btn-primary btn-full">
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
                <div className={`stat-icon stat-icon-${stat.badge}`}>
                  <stat.icon className="w-6 h-6" />
                </div>
                <BarChart3 className="w-4 h-4 text-[hsl(var(--text-muted))]" />
              </div>
              <div className={styles.statValue}>{stat.value}</div>
              <div className={styles.statLabel}>{stat.label}</div>
            </div>
          ))}
        </div>

        {/* ── Hot Job Matches ─────────────────────────────────────────── */}
        <div className="space-y-6">
          <div className={styles.jobListHeader}>
            <h2 className={styles.jobListTitle}>
              <Flame className="w-6 h-6 text-[hsl(var(--danger))]" />
              Hot Job Matches
            </h2>
            <Link href="/user/jobs" className={styles.viewAllLink}>
              Xem tất cả
            </Link>
          </div>

          <div className={styles.jobGrid}>
            {matchedJobs.map((job) => (
              <div key={job.id} className={styles.jobCard}>
                <div className="job-match-badge">
                  <div className="job-match-value">{job.match}</div>
                  <div className="job-match-label">MATCH</div>
                </div>

                <div className="job-body">
                  <h3 className="job-title">{job.title}</h3>
                  <div className="job-meta">
                    <span className="job-meta-item">
                      <Briefcase className="w-4 h-4" />{job.company}
                    </span>
                    <span className="job-meta-item">
                      <MapPin className="w-4 h-4" />{job.location}
                    </span>
                  </div>
                  <div className="job-tags">
                    {job.skills.map((s) => (
                      <span key={s} className="skill-tag">{s}</span>
                    ))}
                  </div>
                </div>

                <div className="p-6 md:pr-10 flex items-center">
                  <Link href="/user/analysis" className="btn btn-secondary">
                    GAP ANALYSIS <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Gap Analysis CTA ─────────────────────────────────────────── */}
        <div className={styles.ctaCard}>
          {/* Ambient glow */}
          <div className={styles.ctaGlow} />

          {/* Radar decoration */}
          <div className={styles.radarDecoration}>
            <div className="absolute inset-0 border border-[hsl(var(--accent)_/_0.3)] rounded-full animate-ping [animation-duration:4s]" />
            <div className="absolute inset-[20%] border border-[hsl(var(--accent-2)_/_0.2)] rounded-full animate-ping [animation-duration:6s]" />
            <div className="absolute inset-[40%] border border-[hsl(var(--accent)_/_0.1)] rounded-full animate-ping [animation-duration:8s]" />
          </div>

          <div className="flex flex-col lg:flex-row items-center gap-12 relative z-10">
            <div className="flex-1 space-y-6">
              <div className="section-label section-label-accent">
                <Sparkles className="w-4 h-4" /> AI Powered Gap Engine
              </div>
              <h2 className="text-3xl md:text-4xl font-black tracking-tight">
                Thấu hiểu điểm mạnh, làm chủ lộ trình.
              </h2>
              <p className="font-medium leading-relaxed max-w-xl text-[hsl(var(--text-secondary))]">
                Công cụ Gap Analysis của Lumix AI so sánh hàng nghìn tham số giữa hồ sơ của bạn và yêu cầu thực tế từ thị trường để gợi ý các kỹ năng "chốt hạ" giúp bạn nhận việc.
                {marketData?.top_matching_roles?.length > 0 && (
                  <span className="block mt-4 text-sm font-bold italic text-[hsl(var(--success))]">
                    Vai trò phù hợp nhất: {marketData.top_matching_roles.join(", ")}
                  </span>
                )}
              </p>
              <Link href="/user/analysis" className="btn btn-primary">
                Thử phân tích ngay <ChevronRightIcon className="w-5 h-5" />
              </Link>
            </div>

            {/* Radar visual */}
            <div className={styles.radarContainer}>
              <div className="radar-bg" />
              <div className={styles.radarRing} style={{ inset: "12%" }} />
              <div className={styles.radarRing} style={{ inset: "28%" }} />
              <div className={styles.radarRing} style={{ inset: "44%" }} />
              <div className="absolute inset-0 rounded-full animate-spin [animation-duration:4s] border-r-2 border-[hsl(var(--accent)_/_0.4)] bg-gradient-to-r from-transparent via-transparent to-[hsl(var(--accent)_/_0.05)]" />
              <div className={styles.radarPoint} style={{ top: "20%", left: "30%", background: "hsl(var(--accent-2))", boxShadow: "0 0 10px hsl(var(--accent-2))" }} />
              <div className={styles.radarPoint} style={{ top: "40%", right: "25%", background: "hsl(var(--accent))", boxShadow: "0 0 10px hsl(var(--accent))", animationDelay: "1s" }} />
              <div className={styles.radarPoint} style={{ bottom: "30%", left: "40%", background: "hsl(var(--success))", boxShadow: "0 0 10px hsl(var(--success))", animationDelay: "2s" }} />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="relative">
                  <div className="absolute inset-0 bg-[hsl(var(--accent)_/_0.2)] blur-2xl rounded-full" />
                  <LineChart className="w-20 h-20 text-[hsl(var(--text))] relative z-10" />
                </div>
              </div>
              <div className={styles.radarStatus} style={{ top: "2%", right: "5%" }}>Scanning...</div>
              <div className={styles.radarStatus} style={{ bottom: "2%", left: "5%" }}>Matched 92%</div>
            </div>
          </div>
        </div>

      </div>
    </AuthGuard>
  );
};

export default UserDashboard;

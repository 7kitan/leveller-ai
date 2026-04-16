"use client";

import React, { useState, useEffect } from "react";
import { 
  Sparkles, Zap, ArrowLeft, TrendingUp, 
  BarChart3, Globe, Briefcase, DollarSign,
  ChevronRight, Flame, Target, Star
} from "lucide-react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import styles from "./user-recommend.module.css";

interface TrendingSkill {
  skill_name: string;
  job_count: number;
  avg_salary_vnd: number | null;
}

interface Job {
  id: string;
  title_raw: string;
  company_name?: string;
}

export default function UserRecommendPage() {
  const { token } = useAuth();
  const [trendingSkills, setTrendingSkills] = useState<TrendingSkill[]>([]);
  const [featuredJobs, setFeaturedJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
        fetchData();
    }
  }, [token]);

  const fetchData = async () => {
    setLoading(true);
    try {
        const [skillRes, jobRes] = await Promise.all([
            axios.get("/api/recommend/trending-skills?days=30&limit=10", {
                headers: { "Authorization": `Bearer ${token}` }
            }),
            axios.get("/api/jd/search?limit=3", {
                headers: { "Authorization": `Bearer ${token}` }
            })
        ]);
        setTrendingSkills(skillRes.data);
        setFeaturedJobs(jobRes.data);
    } catch (err) {
        console.error("Lỗi fetch recommendation:", err);
    } finally {
        setLoading(false);
    }
  };

  const formatSalary = (val: number | null) => {
    if (!val) return "N/A";
    return (val / 1000000).toFixed(1) + "M";
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center">
        <div className="w-16 h-16 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin"></div>
        <p className="mt-4 text-cyan-400 font-bold animate-pulse uppercase tracking-widest text-xs">Phân tích thị trường...</p>
      </div>
    );
  }

  return (
    <div className={styles.pageRoot}>
      {/* Header Section */}
      <div className={styles.header}>
        <div className="space-y-4">
          <div className={styles.badgeHeader}>
            <Sparkles size={14} className="text-cyan-400" />
            <span className="text-cyan-400 text-[10px] font-black tracking-[0.2em] uppercase">Market Intelligence v2.0</span>
          </div>
          <h1 className={styles.title}>
            SMART <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-indigo-500">INSIGHTS.</span>
          </h1>
          <p className={styles.subtitle}>
            Tối ưu hóa sự nghiệp dựa trên dữ liệu thực tế từ thị trường lao động toàn cầu.
          </p>
        </div>

        <Link 
            href="/user" 
            className={styles.dashboardBtn}
        >
          <ArrowLeft className="w-4 h-4" /> Dashboard
        </Link>
      </div>

      <div className={styles.gridSystem}>
        {/* Left Column: Trending Skills Heatmap */}
        <div className="lg:col-span-8 space-y-8">
          <div className={`${styles.panel} ${styles.heatmapPanel}`}>
            <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:scale-110 transition-transform duration-1000">
                <TrendingUp size={120} />
            </div>
            
            <div className="flex items-center gap-4 mb-10 relative z-10">
                <div className="p-3 bg-cyan-500/20 rounded-xl">
                    <Flame className="text-cyan-400 w-6 h-6" />
                </div>
                <div>
                    <h2 className="text-2xl font-black text-white tracking-tight uppercase italic">Market Heatmap</h2>
                    <p className="text-white/30 text-xs font-bold uppercase tracking-widest">Top kỹ năng đang "khát" nhân lực nhất</p>
                </div>
            </div>

            <div className="space-y-6 relative z-10">
                {trendingSkills.map((skill, idx) => (
                    <motion.div 
                        key={idx}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className="group/item"
                    >
                        <div className="flex justify-between items-end mb-2">
                            <span className="text-white font-black italic uppercase text-sm group-hover/item:text-cyan-400 transition-colors">{skill.skill_name}</span>
                            <span className="text-white/40 text-[10px] font-black uppercase tracking-widest">
                                {skill.job_count} Jobs Available
                            </span>
                        </div>
                        <div className={styles.progressBarTrack}>
                            <motion.div 
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.min(100, (skill.job_count / (trendingSkills[0]?.job_count || 1)) * 100)}%` }}
                                transition={{ duration: 1.5, ease: "easeOut" }}
                                className={styles.progressBarFill}
                            />
                        </div>
                    </motion.div>
                ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
             <div className={`${styles.panel} ${styles.salaryPanel}`}>
                <div className="flex items-center gap-3 mb-6">
                    <DollarSign className="text-indigo-400" />
                    <h3 className="text-white font-black italic uppercase text-sm tracking-widest">Salary Benchmarks</h3>
                </div>
                <div className="space-y-4">
                    {trendingSkills.slice(0, 4).map((skill, idx) => (
                        <div key={idx} className="flex justify-between items-center py-3 border-b border-white/5 last:border-0">
                            <span className="text-white/60 text-xs font-bold">{skill.skill_name}</span>
                            <span className="text-indigo-400 font-black italic">avg. {formatSalary(skill.avg_salary_vnd)}</span>
                        </div>
                    ))}
                </div>
             </div>

             <div className={`${styles.panel} ${styles.infoPanel}`}>
                <div className="flex items-center gap-3 flex-col">
                  <Globe className="text-cyan-500 mb-4 animate-pulse" size={40} />
                  <h3 className="text-white font-black italic uppercase text-sm">Global Reach</h3>
                  <p className="text-white/30 text-xs mt-2 font-medium">Báo cáo dựa trên 50,000+ tin tuyển dụng từ LinkedIn, Indeed và TopCV.</p>
                </div>
             </div>
          </div>
        </div>

        {/* Right Column: Featured Opportunities */}
        <div className="lg:col-span-4 space-y-8">
          <div className={`${styles.panel} ${styles.opportunitiesPanel}`}>
            <h3 className="text-white font-black italic uppercase text-sm tracking-[0.2em] mb-8 flex items-center gap-2">
                <Target className="w-5 h-5 text-rose-500" /> New Opportunities
            </h3>
            <div className="space-y-6">
                {featuredJobs.map((job) => (
                    <div key={job.id} className="group cursor-pointer">
                        <Link href={`/user/jobs`} className={styles.jobCard}>
                            <h4 className="text-white font-black text-sm uppercase italic line-clamp-1 group-hover:text-cyan-400">{job.title_raw}</h4>
                            <div className="flex items-center gap-2 mt-2 opacity-40">
                                <Briefcase size={12} />
                                <span className="text-[10px] font-bold uppercase tracking-widest">Verified Employer</span>
                            </div>
                            <div className="mt-4 flex justify-end">
                                <span className="text-[10px] font-black text-cyan-400 flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                                    PHÂN TÍCH MATCH <ChevronRight size={12} />
                                </span>
                            </div>
                        </Link>
                    </div>
                ))}
            </div>

            <Link 
                href="/user/jobs"
                className="mt-8 flex w-full items-center justify-center py-4 bg-white/5 hover:bg-white/10 text-white font-black text-xs uppercase tracking-widest rounded-xl border border-white/10 transition-all"
            >
                Xem tất cả Job Market
            </Link>
          </div>

          <div className={`${styles.panel} ${styles.advicePanel}`}>
             <div className="absolute -bottom-4 -right-4 opacity-5">
                <Star size={100} fill="currentColor" />
             </div>
             <h3 className="text-white font-black italic uppercase text-sm flex items-center gap-2 mb-4">
                <Zap className="text-amber-500" /> AI Career Advice
             </h3>
             <p className="text-white/50 text-xs italic leading-relaxed font-medium">
                "Thị trường đang dịch chuyển mạnh sang AI-Native development. Tập trung nâng cấp kỹ năng Prompt Engineering và LLM Integration để tăng 40% khả năng nhận offer lương cao hơn."
             </p>
          </div>
        </div>
      </div>
    </div>
  );
}


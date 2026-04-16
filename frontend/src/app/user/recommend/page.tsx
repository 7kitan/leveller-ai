"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { 
  TrendingUp, 
  Briefcase, 
  Target, 
  ArrowRight, 
  RefreshCcw,
  BarChart3,
  Globe,
  CheckCircle2
} from "lucide-react";
import styles from "./user-recommend.module.css";
import { motion } from "framer-motion";

interface RecommendedJob {
  title: string;
  match_score: number;
  market_demand: string;
  top_skillsRequired: string[];
  career_path: string;
}

const UserRecommendPage = () => {
  const { token } = useAuth();
  const [recommendations, setRecommendations] = useState<RecommendedJob[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRecommendations = async () => {
    setLoading(true);
    try {
      const resp = await axios.get("/api/analysis/recommendations", {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRecommendations(resp.data);
    } catch (err) {
      console.error("Fetch recommendations error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchRecommendations();
  }, [token]);

  if (loading) {
    return (
      <div className={styles.loadingWrapper}>
        <div className={styles.spinner}></div>
        <p className={styles.loadingText}>Phân tích thị trường...</p>
      </div>
    );
  }

  return (
    <AuthGuard>
      <div className={styles.pageRoot}>
        {/* Header Section */}
        <div className={styles.header}>
          <div className={styles.title}>
            <div className={styles.badge}>
                <Globe size={12} />
                <span className={styles.badgeLabel}>Market Intelligence v2.0</span>
            </div>
            <h1 className={styles.titleMain}>
                SMART <span className={styles.gradientText}>INSIGHTS.</span>
            </h1>
            <p className={styles.headerSubtitle}>
              Dựa trên bản đồ kỹ năng hiện tại, đây là các vị trí tối ưu trên thị trường lao động.
            </p>
          </div>
          <div className={styles.controlBar}>
             <button onClick={fetchRecommendations} className={styles.refreshBtn}>
                <RefreshCcw size={16} /> Làm mới
             </button>
          </div>
        </div>

        {/* Market Insights Dashboard */}
        <div className={styles.mainGrid}>
          {/* Sidebar Insights */}
          <aside className={styles.sidebar}>
            <div className={styles.insightCard}>
              <div className={styles.insightIcon}>
                <BarChart3 size={20} />
              </div>
              <h3 className={styles.insightTitle}>Trending Roles</h3>
              <div className={styles.insightValue}>{recommendations.length > 0 ? recommendations[0].title : "N/A"}</div>
              <p className={styles.insightSubtext}>Vị trí dẫn đầu về nhu cầu tuyển dụng.</p>
            </div>

            <div className={styles.insightCard}>
              <div className={styles.insightIcon}>
                <Target size={20} />
              </div>
              <h3 className={styles.insightTitle}>Avg Match Rate</h3>
              <div className={styles.insightValue}>
                {recommendations.length > 0 
                  ? `${Math.round(recommendations.reduce((acc, curr) => acc + curr.match_score, 0) / recommendations.length)}%` 
                  : "0%"}
              </div>
              <p className={styles.insightSubtext}>Độ khớp trung bình với Portfolio.</p>
            </div>
          </aside>

          {/* Job Recommendations Area */}
          <div className={styles.contentArea}>
            {recommendations.map((job, index) => (
              <motion.div 
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={styles.recommendationCard}
              >
                <div className={styles.cardHeader}>
                   <div className={styles.matchBadge}>
                      <CheckCircle2 size={12} />
                      {job.match_score}% MATCH
                   </div>
                   <div className={styles.demandBadge}>
                      {job.market_demand.toUpperCase()}
                   </div>
                </div>

                <h3 className={styles.jobTitle}>{job.title}</h3>
                
                <div className={styles.skillGroup}>
                  <p className={styles.skillLabel}>Kỹ năng trọng tâm</p>
                  <div className={styles.skillList}>
                    {job.top_skillsRequired.map((skill, sIdx) => (
                      <span key={sIdx} className={styles.skillBadge}>
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                <button className={styles.actionBtn}>
                  Xem chi tiết lộ trình <ArrowRight size={14} />
                </button>
              </motion.div>
            ))}
          </div>
        </div>

        {/* AI Insight Footer Widget */}
        <div className={styles.footer}>
           <h4 className={styles.footerTitle}>
              <TrendingUp size={20} className={styles.footerIcon} /> 
              Market Analysis Note
           </h4>
           <div className={styles.footerContent}>
              <p className={styles.footerText}>
                Hệ thống AI đã phân tích hơn 50,000+ tin tuyển dụng từ các nền tảng LinkedIn và Indeed để đưa ra gợi ý này.
              </p>
              <p className={cn(styles.footerText, styles.footerNote)}>
                Gợi ý: Hãy tập trung vào các chứng chỉ Cloud để tăng 15% tỷ lệ khớp cho vai trò DevSecOps.
              </p>
           </div>
        </div>
      </div>
    </AuthGuard>
  );
};

export default UserRecommendPage;

"use client";

import React, { useState, useEffect } from "react";
import { 
  TrendingUp, 
  RefreshCcw,
  Activity,
  Clock,
  CheckCircle2,
  AlertCircle,
  Zap
} from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthContext";
import { useLanguage } from "@/context/LanguageContext";
import AuthGuard from "@/components/auth/AuthGuard";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";
import api from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import styles from "./market.module.css";

interface MarketStats {
  total_skills: number;
  last_updated: string | null;
  top_skills: Array<{
    skill_name: string;
    demand_score: number;
    avg_salary_min: number;
  }>;
}

const AdminMarketPage = () => {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [stats, setStats] = useState<MarketStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchMarketStats = async () => {
    try {
      setLoading(true);
      const res = await api.get("/analysis/market-stats");
      setStats(res.data);
    } catch (err: any) {
      console.error("Fetch market stats error:", err);
      toast.error("Failed to load market stats");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === "admin") {
      fetchMarketStats();
    }
  }, [user]);

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      const res = await api.post("/admin/refresh-market-stats");
      toast.success("Market stats refresh has been triggered. This may take a few minutes.");
      
      // Wait 3 seconds then refresh the stats
      setTimeout(() => {
        fetchMarketStats();
      }, 3000);
    } catch (err: any) {
      console.error("Refresh error:", err);
      toast.error(err.response?.data?.detail || "Failed to trigger refresh");
    } finally {
      setRefreshing(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Never";
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return "Unknown";
    }
  };

  const formatSalary = (salary: number) => {
    if (!salary) return "N/A";
    const millions = salary / 1000000;
    return `$${formatNumber(millions)}M`;
  };

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <div className={styles.pageRoot}>
          <PageHeader
            title={<><TrendingUp className={styles.headerIcon} /> Market Intelligence</>}
            subtitle="Monitor and manage market data aggregation"
          />

          {/* Actions Bar */}
          <div className={styles.actionsBar}>
            <div className={styles.statusBox}>
              <Activity className={styles.statusIcon} size={20} />
              <span className={styles.statusText}>
                Auto-refresh: <strong>Hourly</strong>
              </span>
            </div>

            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className={styles.btnPrimary}
            >
              <RefreshCcw size={16} className={refreshing ? styles.spinning : ""} />
              {refreshing ? "Refreshing..." : "Refresh Now"}
            </button>
          </div>

          {/* Stats Overview */}
          {loading ? (
            <div className={styles.loadingState}>
              <div className={styles.spinner} />
              <p>Loading market data...</p>
            </div>
          ) : stats ? (
            <>
              <div className={styles.statsGrid}>
                <div className={styles.statCard}>
                  <div className={styles.statIcon}>
                    <Zap size={28} />
                  </div>
                  <div className={styles.statValue}>{stats.total_skills || 0}</div>
                  <div className={styles.statLabel}>Total Skills Tracked</div>
                </div>

                <div className={styles.statCard}>
                  <div className={styles.statIcon}>
                    <Clock size={28} />
                  </div>
                  <div className={styles.statValue}>
                    {stats.last_updated ? "Active" : "Pending"}
                  </div>
                  <div className={styles.statLabel}>
                    Last Updated: {formatDate(stats.last_updated)}
                  </div>
                </div>

                <div className={styles.statCard}>
                  <div className={styles.statIcon}>
                    <CheckCircle2 size={28} />
                  </div>
                  <div className={styles.statValue}>
                    {stats.top_skills?.length || 0}
                  </div>
                  <div className={styles.statLabel}>Top Trending Skills</div>
                </div>
              </div>

              {/* Top Skills Table */}
              <div className={styles.tableSection}>
                <h3 className={styles.sectionTitle}>Top Trending Skills</h3>
                
                {stats.top_skills && stats.top_skills.length > 0 ? (
                  <div className={styles.tableWrapper}>
                    <table className={styles.table}>
                      <thead>
                        <tr>
                          <th>Rank</th>
                          <th>Skill Name</th>
                          <th>Demand Score</th>
                          <th>Avg Salary (Min)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stats.top_skills.map((skill, idx) => (
                          <tr key={skill.skill_name}>
                            <td className={styles.rankCell}>#{idx + 1}</td>
                            <td className={styles.skillCell}>
                              <strong>{skill.skill_name}</strong>
                            </td>
                            <td className={styles.scoreCell}>
                              <span className={styles.scoreBadge}>
                                {formatNumber(skill.demand_score)}
                              </span>
                            </td>
                            <td className={styles.salaryCell}>
                              {formatSalary(skill.avg_salary_min)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className={styles.emptyState}>
                    <AlertCircle size={48} />
                    <p>No market data available. Click "Refresh Now" to aggregate data.</p>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className={styles.emptyState}>
              <AlertCircle size={48} />
              <p>Failed to load market stats</p>
            </div>
          )}
        </div>
      </PageContainer>
    </AuthGuard>
  );
};

export default AdminMarketPage;

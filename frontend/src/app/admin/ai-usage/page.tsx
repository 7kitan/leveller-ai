"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { 
  Cpu, 
  Activity, 
  Users, 
  Database, 
  Clock, 
  AlertTriangle,
  BarChart3,
  Search,
  RefreshCw,
  Zap,
  Mail 
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/context/LanguageContext";
import styles from "../admin-dashboard.module.css";

const AIUsagePage = () => {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [stats, setStats] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    setRefreshing(true);
    try {
      const [statsRes, logsRes] = await Promise.all([
        axios.get("/api/analysis/admin/llm-stats", {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get("/api/analysis/admin/llm-logs?limit=20", {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      setStats(statsRes.data);
      setLogs(logsRes.data.items);
    } catch (err) {
      console.error("Fetch AI usage error:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (token) fetchData();
  }, [token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-transparent">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <AuthGuard requireAdmin>
      <div className={styles.pageRoot}>
        {/* Header Section */}
        <div className={styles.headerWrapper}>
          <div>
            <h1 className={styles.headerTitle}>
              <Cpu className={styles.insightIcon} size={48} /> {t("nav_monitor")}
            </h1>
            <p className={styles.headerSubtitle}>
              Track token consumption and performance across all AI models.
            </p>
          </div>
          <button 
            onClick={fetchData}
            disabled={refreshing}
            className={cn(styles.statusIndicator, "cursor-pointer hover:bg-emerald-500/10 transition-colors border-none")}
          >
            <RefreshCw size={16} className={cn(refreshing ? "animate-spin" : "", "text-emerald-500")} />
            <span className={styles.statusLabel}>
              {refreshing ? t("admin_settings_refreshing") : t("admin_settings_refresh_data")}
            </span>
          </button>
        </div>

        {/* Quick Stats Grid */}
        <div className={styles.statsGrid}>
          <StatCard 
            label="Total Calls" 
            value={stats?.summary?.total_calls?.toLocaleString()} 
            icon={Activity} 
            color="#10b981" 
          />
          <StatCard 
            label="Total Tokens" 
            value={stats?.summary?.total_tokens?.toLocaleString()} 
            icon={Zap} 
            color="#f59e0b" 
          />
          <StatCard 
            label="Avg Latency" 
            value={`${stats?.summary?.avg_latency_ms}ms`} 
            icon={Clock} 
            color="#0ea5e9" 
          />
          <StatCard 
            label="Est. Cost" 
            value={`~$${((stats?.summary?.total_tokens || 0) / 1000000 * 0.5).toFixed(2)}`} 
            icon={BarChart3} 
            color="#ec4899" 
          />
        </div>

        <div className={styles.moduleGrid}>
          {/* Models and Top Users */}
          <div className="col-span-12 lg:col-span-4 space-y-6">
            <div className={cn(styles.statCard, "p-8")}>
              <h2 className="text-xl font-extrabold mb-6 flex items-center gap-3 text-[var(--color-text-main)]">
                <Database size={24} className="text-emerald-500" /> Usage by Model
              </h2>
              <div className="space-y-6">
                {stats?.by_model?.map((m: any) => (
                  <div key={m.model_id} className="p-4 bg-black/5 dark:bg-white/5 rounded-2xl">
                    <div className="flex justify-between items-center mb-3">
                      <span className="font-bold text-emerald-500">{m.model_id}</span>
                      <span className="text-[10px] font-black uppercase tracking-widest text-[var(--color-text-muted)]">{m.calls} calls</span>
                    </div>
                    <div className="w-full bg-black/10 dark:bg-white/10 h-2 rounded-full overflow-hidden">
                      <div 
                        className="bg-emerald-500 h-full rounded-full" 
                        style={{ width: `${(m.tokens / stats.summary.total_tokens * 100) || 0}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between mt-2 text-[10px] font-bold text-[var(--color-text-muted)]">
                      <span>{m.tokens.toLocaleString()} tokens</span>
                      <span>{Math.round((m.tokens / stats.summary.total_tokens * 100) || 0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className={cn(styles.statCard, "p-8")}>
              <h2 className="text-xl font-extrabold mb-6 flex items-center gap-3 text-[var(--color-text-main)]">
                <Users size={24} className="text-blue-500" /> Top Consumers
              </h2>
              <div className="space-y-4">
                {stats?.top_users?.map((u: any, idx: number) => (
                  <div key={u.email} className="flex items-center justify-between p-3 hover:bg-black/5 dark:hover:bg-white/5 rounded-2xl transition-colors">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-blue-500/10 text-blue-500 flex items-center justify-center text-xs font-black">
                        {idx + 1}
                      </div>
                      <div className="truncate w-32 md:w-40 text-sm font-bold text-[var(--color-text-main)]">{u.email}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-extrabold text-[var(--color-text-main)]">{u.tokens.toLocaleString()}</div>
                      <div className="text-[10px] font-bold text-[var(--color-text-muted)]">{u.calls} calls</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recent Logs Table */}
          <div className="col-span-12 lg:col-span-8">
            <div className={cn(styles.statCard, "p-8 h-full")}>
              <div className="flex justify-between items-center mb-8">
                <h2 className="text-2xl font-extrabold flex items-center gap-4 text-[var(--color-text-main)]">
                  <Activity size={28} className="text-pink-500" /> Recent AI Activity
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-[var(--color-text-muted)] border-b border-[var(--color-border-subtle)] text-xs font-black uppercase tracking-widest">
                      <th className="pb-4">Model / Type</th>
                      <th className="pb-4">User</th>
                      <th className="pb-4 text-right">Tokens</th>
                      <th className="pb-4 text-right">Latency</th>
                      <th className="pb-4 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--color-border-subtle)]">
                    {logs.map((log) => (
                      <tr key={log.id} className="group hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                        <td className="py-5">
                          <div className="font-extrabold text-[var(--color-text-main)]">{log.model_id}</div>
                          <div className="text-[10px] font-bold text-[var(--color-text-muted)] uppercase tracking-tight">{log.call_type.replace(/_/g, ' ')}</div>
                        </td>
                        <td className="py-5">
                          <div className="text-sm font-bold text-[var(--color-text-main)] truncate w-32">{log.user_email}</div>
                          <div className="text-[10px] font-medium text-[var(--color-text-muted)]">
                            {new Date(log.created_at).toLocaleString()}
                          </div>
                        </td>
                        <td className="py-5 text-right">
                          <div className="text-sm font-extrabold text-[var(--color-text-main)]">{log.total_tokens.toLocaleString()}</div>
                          <div className="text-[10px] font-bold text-[var(--color-text-muted)]">P:{log.prompt_tokens} C:{log.completion_tokens}</div>
                        </td>
                        <td className="py-5 text-right text-sm font-bold text-[var(--color-text-main)]">
                          {log.latency_ms}ms
                        </td>
                        <td className="py-5 text-center">
                          <span className={cn(
                            "px-3 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest",
                            log.status === "success" ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
                          )}>
                            {log.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
};

const StatCard = ({ label, value, icon: Icon, color }: any) => {
  return (
    <div className={styles.statCard}>
      <Icon className={styles.statIconDecorative} style={{ color }} />
      <div className={styles.statValue}>{value}</div>
      <div className={styles.statLabelSmall}>{label}</div>
    </div>
  );
};

export default AIUsagePage;

"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { 
  Cpu, 
  Activity, 
  Users, 
  Database, 
  Clock, 
  BarChart3,
  RefreshCw,
  Zap
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/context/LanguageContext";
import PageHeader from "@/components/common/PageHeader";
import styles from "../admin-dashboard.module.css";
import localStyles from "./ai-usage.module.css";
import PageContainer from "@/components/common/PageContainer";
import { 
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, 
  CartesianGrid, Tooltip 
} from "recharts";
import { format } from "date-fns";

const AIUsagePage = () => {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [stats, setStats] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [usageSeries, setUsageSeries] = useState<any[]>([]);
  const [period, setPeriod] = useState<'day' | 'hour'>('day');
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    setRefreshing(true);
    try {
      const [statsRes, logsRes, seriesRes] = await Promise.all([
        api.get("admin/stats/llm/summary"),
        api.get("admin/stats/llm/logs?limit=20"),
        api.get(`analysis/admin/llm-usage-series?period=${period}&days=${days}`)
      ]);
      setStats(statsRes.data);
      setLogs(logsRes.data);
      setUsageSeries(seriesRes.data);
    } catch (err) {
      console.error("Fetch AI usage error:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (token) fetchData();
  }, [token, period, days]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-transparent">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        {/* Header Section */}
        <PageHeader
          title={t("nav_monitor")}
          subtitle={t("admin_ai_desc")}
          compact
          showAccent={false}
        >
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
        </PageHeader>

        {/* Quick Stats Grid */}
        <div className={styles.statsGrid}>
          <StatCard 
            label={t("admin_ai_total_calls")} 
            value={stats?.summary?.total_calls?.toLocaleString()} 
            icon={Activity} 
            color="#10b981" 
          />
          <StatCard 
            label={t("admin_ai_total_tokens")} 
            value={stats?.total_tokens?.toLocaleString()} 
            icon={Zap} 
            color="#f59e0b" 
          />
          <StatCard 
            label={t("admin_ai_avg_latency")} 
            value={`${Math.round(stats?.avg_latency_ms || 0)}ms`} 
            icon={Clock} 
            color="#0ea5e9" 
          />
          <StatCard 
            label={t("admin_ai_est_cost")} 
            value={`$${stats?.total_cost_usd?.toFixed(4)}`} 
            icon={BarChart3} 
            color="#ec4899" 
          />
        </div>

        {/* Chart Section */}
        <div className={cn(styles.statCard, "p-8 mb-8")}>
          <div className={localStyles.chartHeader}>
            <h2 className={localStyles.chartTitle}>
              <BarChart3 size={28} className="text-emerald-500" /> {t("admin_ai_usage_trends")}
            </h2>
            <div className={localStyles.chartControls}>
              <div className={localStyles.periodToggle}>
                <button 
                  onClick={() => { setPeriod('hour'); setDays(1); }}
                  className={cn(
                    localStyles.toggleBtn,
                    period === 'hour' ? localStyles.toggleBtnActive : localStyles.toggleBtnInactive
                  )}
                >
                  {t("admin_ai_hourly")}
                </button>
                <button 
                  onClick={() => setPeriod('day')}
                  className={cn(
                    localStyles.toggleBtn,
                    period === 'day' ? localStyles.toggleBtnActive : localStyles.toggleBtnInactive
                  )}
                >
                  {t("admin_ai_daily")}
                </button>
              </div>
              
              <div className={localStyles.divider} />

              <div className={localStyles.daysSelector}>
                {[7, 30, 90].map((d) => (
                  <button
                    key={d}
                    onClick={() => { setDays(d); if (period === 'hour') setPeriod('day'); }}
                    className={cn(
                      localStyles.dayBtn,
                      days === d && period === 'day' ? localStyles.dayBtnActive : localStyles.dayBtnInactive
                    )}
                  >
                    {d}D
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={usageSeries} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorTokens" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                <XAxis 
                  dataKey="timestamp" 
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: 'var(--color-text-muted)', fontSize: 10, fontWeight: 'bold' }}
                  tickFormatter={(val) => {
                    const date = new Date(val);
                    return period === 'hour' ? format(date, 'HH:mm') : format(date, 'dd/MM');
                  }}
                  minTickGap={30}
                />
                <YAxis 
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: 'var(--color-text-muted)', fontSize: 10, fontWeight: 'bold' }}
                  tickFormatter={(val) => val >= 1000 ? `${(val/1000).toFixed(1)}k` : val}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(0,0,0,0.8)', 
                    borderRadius: '16px', 
                    border: 'none',
                    backdropFilter: 'blur(10px)',
                    boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
                    color: '#fff'
                  }}
                  itemStyle={{ color: '#10b981' }}
                  labelStyle={{ marginBottom: '8px', fontWeight: 'bold', color: '#888' }}
                  labelFormatter={(val) => format(new Date(val), period === 'hour' ? 'PPP HH:mm' : 'PPP')}
                />
                <Area 
                  type="monotone" 
                  dataKey="tokens" 
                  stroke="#10b981" 
                  strokeWidth={4}
                  fillOpacity={1} 
                  fill="url(#colorTokens)" 
                  animationDuration={1500}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className={styles.moduleGrid}>
          {/* Models and Top Users */}
          <div className="col-span-12 lg:col-span-4 space-y-6">
            <div className={cn(styles.statCard, "p-8")}>
              <h2 className="text-xl font-extrabold mb-6 flex items-center gap-3 text-[var(--color-text-main)]">
                <Database size={24} className="text-emerald-500" /> {t("admin_ai_by_model")}
              </h2>
              <div className="space-y-6">
                {stats?.model_breakdown?.map((m: any) => (
                  <div key={m.model} className={localStyles.modelCard}>
                    <div className={localStyles.modelHeader}>
                      <span className={localStyles.modelName}>{m.model}</span>
                      <span className={localStyles.modelCalls}>{m.calls} {t("admin_ai_calls")}</span>
                    </div>
                    <div className={localStyles.progressBar}>
                      <div 
                        className={localStyles.progressFill} 
                        style={{ width: `${(m.tokens / stats.total_tokens * 100) || 0}%` }}
                      ></div>
                    </div>
                    <div className={localStyles.modelFooter}>
                      <span>{m.tokens.toLocaleString()} {t("admin_ai_tokens_cost")} {m.cost_usd}</span>
                      <span>{Math.round((m.tokens / stats.total_tokens * 100) || 0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className={cn(styles.statCard, "p-8")}>
              <h2 className="text-xl font-extrabold mb-6 flex items-center gap-3 text-[var(--color-text-main)]">
                <Users size={24} className="text-blue-500" /> {t("admin_ai_top_users")}
              </h2>
              <div className="space-y-4">
                {stats?.top_users?.map((u: any, idx: number) => (
                  <div key={u.email} className={localStyles.userCard}>
                    <div className="flex items-center gap-4">
                      <div className={localStyles.userRank}>
                        {idx + 1}
                      </div>
                      <div className={localStyles.userEmail}>{u.email}</div>
                    </div>
                    <div className="text-right">
                      <div className={localStyles.userTokens}>{u.tokens.toLocaleString()}</div>
                      <div className={localStyles.userCalls}>{u.calls} {t("admin_ai_calls")}</div>
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
                  <Activity size={28} className="text-pink-500" /> {t("admin_ai_recent_activity")}
                </h2>
              </div>
              <div className={localStyles.tableWrapper}>
                <table className={localStyles.table}>
                  <thead>
                    <tr className={localStyles.thead}>
                      <th className={localStyles.th}>{t("admin_ai_model_type")}</th>
                      <th className={localStyles.th}>{t("admin_ai_user")}</th>
                      <th className={cn(localStyles.th, "text-right")}>{t("admin_ai_tokens")}</th>
                      <th className={cn(localStyles.th, "text-right")}>{t("admin_ai_latency")}</th>
                      <th className={cn(localStyles.th, "text-center")}>{t("admin_ai_status")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--color-border-subtle)]">
                    {logs.map((log) => (
                      <tr key={log.id} className={localStyles.tr}>
                        <td className={localStyles.td}>
                          <div className={localStyles.modelId}>{log.model_id}</div>
                          <div className={localStyles.callType}>{log.call_type.replace(/_/g, ' ')}</div>
                        </td>
                        <td className={localStyles.td}>
                          <div className="text-sm font-bold text-[var(--color-text-main)] truncate w-32">{log.user_email}</div>
                          <div className="text-[10px] font-medium text-[var(--color-text-muted)]">
                            {new Date(log.created_at).toLocaleString()}
                          </div>
                        </td>
                        <td className={cn(localStyles.td, "text-right")}>
                          <div className="text-sm font-extrabold text-[var(--color-text-main)]">{log.total_tokens.toLocaleString()}</div>
                          <div className="text-[10px] font-bold text-[var(--color-text-muted)]">{t("admin_ai_prompt")}{log.prompt_tokens} {t("admin_ai_completion")}{log.completion_tokens}</div>
                        </td>
                        <td className={cn(localStyles.td, "text-right text-sm font-bold text-[var(--color-text-main)]")}>
                          {log.latency_ms}ms
                        </td>
                        <td className={cn(localStyles.td, "text-center")}>
                          <span className={cn(
                            localStyles.statusBadge,
                            log.status === "success" ? localStyles.statusSuccess : localStyles.statusError
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
      </PageContainer>
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


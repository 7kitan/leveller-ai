"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { 
  Activity, 
  RefreshCw, 
  Trash2, 
  Filter, 
  AlertCircle, 
  Info, 
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Database
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/context/LanguageContext";
import styles from "../admin-dashboard.module.css";
import localStyles from "./system-logs.module.css";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";

const SystemLogsPage = () => {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [level, setLevel] = useState<string>("");
  const [module, setModule] = useState<string>("");
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const fetchLogs = async (newOffset = 0) => {
    setRefreshing(true);
    try {
      const res = await api.get(`/admin/system/logs?limit=${limit}&offset=${newOffset}&level=${level}&module=${module}`);
      setLogs(res.data);
      setOffset(newOffset);
    } catch (err) {
      console.error("Fetch system logs error:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const cleanupLogs = async () => {
    if (!confirm(t("admin_logs_cleanup_confirm" as any))) return;
    try {
      await api.delete("/admin/system/logs/cleanup?days=30");
      fetchLogs(0);
    } catch (err) {
      console.error("Cleanup logs error:", err);
    }
  };

  useEffect(() => {
    if (token) fetchLogs(0);
  }, [token, level, module]);

  const getLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case "CRITICAL": return "bg-purple-500/10 text-purple-500 border-purple-500/20";
      case "ERROR": return "bg-rose-500/10 text-rose-500 border-rose-500/20";
      case "WARNING": return "bg-amber-500/10 text-amber-500 border-amber-500/20";
      case "INFO": return "bg-blue-500/10 text-blue-500 border-blue-500/20";
      default: return "bg-slate-500/10 text-slate-500 border-slate-500/20";
    }
  };

  const getLevelIcon = (level: string) => {
    switch (level.toUpperCase()) {
      case "CRITICAL": return <AlertCircle size={14} />;
      case "ERROR": return <AlertCircle size={14} />;
      case "WARNING": return <AlertTriangle size={14} />;
      case "INFO": return <Info size={14} />;
      default: return <Database size={14} />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-transparent">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-rose-500"></div>
      </div>
    );
  }

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <PageHeader 
          title={t("nav_system_logs")}
          subtitle={t("admin_logs_desc")}
        >
          <div className={localStyles.actions}>
            <button 
              onClick={cleanupLogs}
              className={localStyles.cleanupBtn}
            >
              <Trash2 size={16} /> {t("admin_logs_cleanup")}
            </button>
            <button 
              onClick={() => fetchLogs(offset)}
              disabled={refreshing}
              className={cn(styles.statusIndicator, localStyles.refreshBtn, "border-none")}
            >
              <RefreshCw size={16} className={cn(refreshing ? "animate-spin" : "", "text-rose-500")} />
              <span className={styles.statusLabel}>
                {refreshing ? t("admin_logs_refreshing") : t("admin_logs_refresh")}
              </span>
            </button>
          </div>
        </PageHeader>

        {/* Filters Bar */}
        <div className={cn(styles.statCard, localStyles.filtersBar)}>
          <div className={localStyles.filterGroup}>
            <Filter size={18} className="text-slate-400" />
            <span className={localStyles.filterLabel}>{t("admin_logs_filters")}:</span>
          </div>
          
          <select 
            value={level} 
            onChange={(e) => setLevel(e.target.value)}
            className={localStyles.select}
          >
            <option value="">{t("admin_logs_all_levels")}</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="ERROR">ERROR</option>
            <option value="WARNING">WARNING</option>
            <option value="INFO">INFO</option>
          </select>

          <input 
            type="text" 
            placeholder={t("admin_logs_module_placeholder" as any)}
            value={module}
            onChange={(e) => setModule(e.target.value)}
            className={localStyles.input}
          />
        </div>

        {/* Logs Table */}
        <div className={cn(styles.statCard, localStyles.tableContainer)}>
          <div className="overflow-x-auto">
            <table className={localStyles.table}>
              <thead>
                <tr className={localStyles.thead}>
                  <th className={localStyles.th}>{t("admin_logs_timestamp")}</th>
                  <th className={localStyles.th}>{t("admin_logs_level")}</th>
                  <th className={localStyles.th}>{t("admin_logs_module")}</th>
                  <th className={localStyles.th}>{t("admin_logs_message")}</th>
                  <th className={cn(localStyles.th, "text-right")}>{t("admin_logs_actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border-subtle)]">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-20 text-center text-[var(--color-text-muted)] font-bold">
                      {t("admin_logs_no_results")}
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className={localStyles.tr}>
                      <td className={cn(localStyles.td, localStyles.timestamp)}>
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className={localStyles.td}>
                        <span className={cn(
                          localStyles.levelBadge,
                          getLevelColor(log.level)
                        )}>
                          {getLevelIcon(log.level)}
                          {log.level}
                        </span>
                      </td>
                      <td className={localStyles.td}>
                        <span className={localStyles.module}>{log.module}</span>
                      </td>
                      <td className={localStyles.td}>
                        <div className={localStyles.message}>{log.message}</div>
                        {log.details && (
                          <div className={localStyles.details}>
                            {typeof log.details === 'string' ? log.details : JSON.stringify(log.details)}
                          </div>
                        )}
                      </td>
                      <td className={cn(localStyles.td, localStyles.actionsCell)}>
                        <button 
                          onClick={() => alert(JSON.stringify(log, null, 2))}
                          className={localStyles.detailsBtn}
                        >
                          {t("admin_logs_details")}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className={localStyles.pagination}>
            <div className={localStyles.paginationText}>
              {t("admin_logs_showing")} {logs.length} logs
            </div>
            <div className={localStyles.paginationButtons}>
              <button 
                onClick={() => fetchLogs(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className={localStyles.pageBtn}
              >
                <ChevronLeft size={20} />
              </button>
              <button 
                onClick={() => fetchLogs(offset + limit)}
                disabled={logs.length < limit}
                className={localStyles.pageBtn}
              >
                <ChevronRight size={20} />
              </button>
            </div>
          </div>
        </div>
      </PageContainer>
    </AuthGuard>
  );
};

export default SystemLogsPage;

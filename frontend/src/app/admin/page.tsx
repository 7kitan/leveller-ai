"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { 
  Users, 
  FileText,
  TrendingUp,
  ShieldCheck,
  ArrowUpRight,
  Cpu,
  Layers,
  BookOpen,
  ChevronRight,
  Zap,
  Settings,
  Activity,
  Video
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import styles from "./admin-dashboard.module.css";
import { useLanguage } from "@/context/LanguageContext";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";

const AdminDashboard = () => {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [stats, setStats] = useState({
    users: 0,
    cvs: 0,
    jobs: 0,
    marketFits: 0
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await api.get("analysis/admin/stats");
        setStats(res.data);
      } catch (err) {
        console.error("Fetch stats error:", err);
      }
    };
    if (user) fetchStats();
  }, [user]);

  const dashboardModules = [
    { 
      title: t("admin_dash_module_users_title"), 
      desc: t("admin_dash_module_users_desc"), 
      icon: Users, 
      path: "/admin/users",
      color: "#818cf8"
    },
    { 
      title: t("admin_dash_module_cvs_title"), 
      desc: t("admin_dash_module_cvs_desc"), 
      icon: FileText, 
      path: "/admin/cvs",
      color: "#ec4899"
    },
    { 
      title: t("admin_dash_module_jobs_title"), 
      desc: t("admin_dash_module_jobs_desc"), 
      icon: Layers, 
      path: "/admin/jobs",
      color: "#f59e0b"
    },
    { 
      title: t("admin_dash_module_courses_title"), 
      desc: t("admin_dash_module_courses_desc"), 
      icon: BookOpen, 
      path: "/admin/courses",
      color: "#0ea5e9"
    },
    { 
      title: t("admin_dash_module_market_title"), 
      desc: t("admin_dash_module_market_desc"), 
      icon: TrendingUp, 
      path: "/admin/market",
      color: "#a78bfa"
    },
    { 
      title: t("admin_dash_module_settings_title"), 
      desc: t("admin_dash_module_settings_desc"), 
      icon: Settings, 
      path: "/admin/settings",
      color: "#64748b"
    },
    { 
      title: t("admin_dash_module_ai_usage_title"), 
      desc: t("admin_dash_module_ai_usage_desc"), 
      icon: Cpu, 
      path: "/admin/ai-usage",
      color: "#10b981"
    },
    { 
      title: t("admin_dash_module_system_logs_title"), 
      desc: t("admin_dash_module_system_logs_desc"), 
      icon: Activity, 
      path: "/admin/system-logs",
      color: "#f43f5e"
    },
    { 
      title: t("admin_dash_module_youtube_title"), 
      desc: t("admin_dash_module_youtube_desc"), 
      icon: Video, 
      path: "/admin/youtube",
      color: "#ef4444"
    }
  ];

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        {/* Header Section */}
        <PageHeader
          title={t("admin_dash_title")}
          subtitle={t("admin_dash_subtitle")}
          compact
        >
          <div className={styles.statusIndicator}>
            <div className={cn(styles.badgeDot, styles.indicatorSuccess)} />
            <span className={styles.statusLabel}>{t("admin_dash_status_online")}</span>
          </div>
        </PageHeader>

        {/* Quick Stats Grid */}
        <div className={styles.statsGrid}>
          {[
            { label: t("admin_dash_users_label"), value: stats.users, icon: Users },
            { label: t("admin_dash_cvs_label"), value: stats.cvs || 0, icon: FileText },
            { label: t("admin_dash_jobs_label"), value: stats.jobs || 0, icon: Layers },
            { label: t("admin_dash_market_fit_label"), value: `${stats.marketFits}%`, icon: Zap },
          ].map((stat) => (
            <div key={stat.label} className={styles.statCard}>
              <stat.icon className={cn(styles.statIcon, styles.statIconDecorative)} />
              <div className={styles.statValue}>{stat.value}</div>
              <div className={styles.statLabelSmall}>{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Module Access Grid */}
        <div className={styles.moduleGrid}>
          {dashboardModules.map((stat) => (
            <Link 
              key={stat.path} 
              href={stat.path} 
              className={styles.moduleCard}
              style={{ "--accent-color": stat.color } as React.CSSProperties}
            >
               <div className={styles.cardDecoration}>
                   <stat.icon size={48} />
               </div>
               
               <div className={styles.moduleIconBox}>
                  <stat.icon size={24} />
               </div>
               
               <div className={styles.moduleTextGroup}>
                  <h3 className={styles.moduleTitle}>{stat.title}</h3>
                  <p className={styles.moduleDesc}>{stat.desc}</p>
               </div>

               <div className={styles.footerWrapper}>
                   <div className={styles.linkText}>
                     {t("admin_dash_access_module")} <ChevronRight size={14} />
                   </div>
                   <div className={styles.hoverIcon}>
                     <ArrowUpRight size={20} className={styles.iconWithAccent} />
                   </div>
               </div>

                <div className={styles.progressBar}>
                   <div className={styles.progressFill} />
                </div>
            </Link>
          ))}
        </div>

        {/* Global Insight Widget */}
        <div className={styles.insightSection}>
          <TrendingUp size={400} className={styles.bgDecoration} />
           <div className={styles.relativeZ10}>
            <h2 className={styles.insightTitle}>
               <ShieldCheck size={24} className={styles.insightIcon} /> {t("admin_dash_health_title")}
            </h2>
            <p className={styles.insightText}>
               {t("admin_dash_health_desc")}
            </p>
            <div className={styles.badgeGroup}>
               <div className={styles.badge}>
                  <div className={cn(styles.badgeDot, styles.indicatorSuccess)} />
                  <span className={styles.badgeLabel}>{t("admin_dash_badge_graph_sync")}</span>
               </div>
               <div className={styles.badge}>
                  <div className={cn(styles.badgeDot, styles.indicatorPrimary)} />
                  <span className={styles.badgeLabel}>{t("admin_dash_badge_cache_clear")}</span>
               </div>
            </div>
          </div>
        </div>
      </PageContainer>
    </AuthGuard>
  );
};

export default AdminDashboard;



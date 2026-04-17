"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { 
  Users, 
  Database,
  Network,
  TrendingUp,
  ShieldCheck,
  ArrowUpRight,
  Cpu,
  Layers,
  BookOpen,
  ChevronRight,
  Zap
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import styles from "./admin-dashboard.module.css";

const AdminDashboard = () => {
  const { token } = useAuth();
  const [stats, setStats] = useState({
    users: 0,
    skills: 0,
    relations: 0,
    marketFits: 0
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await axios.get("/api/analysis/admin/stats", {
          headers: { Authorization: `Bearer ${token}` }
        });
        setStats(res.data);
      } catch (err) {
        console.error("Fetch stats error:", err);
      }
    };
    if (token) fetchStats();
  }, [token]);

  const dashboardModules = [
    { 
      title: "User Control", 
      desc: "Quản lý quyền truy cập và phân vai người dùng hệ thống.", 
      icon: Users, 
      path: "/admin/users",
      color: "#818cf8"
    },
    { 
      title: "Taxonomy Hub", 
      desc: "Định nghĩa kĩ năng và thực thể cho Knowledge Graph.", 
      icon: Database, 
      path: "/admin/taxonomy",
      color: "#34d399"
    },
    { 
      title: "Job Portal", 
      desc: "Quản trị tin tuyển dụng, trạng thái và ánh xạ taxonomy.", 
      icon: Layers, 
      path: "/admin/jobs",
      color: "#f59e0b"
    },
    { 
      title: "Course Catalog", 
      desc: "Quản lý dữ liệu khóa học và vector embedding tri thức.", 
      icon: BookOpen, 
      path: "/admin/courses",
      color: "#0ea5e9"
    },
    { 
      title: "Relations Map", 
      desc: "Thiết lập quan hệ phân cấp giữa các thực thể tri thức.", 
      icon: Network, 
      path: "/admin/relations",
      color: "#f472b6"
    },
    { 
      title: "Market Insight", 
      desc: "Giám sát chỉ số khớp lệnh thị trường và phân tích Gap.", 
      icon: TrendingUp, 
      path: "/admin/market",
      color: "#a78bfa"
    }
  ];

  return (
    <AuthGuard requireAdmin>
      <div className={styles.pageRoot}>
        {/* Header Section */}
        <div className={styles.headerWrapper}>
          <div>
            <h1 className={styles.headerTitle}>System Oversight</h1>
            <p className={styles.headerSubtitle}>Bảng điều khiển quản trị tập trung cho Knowledge Graph & User AI.</p>
          </div>
          <div className={styles.statusIndicator}>
            <div className={cn(styles.badgeDot, styles.indicatorSuccess)} />
            <span className={styles.statusLabel}>AI Intelligence Online</span>
          </div>
        </div>

        {/* Quick Stats Grid */}
        <div className={styles.statsGrid}>
          {[
            { label: "Active Users", value: stats.users, icon: Users },
            { label: "Graph Entities", value: stats.skills, icon: Cpu },
            { label: "Semantic Links", value: stats.relations, icon: Network },
            { label: "Avg Market Fit", value: `${stats.marketFits}%`, icon: Zap },
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
                     Access Module <ChevronRight size={14} />
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
               <Layers size={24} className={styles.insightIcon} /> Knowledge Logic Health
            </h2>
            <p className={styles.insightText}>
               Hệ thống đang hoạt động ổn định. Taxonomy được cập nhật lần cuối vào 2 giờ trước. 
               Không có xung đột semantic nào được phát hiện trong quá trình ánh xạ kĩ năng người dùng.
            </p>
            <div className={styles.badgeGroup}>
               <div className={styles.badge}>
                  <div className={cn(styles.badgeDot, styles.indicatorSuccess)} />
                  <span className={styles.badgeLabel}>Live Graph Sync</span>
               </div>
               <div className={styles.badge}>
                  <div className={cn(styles.badgeDot, styles.indicatorPrimary)} />
                  <span className={styles.badgeLabel}>Semantic Cache Clear</span>
               </div>
            </div>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
};

export default AdminDashboard;

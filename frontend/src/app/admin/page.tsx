"use client";

import React, { useEffect, useState } from "react";
import { 
  Users, 
  FileText, 
  BookOpen, 
  Network, 
  ArrowRight, 
  Database,
  Cpu,
  Layers,
  Sparkles,
  Zap,
  TrendingUp,
  Activity
} from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import styles from "./admin-dashboard.module.css";

const AdminDashboard = () => {
  const { token } = useAuth();
  const [stats, setStats] = useState([
    { label: "Technical Skills", value: "...", icon: Cpu, color: "text-violet-400" },
    { label: "Total Users", value: "...", icon: Users, color: "text-cyan-400", path: "/admin/users" },
    { label: "CV Repository", value: "...", icon: FileText, color: "text-amber-400", path: "/admin/cvs" },
    { label: "Graph Nodes", value: "...", icon: Database, color: "text-emerald-400" },
  ]);

  useEffect(() => {
    const fetchDashboardStats = async () => {
      if (!token) return;
      try {
        const [usersRes, cvsRes] = await Promise.all([
          fetch("/api/auth/admin/users", { 
            headers: { 
              "X-Is-Admin": "true",
              "Authorization": `Bearer ${token}`
            } 
          }),
          fetch("/api/cv/admin/all", { 
            headers: { 
              "X-Is-Admin": "true",
              "Authorization": `Bearer ${token}`
            } 
          })
        ]);
        
        const users = await usersRes.json();
        const cvs = await cvsRes.json();
        
        const userCount = Array.isArray(users) ? users.length : 0;
        const cvCount = Array.isArray(cvs) ? cvs.length : 0;

        setStats(prev => [
          prev[0],
          { ...prev[1], value: userCount.toString() },
          { ...prev[2], value: cvCount.toString() },
          prev[3]
        ]);
      } catch (err) {
        console.error("Error fetching dashboard stats:", err);
      }
    };
    fetchDashboardStats();
  }, []);

  const managementModules = [
    { title: "User Management", desc: "Quản lý tài khoản, phân quyền và giám sát hoạt động người dùng.", path: "/admin/users", icon: Users, color: "from-blue-600/20 to-cyan-600/20" },
    { title: "CV Repository", desc: "Kho lưu trữ tập trung toàn bộ hồ sơ ứng viên và kết quả phân tích AI.", path: "/admin/cvs", icon: FileText, color: "from-amber-600/20 to-orange-600/20" },
    { title: "Technical Dictionary", desc: "Định nghĩa và chuẩn hóa ánh xạ từ khóa kỹ thuật (Taxonomy).", path: "/admin/taxonomy", icon: BookOpen, color: "from-violet-600/20 to-purple-600/20" },
    { title: "Graph Intelligence", desc: "Cấu trúc mối quan hệ phân cấp và phụ thuộc tri thức kỹ năng.", path: "/admin/relations", icon: Network, color: "from-emerald-600/20 to-teal-600/20" },
  ];

  return (
    <div className={styles.pageRoot}>
      {/* Welcome Header */}
      <div className={styles.headerWrapper}>
        <div className="space-y-1">
          <h1 className={styles.headerTitle}>
            Command Center
          </h1>
          <p className={styles.headerSubtitle}>Chào mừng trở lại. Hệ thống đang vận hành tối ưu.</p>
        </div>
        <div className={styles.statusIndicator}>
          <Activity className="w-5 h-5 text-emerald-500 animate-pulse" />
          <span className="text-xs font-black uppercase tracking-widest text-white/60">AI Intelligence Online</span>
        </div>
      </div>

      {/* Real-time Status Grid */}
      <div className={styles.statsGrid}>
        {stats.map((stat) => (
          <div key={stat.label} className={styles.statCard}>
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
              <stat.icon size={64} />
            </div>
            <stat.icon className={`${stat.color} ${styles.statIcon}`} />
            <div className={styles.statValue}>
               {stat.value}
            </div>
            <div className="flex items-center justify-between relative z-10">
               <div className="text-xs font-black uppercase tracking-widest text-white/30">{stat.label}</div>
               {stat.path && (
                 <Link href={stat.path} className="text-[10px] font-bold text-violet-400 hover:text-white transition-colors flex items-center gap-1">
                    Manage <ArrowRight size={10} />
                 </Link>
               )}
            </div>
          </div>
        ))}
      </div>

      {/* Module Navigation Grid */}
      <div className={styles.moduleGrid}>
        {managementModules.map((module) => (
          <Link 
            key={module.title} 
            href={module.path} 
            className={`bg-gradient-to-br ${module.color} ${styles.moduleCard}`}
          >
            <div className="flex items-start justify-between mb-10">
               <div className={styles.moduleIconBox}>
                  <module.icon className="w-8 h-8" />
               </div>
               <div className="p-3 rounded-full bg-white/5 opacity-0 group-hover:opacity-100 transition-all">
                  <ArrowRight className="w-6 h-6 text-white" />
               </div>
            </div>
            <h3 className="text-3xl font-black text-white mb-4 tracking-tight">{module.title}</h3>
            <p className="text-white/40 leading-relaxed font-medium text-lg mb-10">{module.desc}</p>
            
            <div className="h-1 w-24 bg-white/10 rounded-full overflow-hidden">
               <div className="h-full w-0 group-hover:w-full bg-white/40 transition-all duration-700"></div>
            </div>
          </Link>
        ))}
      </div>

      {/* Graph Intelligence / System Health */}
      <div className={styles.insightSection}>
        <TrendingUp className="absolute top-[-20%] right-[-5%] w-96 h-96 text-violet-500/5 rotate-12" />
        <div className="max-w-2xl relative z-10">
          <h3 className="text-3xl font-black text-white mb-6 flex items-center gap-4">
            <Sparkles className="w-8 h-8 text-amber-400" /> System Growth Insight
          </h3>
          <p className="text-white/50 leading-relaxed font-medium text-xl mb-10 italic">
            " Lượng dữ liệu hồ sơ tăng 12% trong tuần này. AI khuyến nghị bóc tách sâu hơn các kỹ năng Cloud Native để làm phong phú bản đồ tri thức. "
          </p>
          <div className="flex items-center gap-6">
             <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                <span className="text-xs font-black text-white/40 uppercase tracking-widest">Database Sync: OK</span>
             </div>
             <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-violet-500"></div>
                <span className="text-xs font-black text-white/40 uppercase tracking-widest">Worker Load: 14%</span>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;

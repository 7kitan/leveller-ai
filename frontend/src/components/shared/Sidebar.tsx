"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import {
  LayoutDashboard,
  BookOpen,
  Search,
  FileText,
  LineChart,
  Zap,
  UserCircle,
  TrendingUp,
  GraduationCap,
  Settings,
  LogOut,
  Network,
} from "lucide-react";

import styles from "./sidebar.module.css";

const MENU_ITEMS = {
  admin: [
    { name: "Dashboard",          icon: LayoutDashboard, path: "/admin" },
    { name: "Users",             icon: UserCircle,      path: "/admin/users" },
    { name: "CV Repository",      icon: FileText,        path: "/admin/cvs" },
    { name: "Technical Dictionary",icon: BookOpen,       path: "/admin/taxonomy" },
    { name: "Graph Relations",    icon: Network,         path: "/admin/relations" },
    { name: "System Settings",    icon: Settings,        path: "/admin/settings" },
  ],
  user: [
    { name: "Dashboard",   icon: LayoutDashboard, path: "/user" },
    { name: "Job Market",  icon: Search,          path: "/user/jobs" },
    { name: "My CVs",     icon: FileText,        path: "/user/cv" },
    { name: "Gap Analysis", icon: LineChart,      path: "/user/analysis" },
    { name: "Recommended",  icon: Zap,             path: "/user/recommend" },
  ],
  student: [
    { name: "Learning Path",    icon: TrendingUp,     path: "/student" },
    { name: "Skill Explorer",  icon: GraduationCap,   path: "/student/skills" },
    { name: "Courses",         icon: BookOpen,        path: "/student/courses" },
    { name: "Student Profile", icon: UserCircle,     path: "/student/profile" },
  ],
};

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const items = user?.role ? (MENU_ITEMS[user.role] as any[] ?? []) : [];

  return (
    <aside className={styles.sidebar}>
      {/* Brand */}
      <div className={styles.brand}>
        <div className={styles.brandIcon}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>
        <div>
          <div className={styles.brandName}>LUMIX AI</div>
          <div className={styles.brandSub}>Career Nexus</div>
        </div>
      </div>

      {/* Nav */}
      <div className={styles.navLabel}>Navigation</div>
      <nav className={styles.nav}>
        {items.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link key={item.name} href={item.path}>
              <div className={`${styles.item} ${isActive ? styles.active : ""}`}>
                <item.icon className={styles.icon} width={20} height={20} />
                <span className={styles.label}>{item.name}</span>
                {isActive && <div className={styles.dot} />}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* User footer */}
      <div className={styles.footer}>
        <div className={styles.user}>
          <div className={styles.avatar}>
            {user?.email[0] ?? "?"}
          </div>
          <div className="overflow-hidden">
            <div className={styles.userEmail}>{user?.email}</div>
            <div className={styles.userRole}>{user?.role}</div>
          </div>
        </div>

        <button onClick={logout} className={styles.logout}>
          <LogOut width={16} height={16} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}

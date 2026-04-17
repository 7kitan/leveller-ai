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
    { name: "Users",              icon: UserCircle,      path: "/admin/users" },
    { name: "CV Repository",       icon: FileText,        path: "/admin/cvs" },
    { name: "Course Catalog",      icon: BookOpen,        path: "/admin/courses" },
    { name: "Job Portal",          icon: Search,          path: "/admin/jobs" },
    { name: "Technical Dictionary",icon: BookOpen,        path: "/admin/taxonomy" },
    { name: "Graph Relations",     icon: Network,         path: "/admin/relations" },
    { name: "System Settings",     icon: Settings,        path: "/admin/settings" },
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

export interface NavItem {
  name: string;
  icon: React.ComponentType<{ width?: number; height?: number; className?: string; size?: number; title?: string }>;
  path: string;
}

interface SidebarProps {
  isCollapsed?: boolean;
  isMobileOpen?: boolean;
  setIsMobileOpen?: (v: boolean) => void;
  /** Pass admin nav items when rendering from admin layout (overrides role-based lookup) */
  adminItems?: NavItem[];
}

export default function Sidebar({
  isCollapsed,
  isMobileOpen,
  setIsMobileOpen,
  adminItems,
}: SidebarProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const { theme } = useTheme();

  // Use passed adminItems if provided (admin layout); otherwise fall back to role-based
  const items: NavItem[] = adminItems
    ?? (user?.role ? (MENU_ITEMS[user.role] ?? []) : []);

  // Only show mini version (icons only) if collapsed AND not open as a mobile drawer
  const isMini = isCollapsed && !isMobileOpen;

  return (
    <aside className={`${styles.sidebar} ${isMini ? styles.collapsed : ""} ${isMobileOpen ? styles.mobileOpen : ""}`}>
      {/* Brand */}
      <div className={styles.brand}>
        <div className={styles.brandIcon}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>
        {!isMini && (
          <div className={styles.brandTextWrapper}>
            <div className={styles.brandName}>LUMIX AI</div>
            <div className={styles.brandSub}>Career Nexus</div>
          </div>
        )}

        {isMobileOpen && (
          <button className={styles.mobileClose} onClick={() => setIsMobileOpen?.(false)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className={styles.nav}>
        {items.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link
              key={item.path}
              href={item.path}
              onClick={() => setIsMobileOpen?.(false)}
            >
              <div className={`${styles.item} ${isActive ? styles.active : ""}`}>
                <item.icon className={styles.icon} width={20} height={20} title={isMini ? item.name : ""} />
                <span className={styles.label}>{item.name}</span>
                {isActive && <div className={styles.dot} />}
              </div>
            </Link>
          );
        })}
      </nav>

    </aside>
  );
}

"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { useLanguage } from "@/context/LanguageContext";
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
  Globe,
} from "lucide-react";

import styles from "./sidebar.module.css";

const MENU_ITEMS = {
  admin: [
    { key: "nav_dashboard",       icon: LayoutDashboard, path: "/admin" },
    { key: "nav_users",           icon: UserCircle,      path: "/admin/users" },
    { key: "nav_cv",              icon: FileText,        path: "/admin/cvs" },
    { key: "nav_courses",         icon: BookOpen,        path: "/admin/courses" },
    { key: "nav_jobs",            icon: Search,          path: "/admin/jobs" },
    { key: "nav_taxonomy",        icon: BookOpen,        path: "/admin/taxonomy" },
    { key: "nav_relations",       icon: Network,         path: "/admin/relations" },
    { key: "nav_settings",        icon: Settings,        path: "/admin/settings" },
  ],
  user: [
    { key: "nav_dashboard",   icon: LayoutDashboard, path: "/user" },
    { key: "nav_jobs",        icon: Search,          path: "/user/jobs" },
    { key: "nav_cv",          icon: FileText,        path: "/user/cv" },
    { key: "nav_analysis",    icon: LineChart,      path: "/user/analysis" },
    { key: "nav_recommend",   icon: Zap,             path: "/user/recommend" },
  ],
  student: [
    { key: "nav_roadmap",      icon: TrendingUp,     path: "/student" },
    { key: "nav_skills",       icon: GraduationCap,   path: "/student/skills" },
    { key: "nav_courses",      icon: BookOpen,        path: "/student/courses" },
    { key: "nav_profile",      icon: UserCircle,     path: "/student/profile" },
  ],
};

export interface NavItem {
  key: string;
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
  const { language, setLanguage, t } = useLanguage();

  // Use passed adminItems if provided (admin layout); otherwise fall back to role-based
  const items: NavItem[] = adminItems
    ?? (user?.role ? (MENU_ITEMS[user.role as keyof typeof MENU_ITEMS] ?? []) : []);

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
          const translatedName = t(item.key as any);
          return (
            <Link
              key={item.path}
              href={item.path}
              onClick={() => setIsMobileOpen?.(false)}
            >
              <div className={`${styles.item} ${isActive ? styles.active : ""}`}>
                <item.icon className={styles.icon} width={20} height={20} title={isMini ? translatedName : ""} />
                <span className={styles.label}>{translatedName}</span>
                {isActive && <div className={styles.dot} />}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Language Toggle */}
      <div className={styles.footer}>
        <button 
          className={styles.langToggle} 
          onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
          title={language === 'vi' ? "Switch to English" : "Chuyển sang Tiếng Việt"}
        >
          <Globe size={18} />
          {!isMini && <span className={styles.langLabel}>{language.toUpperCase()}</span>}
        </button>
      </div>

    </aside>
  );
}

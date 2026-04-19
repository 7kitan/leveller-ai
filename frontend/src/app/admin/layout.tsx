"use client";

import React from "react";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/shared/Sidebar";
import Navbar from "@/components/shared/Navbar";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import {
  LayoutDashboard,
  UserCircle,
  FileText,
  BookOpen,
  Network,
  Settings,
  Layers,
  Database,
} from "lucide-react";

import styles from "@/components/shared/layout.module.css";
import { cn } from "@/lib/utils";

const ADMIN_NAV_ITEMS = [
  { name: "Dashboard",            icon: LayoutDashboard, path: "/admin" },
  { name: "User Control",          icon: UserCircle,      path: "/admin/users" },
  { name: "CV Repository",         icon: FileText,        path: "/admin/cvs" },
  { name: "Course Catalog",        icon: BookOpen,        path: "/admin/courses" },
  { name: "Job Portal",            icon: Layers,          path: "/admin/jobs" },
  { name: "System Settings",       icon: Settings,        path: "/admin/settings" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const { theme } = useTheme();
  const [isCollapsed, setIsCollapsed] = React.useState(false);
  const [isMobileOpen, setIsMobileOpen] = React.useState(false);

  // Auto-collapse on small screens
  React.useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1280) setIsCollapsed(true);
      if (window.innerWidth < 1024) setIsMobileOpen(false);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Close mobile menu on route change
  React.useEffect(() => {
    setIsMobileOpen(false);
  }, [pathname]);

  const toggleSidebar = () => setIsCollapsed(!isCollapsed);
  const toggleMobileMenu = () => setIsMobileOpen(!isMobileOpen);

  return (
    <div
      className={styles.pageWrapper}
      style={{
        "--sidebar-width": isCollapsed ? "80px" : "288px",
      } as React.CSSProperties}
    >
      {/* Ambient glow decorations */}
      <div className={styles.ambientGlow1} />
      <div className={styles.ambientGlow2} />

      {/* Sidebar */}
      <Sidebar
        isCollapsed={isCollapsed}
        isMobileOpen={isMobileOpen}
        setIsMobileOpen={setIsMobileOpen}
        adminItems={ADMIN_NAV_ITEMS}
      />

      {/* Main content area */}
      <div
        className={cn(
          styles.mainContent,
          styles.contentWithChrome,
          isCollapsed && styles.contentCollapsed
        )}
      >
        {/* Navbar */}
        <Navbar
          toggleSidebar={toggleSidebar}
          toggleMobileMenu={toggleMobileMenu}
          isCollapsed={isCollapsed}
          isMobileOpen={isMobileOpen}
          setIsMobileOpen={setIsMobileOpen}
        />

        <main className={cn(styles.pageContainer, styles.animateIn)}>
          {children}
        </main>

        <footer className={styles.footer}>
          &copy; 2026 Lumix AI &bull; Career Nexus &bull; V6.5
        </footer>
      </div>

      {/* Mobile backdrop */}
      <div
        className={cn(
          styles.mobileBackdrop,
          isMobileOpen && styles.mobileBackdropVisible
        )}
        onClick={() => setIsMobileOpen(false)}
      />
    </div>
  );
}

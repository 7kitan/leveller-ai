"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { useLanguage } from "@/context/LanguageContext";
import {
  LogOut, Bell, Globe,
  LayoutDashboard, BookOpen, Search, FileText,
  LineChart, Zap, UserCircle, TrendingUp, GraduationCap, Settings, Network,
} from "lucide-react";

import styles from "./navbar.module.css";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { UserRole } from "@/types/roles";

// MENU_ITEMS removed - unified in Sidebar.tsx

export default function Navbar({
  toggleSidebar, toggleMobileMenu, isCollapsed, isMobileOpen, setIsMobileOpen,
}: {
  toggleSidebar: () => void;
  toggleMobileMenu: () => void;
  isCollapsed: boolean;
  isMobileOpen: boolean;
  setIsMobileOpen: (v: boolean) => void;
}) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const { language, setLanguage, t } = useLanguage();
  const pathname = usePathname();
  const [isUserMenuOpen, setIsUserMenuOpen] = React.useState(false);
  const userMenuRef = React.useRef<HTMLDivElement>(null);

  // Close user menu on click outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };
    if (isUserMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isUserMenuOpen]);

  // Close menus on route change
  React.useEffect(() => {
    setIsUserMenuOpen(false);
    setIsMobileOpen(false);
  }, [pathname, setIsMobileOpen]);

  if (!user) return null;

  const dashboardPath =
    user.role === UserRole.ADMIN
      ? "/admin"
      : user.role === UserRole.STUDENT
      ? "/student"
      : "/user";

  return (
    <nav className={styles.navbar}>
      <div className={styles.container}>

        {/* Left: Mobile Toggle + Desktop Collapse} */}
        <div className={styles.left}>
          {/* Mobile hamburger */}
          <button className={styles.mobileHamburger} onClick={toggleMobileMenu}>
             <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/>
             </svg>
          </button>
        </div>

        {/* Right: Search + theme toggle + notifications + user */}
        <div className={styles.right}>
          <div className={styles.searchWrapper}>
            <div className={styles.inputWrapper}>
              <svg className={styles.inputIcon} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
              <input type="text" placeholder={t("search_placeholder")} className={styles.input} />
            </div>
          </div>

          <div className={styles.actions}>
            <button 
              onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
              className={styles.langToggle}
              title={language === 'vi' ? "Switch to English" : "Chuyển sang Tiếng Việt"}
            >
              <Globe width="16" height="16" />
              <span>{language === 'vi' ? '🇻🇳' : '🇺🇸'}</span>
              <span className={styles.langText}>{language.toUpperCase()}</span>
            </button>
            <button onClick={toggle} className={styles.iconBtn}>
              {theme === "dark" ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
              )}
            </button>
            <button className={styles.iconBtn}>
              <Bell width="18" height="18" />
              <span className={styles.iconBadge} />
            </button>
          </div>

          <div className={styles.userProfile} ref={userMenuRef}>
            <div 
              className={styles.userTrigger} 
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            >
              <div className={styles.userInfo}>
                <span className={styles.userName}>{user.full_name || user.email.split("@")[0]}</span>
              </div>
              <div className={cn(styles.avatar, isUserMenuOpen && styles.avatarActive)}>
                 {(user.full_name?.[0] || user.email[0]).toUpperCase()}
              </div>
            </div>

            {/* Profile Dropdown */}
            <AnimatePresence>
              {isUserMenuOpen && (
                <motion.div 
                  className={styles.userDropdown}
                  initial={{ opacity: 0, scale: 0.95, y: 10 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: 10 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                >
                  <div className={styles.dropdownHeader}>
                    <div className={styles.dropdownAvatar}>
                      {(user.full_name?.[0] || user.email[0]).toUpperCase()}
                    </div>
                    <div className={styles.dropdownInfo}>
                      {user.full_name && (
                        <div className={styles.dropdownName}>{user.full_name}</div>
                      )}
                      <div className={styles.dropdownEmail}>{user.email}</div>
                      <div className={styles.dropdownRole}>{user.role}</div>
                    </div>
                  </div>
                  
                  <div className={styles.dropdownDivider} />
                  
                  <div className={styles.dropdownBody}>
                    <Link href={user.role === UserRole.ADMIN ? '/admin/profile' : '/user/profile'} className={styles.dropdownItem}>
                      <UserCircle width={18} height={18} />
                      <span>{t("profile_info")}</span>
                    </Link>
                    {user.role === UserRole.ADMIN && (
                      <Link href="/admin/settings" className={styles.dropdownItem}>
                        <Settings width={18} height={18} />
                        <span>{t("nav_settings")}</span>
                      </Link>
                    )}
                  </div>

                  <div className={styles.dropdownDivider} />
                  
                  <button onClick={logout} className={cn(styles.dropdownItem, styles.logoutAction)}>
                    <LogOut width={18} height={18} />
                    <span>{t("logout")}</span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </nav>
  );
}

"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { LogOut, Bell } from "lucide-react";

import styles from "./navbar.module.css";

export default function Navbar() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();

  if (!user) return null;

  const dashboardPath =
    user.role === "admin"
      ? "/admin"
      : user.role === "student"
      ? "/student"
      : "/user";

  return (
    <nav className={styles.navbar}>
      <div className={styles.container}>

        {/* Left: logo + search */}
        <div className={styles.left}>
          <Link href={dashboardPath} className={styles.brandLink}>
            <div className={styles.brandIcon}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
            </div>
            <span className={styles.brandText}>
              LUMIX<span className={styles.brandAccent}>AI</span>
            </span>
          </Link>

          <div className={styles.searchWrapper}>
            <div className={styles.divider} />
            <div className={styles.inputWrapper}>
              <svg className={styles.inputIcon} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
              <input type="text" placeholder="Quick search..." className={styles.input} />
            </div>
          </div>
        </div>

        {/* Right: theme toggle + notifications + user */}
        <div className={styles.right}>

          <div className={styles.actions}>
            {/* Theme toggle */}
            <button
              onClick={toggle}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              className={styles.iconBtn}
            >
              {theme === "dark" ? (
                /* Sun icon */
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
                </svg>
              ) : (
                /* Moon icon */
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
              )}
            </button>

            {/* Notifications */}
            <button className={styles.iconBtn}>
              <Bell width="18" height="18" />
              <span className={styles.iconBadge} />
            </button>
          </div>

          <div className={styles.userProfile}>
            <div className={styles.userInfo}>
              <span className={styles.userName}>
                {user.email.split("@")[0]}
              </span>
              <span className={styles.userRole}>
                {user.role}
              </span>
            </div>

            <div className={styles.avatar}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
              </svg>
            </div>

            <button
              onClick={logout}
              className={styles.logoutBtn}
              title="Logout"
            >
              <LogOut width="16" height="16" />
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

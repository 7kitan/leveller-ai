"use client";

import React from "react";
import Sidebar from "./Sidebar";
import Navbar from "./Navbar";
import { usePathname } from "next/navigation";

import styles from "./layout.module.css";

const LayoutWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname();

  // Determine chrome visibility based on route
  const isAuthPage  = pathname.startsWith("/auth");
  const showChrome = !isAuthPage && pathname !== "/";

  return (
    <div className={styles.pageWrapper}>
      {/* Ambient glow decorations — dark mode only (hidden via CSS in light mode) */}
      <div className={styles.ambientGlow1} />
      <div className={styles.ambientGlow2} />

      {showChrome && <Sidebar />}

      <div className={showChrome ? styles.contentWithSidebar : ""}>
        {showChrome && <Navbar />}

        <main className={showChrome ? styles.pageContainer : ""}>
          <div className={styles.animateIn}>
            {children}
          </div>
        </main>

        {showChrome && (
          <footer className={styles.footer}>
            &copy; 2026 Lumix AI &bull; Career Nexus Architecture &bull; V6.0
          </footer>
        )}
      </div>
    </div>
  );
};

export default LayoutWrapper;

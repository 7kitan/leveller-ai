"use client";

import React from "react";
import Sidebar from "./Sidebar";
import Navbar from "./Navbar";
import { usePathname } from "next/navigation";
import dynamic from "next/dynamic";

const AuthGuard = dynamic(() => import("@/components/auth/AuthGuard"), { ssr: false });

import styles from "./layout.module.css";
import { cn } from "@/lib/utils";

const LayoutWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = React.useState(false);
  const [isMobileOpen, setIsMobileOpen] = React.useState(false);

  // Determine chrome visibility based on route
  const isAuthPage   = pathname.startsWith("/auth");
  const isLandingPage = pathname === "/";
  const isAdminPage  = pathname.startsWith("/admin");
  const showChrome  = !isAuthPage && !isLandingPage && !isAdminPage;

  // Auto-collapse on small screens (but keep expanded on large ones)
  React.useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1280) setIsCollapsed(true);
      if (window.innerWidth < 1024) setIsMobileOpen(false); // Close mobile menu if resizing up
    };
    handleResize(); // Initial check
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
        "--sidebar-width": showChrome ? (isCollapsed ? "80px" : "288px") : "0px"
      } as React.CSSProperties}
    >
      {/* Ambient glow decorations */}
      {showChrome && (
        <>
          <div className={styles.ambientGlow1} />
          <div className={styles.ambientGlow2} />
        </>
      )}

      {showChrome && (
        <Sidebar 
          isCollapsed={isCollapsed} 
          isMobileOpen={isMobileOpen} 
          setIsMobileOpen={setIsMobileOpen} 
        />
      )}

      <div className={cn(
        styles.mainContent,
        showChrome && styles.contentWithChrome,
        isCollapsed && styles.contentCollapsed
      )}>
        {showChrome && (
          <Navbar
            toggleSidebar={toggleSidebar}
            toggleMobileMenu={toggleMobileMenu}
            isCollapsed={isCollapsed}
            isMobileOpen={isMobileOpen}
            setIsMobileOpen={setIsMobileOpen}
          />
        )}

        <main className={showChrome ? styles.pageContainer : ""}>
          <AuthGuard>
            {showChrome ? (
              <div className={styles.animateIn}>
                {children}
              </div>
            ) : (
              children
            )}
          </AuthGuard>
        </main>

        {showChrome && (
          <footer className={styles.footer}>
            &copy; 2026 Lumix AI &bull; Career Nexus &bull; V6.5
          </footer>
        )}
      </div>

      {/* Mobile Backdrop */}
      {showChrome && (
        <div
          className={cn(
            styles.mobileBackdrop,
            isMobileOpen && styles.mobileBackdropVisible
          )}
          onClick={() => setIsMobileOpen(false)}
        />
      )}
    </div>
  );
};

export default LayoutWrapper;

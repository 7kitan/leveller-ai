"use client";

import { useAuth } from "@/context/AuthContext";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";
import styles from "./auth-guard.module.css";
import { cn } from "@/lib/utils";
import MaintenanceOverlay from "@/components/shared/MaintenanceOverlay";
import { UserRole } from "@/types/roles";

interface AuthGuardProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
  requireRole?: UserRole;
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children, requireAdmin, requireRole }) => {
  const { user, loading, maintenanceMode } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  // ── 1. Redirection & Authorization Logic ────────────────────────────
  useEffect(() => {
    // Only run redirection logic if NOT in maintenance
    if (!loading && !maintenanceMode) {
      if (!user) {
        // Unauthenticated users can only view public routes
        const publicRoutes = ["/", "/login", "/register", "/auth/login", "/auth/register", "/auth", "/auth/forgot-password", "/auth/reset-password"];
        if (!publicRoutes.includes(pathname)) {
          router.push("/");
        }
      } else {
        // Authenticated user logic
        const userRole = user?.role;

        // 1. Redirection from homepage to dashboard - ONLY if role exists
        if (pathname === "/" && userRole) {
          router.push(`/${userRole}`);
          return;
        }

        // 2. Prevent accessing wrong role dashboards - ONLY if role exists
        if (userRole) {
          if (pathname.startsWith("/admin") && userRole !== UserRole.ADMIN) {
            router.push(`/${userRole}`);
          } else if (pathname.startsWith("/user") && userRole !== UserRole.USER) {
            router.push(`/${userRole}`);
          } else if (pathname.startsWith("/student") && userRole !== UserRole.STUDENT) {
            router.push(`/${userRole}`);
          }
        }

        // 3. Explicit role requirement check
        if (requireRole && userRole !== requireRole) {
          router.push(`/${userRole}`);
        }
        if (requireAdmin && userRole !== UserRole.ADMIN) {
          router.push(`/${userRole}`);
        }
      }
    }
  }, [user, loading, router, pathname, requireRole, requireAdmin, maintenanceMode]);

  // ── 2. Loading State ───────────────────────────────────────────────
  if (loading) {
    return (
      <div className={styles.loadingOverlay}>
        <div className={styles.spinnerContainer}>
          <div className={cn(styles.spinner, styles.outerSpinner)}></div>
          <div className={cn(styles.spinner, styles.innerSpinner)}></div>
        </div>
      </div>
    );
  }

  // ── 3. Rendering ───────────────────────────────────────────────────
  const isAdmin = user?.role === UserRole.ADMIN;
  const isCriticalPath = ["/auth/login", "/login"].includes(pathname);
  const showMaintenance = maintenanceMode && !isAdmin && !isCriticalPath;

  // Hide protected content if redirects are about to happen
  const publicRoutes = ["/", "/login", "/register", "/auth/login", "/auth/register", "/auth", "/auth/forgot-password", "/auth/reset-password"];
  const isAuthorized = !user ? publicRoutes.includes(pathname) : true;

  if (!isAuthorized && !showMaintenance) return null;

  return (
    <>
      {showMaintenance ? (
        <MaintenanceOverlay />
      ) : (
        children
      )}
    </>
  );
};

export default AuthGuard;

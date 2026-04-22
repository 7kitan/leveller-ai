"use client";

import { useAuth } from "@/context/AuthContext";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";
import styles from "./auth-guard.module.css";
import { cn } from "@/lib/utils";
import MaintenanceOverlay from "@/components/shared/MaintenanceOverlay";

interface AuthGuardProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
  requireRole?: 'admin' | 'user' | 'student';
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children, requireAdmin, requireRole }) => {
  const { user, loading, maintenanceMode, maintenanceDuration } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading) {
      if (!user) {
        // Unauthenticated users can only view public routes
        const publicRoutes = ["/", "/login", "/register", "/auth/login", "/auth/register", "/auth"];
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
          if (pathname.startsWith("/admin") && userRole !== "admin") {
            router.push(`/${userRole}`);
          } else if (pathname.startsWith("/user") && userRole !== "user") {
            router.push(`/${userRole}`);
          } else if (pathname.startsWith("/student") && userRole !== "student") {
            router.push(`/${userRole}`);
          }
        }

        // 3. Explicit role requirement check
        if (requireRole && userRole !== requireRole) {
          router.push(`/${userRole}`);
        }
        if (requireAdmin && userRole !== "admin") {
          router.push(`/${userRole}`);
        }
      }
    }
  }, [user, loading, router, pathname, requireRole, requireAdmin]);

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

  // Hide protected content if redirects are about to happen
  const publicRoutes = ["/", "/login", "/register", "/auth/login", "/auth/register", "/auth"];
  const isAuthorized = !user ? publicRoutes.includes(pathname) : true;
  if (!isAuthorized && !loading) return null;

  // ── Maintenance Mode Gate ──────────────────────────────────────────
  // Allow admins and critical paths during maintenance
  const isCriticalPath = ["/auth/login", "/login"].includes(pathname);
  const isAdmin = user?.role === "admin";
  
  if (maintenanceMode && !isAdmin && !isCriticalPath) {
    return <MaintenanceOverlay isAdmin={!!user} duration={maintenanceDuration} />;
  }

  return <>{children}</>;
};

export default AuthGuard;

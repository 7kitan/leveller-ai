"use client";

import { useAuth } from "@/context/AuthContext";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";

interface AuthGuardProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
  requireRole?: 'admin' | 'user' | 'student';
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children, requireAdmin, requireRole }) => {
  const { user, loading } = useAuth();
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
      <div className="fixed inset-0 bg-[#030508] flex items-center justify-center">
        <div className="relative w-24 h-24">
          <div className="absolute inset-0 rounded-full border-4 border-violet-500/20 border-t-violet-500 animate-spin"></div>
          <div className="absolute inset-4 rounded-full border-4 border-cyan-500/20 border-b-cyan-500 animate-spin [animation-duration:1.5s]"></div>
        </div>
      </div>
    );
  }

  // Hide protected content if redirects are about to happen
  const publicRoutes = ["/", "/login", "/register", "/auth/login", "/auth/register", "/auth"];
  const isAuthorized = !user ? publicRoutes.includes(pathname) : true;
  if (!isAuthorized && !loading) return null;

  return <>{children}</>;
};

export default AuthGuard;

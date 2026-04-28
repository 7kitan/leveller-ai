"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";
import api from "@/lib/api";

import { UserRole } from "@/types/roles";

interface User {
  id: string;
  email: string;
  role: UserRole;
  full_name?: string;
}

interface AuthContextType {
  user: User | null;
  login: (user: User, token: string) => void;
  logout: () => void;
  loading: boolean;
  maintenanceMode: boolean;
  maintenanceDuration: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [maintenanceDuration, setMaintenanceDuration] = useState("");

  // 1. Global Axios interceptor to handle 503 Maintenance Mode silently
  // Setup this BEFORE initializeAuth to catch errors during startup
  useEffect(() => {
    const interceptor = api.interceptors.response.use(
      (response) => response,
      (error) => {
        // Catch 503 Service Unavailable with maintenance flag
        if (error.response?.status === 503 && error.response?.data?.maintenance) {
          setMaintenanceMode(true);
          const duration = error.response.data.duration;
          if (duration) setMaintenanceDuration(duration);
          
          return Promise.reject({ ...error, _silent: true });
        }
        return Promise.reject(error);
      }
    );

    // Listen for global maintenance mode events from api interceptor
    const handleMaintenanceEvent = (event: CustomEvent) => {
      if (event.detail?.active) {
        setMaintenanceMode(true);
        setMaintenanceDuration(event.detail.duration || "");
      }
    };

    if (typeof window !== "undefined") {
      window.addEventListener("maintenanceMode", handleMaintenanceEvent as EventListener);
    }

    return () => {
      api.interceptors.response.eject(interceptor);
      if (typeof window !== "undefined") {
        window.removeEventListener("maintenanceMode", handleMaintenanceEvent as EventListener);
      }
    };
  }, []);

  // 2. Initialize Auth & Detect Maintenance
  useEffect(() => {
    const initializeAuth = async () => {
      const storedUser = typeof window !== 'undefined' ? localStorage.getItem("auth_user") : null;
      const storedToken = typeof window !== 'undefined' ? localStorage.getItem("auth_token") : null;
      
      if (!storedUser || !storedToken) {
        setLoading(false);
        return;
      }

      try {
        // Verify token with backend - Authorization header is automatically added by api interceptor
        const res = await api.get("auth/me", {
          timeout: 8000 
        });
        
        if (res.data) {
          const userData = res.data;
          setUser(userData);
          setMaintenanceMode(res.data.MAINTENANCE_MODE || false);
          setMaintenanceDuration(res.data.MAINTENANCE_DURATION || "");
          localStorage.setItem("auth_user", JSON.stringify(userData));
        }
      } catch (e: any) {
        // Check if this is a maintenance mode error (503)
        if (e.maintenanceMode) {
          setMaintenanceMode(true);
          setMaintenanceDuration(e.maintenanceDuration || "");
          console.log("Maintenance mode active:", e.maintenanceMessage);
        } else if (e.response?.status === 503 && e.response?.data?.maintenance) {
          // Fallback: direct check of response data
          setMaintenanceMode(true);
          setMaintenanceDuration(e.response.data.duration || "");
          console.log("Maintenance mode active:", e.response.data.detail);
        } else if (e._silent) {
          setMaintenanceMode(true);
        } else {
          console.error("Session verification failed:", e.message);
          // If token is invalid or server error, clear everything
          logout();
        }
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = (userData: User, token: string) => {
    setUser(userData);
    localStorage.setItem("auth_user", JSON.stringify(userData));
    localStorage.setItem("auth_token", token);
  };

  const logout = async () => {
    try {
      // Authorization header will be automatically added by api interceptor
      await api.post("auth/logout");
    } catch (e) {
      console.error("Logout error", e);
    }
    setUser(null);
    localStorage.removeItem("auth_user");
    localStorage.removeItem("auth_token");
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, maintenanceMode, maintenanceDuration }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};


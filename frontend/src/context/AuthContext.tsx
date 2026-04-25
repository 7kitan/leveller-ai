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
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
  loading: boolean;
  maintenanceMode: boolean;
  maintenanceDuration: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
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

    return () => api.interceptors.response.eject(interceptor);
  }, []);

  // 2. Initialize Auth & Detect Maintenance
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = typeof window !== 'undefined' ? localStorage.getItem("auth_token") : null;
      
      if (!storedToken) {
        setLoading(false);
        return;
      }

      try {
        // Verify token with backend - retrieves user data AND maintenance status
        // Added 8s timeout to prevent hanging the app forever
        const res = await api.get("auth/verify", {
          params: { token: storedToken },
          timeout: 8000 
        });
        
        if (res.data) {
          const userData = res.data;
          setUser(userData);
          setToken(storedToken);
          setMaintenanceMode(res.data.maintenance_mode || false);
          setMaintenanceDuration(res.data.maintenance_duration || "");
          localStorage.setItem("auth_user", JSON.stringify(userData));
        }
      } catch (e: any) {
        if (e._silent) {
          setMaintenanceMode(true);
        } else {
          console.error("Session verification failed:", e.message);
          // If token is invalid or server is slow, clear everything and allow access to public pages
          logout();
        }
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = (newToken: string, userData: User) => {
    setToken(newToken);
    setUser(userData);
    localStorage.setItem("auth_token", newToken);
    localStorage.setItem("auth_user", JSON.stringify(userData));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading, maintenanceMode, maintenanceDuration }}>
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


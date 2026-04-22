"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

interface User {
  id: string;
  email: string;
  role: 'admin' | 'user' | 'student';
  full_name?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
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

  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem("auth_token");
      if (storedToken) {
        try {
          // Verify token with backend - retrieves user data AND maintenance status
          const res = await axios.get("/api/auth/verify", {
            params: { token: storedToken },
            headers: { Authorization: `Bearer ${storedToken}` }
          });
          
          if (res.data) {
            const userData = res.data;
            if (!userData.role) {
              userData.role = userData.is_admin ? 'admin' : 'user';
            }
            setUser(userData);
            setToken(storedToken);
            setMaintenanceMode(res.data.maintenance_mode || false);
            setMaintenanceDuration(res.data.maintenance_duration || "");
            // Sync localStorage
            localStorage.setItem("auth_user", JSON.stringify(userData));
          }
        } catch (e: any) {
          // If it's the silent maintenance error from our interceptor, do nothing
          if (e._silent) return;
          
          console.error("Session verification failed", e.message);
          logout();
        }
      } else {
        // Even if not logged in, check if system is under maintenance for non-auth pages
        try {
          // Public check if possible, or just fail silently
          // For now, let AuthGuard handle public path logic
        } catch (e) {}
      }
      setLoading(false);
    };

    initializeAuth();
  }, []);

  // Global Axios interceptor to handle 503 Maintenance Mode silently
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        // Catch 503 Service Unavailable with maintenance flag
        if (error.response?.status === 503 && error.response?.data?.maintenance) {
          // Sync maintenance state quietly
          if (!maintenanceMode) {
            setMaintenanceMode(true);
            const duration = error.response.data.duration;
            if (duration) setMaintenanceDuration(duration);
          }
          
          // Return a custom silent error object instead of a full AxiosError
          // This prevents standard "Request failed with status code 503" logs in many environments
          return Promise.reject({ ...error, _silent: true });
        }
        return Promise.reject(error);
      }
    );

    return () => axios.interceptors.response.eject(interceptor);
  }, [maintenanceMode]);

  const login = (newToken: string, userData: User) => {
    // Ensure role exists during login
    if (!userData.role) {
      userData.role = (userData as any).is_admin ? 'admin' : 'user';
    }
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

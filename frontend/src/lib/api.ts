import axios from "axios";

/**
 * Axios instance with automatic Authorization header and maintenance mode handling.
 * 
 * Authentication: Uses Bearer token stored in localStorage
 * Token is sent via Authorization header (not cookies)
 */
const getBaseURL = () => {
  const url = process.env.NEXT_PUBLIC_API_URL || "";
  if (!url) return "";
  return url.endsWith("/") ? url : `${url}/`;
};

const api = axios.create({
  baseURL: getBaseURL(),
});

// Request interceptor: Add Authorization header from localStorage
api.interceptors.request.use((config) => {
  // Fix: Axios strips the path from baseURL if the URL starts with a leading slash
  if (config.url && config.url.startsWith("/")) {
    config.url = config.url.substring(1);
  }

  // Add Authorization header if token exists
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }

  return config;
});

// Response interceptor: Handle 401 (redirect to login) and 503 (maintenance mode)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Handle 401 Unauthorized - Token expired or invalid
    if (error.response?.status === 401) {
      // Clear auth data and redirect to login
      if (typeof window !== "undefined") {
        localStorage.removeItem("auth_user");
        localStorage.removeItem("auth_token");
        
        // Only redirect if not already on auth pages
        if (!window.location.pathname.includes("/auth/login") && 
            !window.location.pathname.includes("/auth/register")) {
          window.location.href = "/auth/login";
        }
      }
      return Promise.reject(error);
    }

    // Handle maintenance mode (503)
    if (error.response?.status === 503) {
      const maintenanceData = error.response.data;
      if (maintenanceData?.maintenance) {
        // Attach maintenance info to error for AuthContext to handle
        error.maintenanceMode = true;
        error.maintenanceDuration = maintenanceData.duration || "Không xác định";
        error.maintenanceMessage = maintenanceData.detail || "Hệ thống đang bảo trì";
        
        // Trigger global maintenance mode event
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("maintenanceMode", {
            detail: {
              active: true,
              duration: maintenanceData.duration || "Không xác định",
              message: maintenanceData.detail || "Hệ thống đang bảo trì"
            }
          }));
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;

import axios from "axios";

/**
 * Axios instance with automatic Authorization header and maintenance mode handling.
 */
const getBaseURL = () => {
  const url = process.env.NEXT_PUBLIC_API_URL || "";
  if (!url) return "";
  return url.endsWith("/") ? url : `${url}/`;
};

const api = axios.create({
  baseURL: getBaseURL(),
});

// Request interceptor: Add Authorization header and fix baseURL stripping
api.interceptors.request.use((config) => {
  // Fix: Axios strips the path from baseURL if the URL starts with a leading slash
  // e.g. baseURL: 'http://localhost:8000', url: '/auth' -> 'http://localhost:8000/auth'
  // Removing the leading slash ensures it becomes 'http://localhost:8000/auth'
  if (config.url && config.url.startsWith("/")) {
    config.url = config.url.substring(1);
  }

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("auth_token");
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Response interceptor: Handle maintenance mode (503) or other global errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // We can handle global errors here if needed
    // The AuthContext also has an interceptor, but using a central instance is cleaner
    return Promise.reject(error);
  }
);

export default api;

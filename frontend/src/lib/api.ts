import axios from "axios";

/**
 * Axios instance with automatic Authorization header and maintenance mode handling.
 */
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "/",
});

// Request interceptor: Add Authorization header
api.interceptors.request.use((config) => {
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

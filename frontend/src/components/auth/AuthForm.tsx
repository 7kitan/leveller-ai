"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import axios from "axios";
import { Loader2, LogIn, UserPlus, AlertCircle } from "lucide-react";
import styles from "./auth-form.module.css";

interface AuthFormProps {
  initialMode?: "login" | "register";
}

export default function AuthForm({ initialMode = "login" }: AuthFormProps) {
  const [isLogin, setIsLogin] = useState(initialMode === "login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const endpoint = isLogin ? "/api/auth/login" : "/api/auth/register";
      const res = await axios.post(endpoint, { email, password });
      
      const { access_token, user } = res.data;
      
      login(access_token, user);
      
      const userRole = user.role || (user.is_admin ? 'admin' : 'user');
      router.push(`/${userRole}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Đã xảy ra lỗi vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.formWrapper}>
      <div className={styles.gradientBg} />
      
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        className={styles.panel}
      >
        <div className={styles.header}>
          <motion.div
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            className={styles.iconBox}
          >
            {isLogin ? <LogIn className="h-8 w-8" /> : <UserPlus className="h-8 w-8" />}
          </motion.div>
          <h2 className={styles.title}>
            {isLogin ? "Chào mừng trở lại" : "Tạo tài khoản mới"}
          </h2>
          <p className={styles.subtitle}>
            {isLogin ? "Đăng nhập để tiếp tục hành trình sự nghiệp" : "Bắt đầu tối ưu hóa sự nghiệp của bạn ngay hôm nay"}
          </p>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.inputGroup}>
            <div className="relative group">
              <input
                type="email"
                required
                className={styles.inputField}
                placeholder="Địa chỉ Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="relative group">
              <input
                type="password"
                required
                className={styles.inputField}
                placeholder="Mật khẩu"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <motion.div 
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className={styles.errorBox}
            >
              <AlertCircle className="h-4 w-4" /> {error}
            </motion.div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className={styles.submitBtn}
            >
              {loading ? (
                <Loader2 className="h-6 w-6 animate-spin" />
              ) : (
                <span className="flex items-center">
                  {isLogin ? "Đăng Nhập" : "Đăng Ký"}
                </span>
              )}
            </button>
          </div>
        </form>

        <div className={styles.toggleWrapper}>
          <button 
            onClick={() => setIsLogin(!isLogin)}
            className={styles.toggleBtn}
          >
            {isLogin ? "Chưa có tài khoản? Đăng ký ngay" : "Đã có tài khoản? Đăng nhập"}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

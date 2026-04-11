"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import axios from "axios";
import { Loader2, LogIn, UserPlus, AlertCircle } from "lucide-react";

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
      
      if (user.is_admin) {
        router.push("/admin");
      } else {
        router.push("/cv");
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Đã xảy ra lỗi vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4 bg-[#0a0a0c]">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5 pointer-events-none" />
      
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel w-full max-w-md space-y-8 rounded-3xl p-10 shadow-2xl relative z-10"
      >
        <div className="text-center">
          <motion.div
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-500/10 text-violet-500 mb-6"
          >
            {isLogin ? <LogIn className="h-8 w-8" /> : <UserPlus className="h-8 w-8" />}
          </motion.div>
          <h2 className="text-3xl font-bold tracking-tight text-white neon-text-violet">
            {isLogin ? "Chào mừng trở lại" : "Tạo tài khoản mới"}
          </h2>
          <p className="mt-3 text-sm text-gray-400">
            {isLogin ? "Đăng nhập để tiếp tục hành trình sự nghiệp" : "Bắt đầu tối ưu hóa sự nghiệp của bạn ngay hôm nay"}
          </p>
        </div>

        <form className="mt-10 space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div className="relative group">
              <input
                type="email"
                required
                className="w-full rounded-2xl border border-white/10 bg-white/5 p-4 text-white transition-all focus:border-violet-500/50 focus:bg-white/10 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                placeholder="Địa chỉ Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="relative group">
              <input
                type="password"
                required
                className="w-full rounded-2xl border border-white/10 bg-white/5 p-4 text-white transition-all focus:border-violet-500/50 focus:bg-white/10 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
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
              className="flex items-center gap-2 text-sm text-red-500 bg-red-500/10 p-4 rounded-xl border border-red-500/20"
            >
              <AlertCircle className="h-4 w-4" /> {error}
            </motion.div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="group flex w-full items-center justify-center rounded-2xl bg-violet-600 py-4 font-bold text-white shadow-xl shadow-violet-500/20 transition-all hover:bg-violet-500 hover:scale-[1.02] active:scale-95 disabled:opacity-50"
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

        <div className="text-center pt-4">
          <button 
            onClick={() => setIsLogin(!isLogin)}
            className="text-sm font-medium text-gray-400 transition-colors hover:text-white"
          >
            {isLogin ? "Chưa có tài khoản? Đăng ký ngay" : "Đã có tài khoản? Đăng nhập"}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

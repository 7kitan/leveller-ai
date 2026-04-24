"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import axios from "axios";
import { Loader2, AlertCircle } from "lucide-react";
import LandingNavbar from "@/components/landing/LandingNavbar";
import { useLanguage } from "@/context/LanguageContext";
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
  const { t } = useLanguage();
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
      setError(err.response?.data?.detail || t("auth_error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.formWrapper}>
      <LandingNavbar />
      
      <div className={styles.backgroundDecoration} />
      
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className={styles.panel}
      >
        <div className={styles.header}>
          <h2 className={styles.title}>
            {isLogin ? t("login_title") : t("register_title")}
          </h2>
          <p className={styles.subtitle}>
            {isLogin ? t("login_subtitle") : t("register_subtitle")}
          </p>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.inputGroup}>
            <input
              type="email"
              required
              className={styles.inputField}
              placeholder={t("email_placeholder")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className={styles.inputGroup}>
            <input
              type="password"
              required
              className={styles.inputField}
              placeholder={t("password_placeholder")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {error && (
            <div className={styles.errorBox}>
              <AlertCircle size={18} /> {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className={styles.submitBtn}
          >
            {loading ? (
              <Loader2 size={24} className={styles.animateSpin} />
            ) : (
              <span>
                {isLogin ? t("login_btn") : t("register_btn")}
              </span>
            )}
          </button>
        </form>

        <button 
          onClick={() => setIsLogin(!isLogin)}
          className={styles.toggleBtn}
        >
          {isLogin ? t("to_register") : t("to_login")}
        </button>
      </motion.div>
    </div>
  );
}

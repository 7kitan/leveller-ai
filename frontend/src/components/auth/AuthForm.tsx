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
import ReCAPTCHA from "react-google-recaptcha";
import Link from "next/link";

interface AuthFormProps {
  initialMode?: "login" | "register";
}

export default function AuthForm({ initialMode = "login" }: AuthFormProps) {
  const [isLogin, setIsLogin] = useState(initialMode === "login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const [showCaptcha, setShowCaptcha] = useState(false);
  const [captchaToken, setCaptchaToken] = useState("");
  
  const { login } = useAuth();
  const { t } = useLanguage();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const endpoint = isLogin ? "/api/auth/login" : "/api/auth/register";
      const payload = isLogin ? { email, password, captcha_token: captchaToken } : { email, password };
      const res = await axios.post(endpoint, payload);
      
      const { access_token, user } = res.data;
      
      login(access_token, user);
      
      const userRole = user.role || (user.is_admin ? 'admin' : 'user');
      router.push(`/${userRole}`);
    } catch (err: any) {
      if (err.response?.headers?.['x-requires-captcha'] === 'true') {
        setShowCaptcha(true);
        setError("Vui lòng xác nhận bạn không phải là robot.");
      } else {
        setError(err.response?.data?.detail || t("auth_error"));
      }
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

          {isLogin && (
            <div className="flex justify-end -mt-4 mb-4">
              <Link href="/auth/forgot-password" className="text-xs text-indigo-500 hover:underline">
                Quên mật khẩu?
              </Link>
            </div>
          )}

          {(showCaptcha || !isLogin) && (
            <div className="mb-4 flex justify-center">
              <ReCAPTCHA
                sitekey={process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || ""}
                onChange={(token) => setCaptchaToken(token || "")}
                theme="dark"
              />
            </div>
          )}

          {error && (
            <div className={styles.errorBox}>
              <AlertCircle size={18} /> {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || (showCaptcha && !captchaToken)}
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
          onClick={() => {
            setIsLogin(!isLogin);
            setError("");
            setShowCaptcha(false);
          }}
          className={styles.toggleBtn}
        >
          {isLogin ? t("to_register") : t("to_login")}
        </button>
      </motion.div>
    </div>
  );
}

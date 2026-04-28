"use client";

import React, { useState, useRef, useMemo, useEffect } from "react";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { Loader2, AlertCircle, Eye, EyeOff } from "lucide-react";
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
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const [showCaptcha, setShowCaptcha] = useState(false);
  const [captchaToken, setCaptchaToken] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const recaptchaRef = useRef<ReCAPTCHA>(null);
  
  const { login } = useAuth();
  const { theme } = useTheme();
  const { t } = useLanguage();
  const router = useRouter();

  const isFormValid = useMemo(() => {
    const isEmailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    const isPasswordValid = password.length >= 8;
    const isNameValid = isLogin || (fullName.trim().length >= 2);
    const isCaptchaValid = !showCaptcha || !!captchaToken;
    
    return isEmailValid && isPasswordValid && isNameValid && isCaptchaValid;
  }, [email, password, fullName, isLogin, showCaptcha, captchaToken, t]);

  useEffect(() => {
    const checkCaptchaStatus = async () => {
      try {
        const res = await api.get("auth/captcha-status");
        if (res.data.requires_captcha) {
          setShowCaptcha(true);
        }
      } catch (err) {
        // Silently ignore pre-check errors
      }
    };
    checkCaptchaStatus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const endpoint = isLogin ? "/auth/login" : "/auth/register";
      const payload = isLogin 
        ? { email, password, captcha_token: captchaToken } 
        : { email, password, full_name: fullName, captcha_token: captchaToken };
      const res = await api.post(endpoint, payload);
      
      const { user, access_token } = res.data;
      
      login(user, access_token);
      
      const userRole = user.role;
      router.push(`/${userRole}`);
    } catch (err: any) {
      // Reset captcha on any error (token is consumed)
      setCaptchaToken("");
      recaptchaRef.current?.reset();
      
      if (err.response?.headers?.['x-requires-captcha'] === 'true') {
        setShowCaptcha(true);
        setError(t("recaptcha_required"));
      } else {
        const detail = err.response?.data?.detail || t("auth_error");
        setError(Array.isArray(detail) ? detail[0]?.msg : (typeof detail === 'object' ? (detail as any).msg : detail));
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
          {!isLogin && (
            <div className={styles.inputGroup}>
              <input
                type="text"
                required
                className={styles.inputField}
                placeholder={t("full_name_placeholder")}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                maxLength={255}
                minLength={2}
              />
            </div>
          )}
          <div className={styles.inputGroup}>
            <input
              type="email"
              required
              className={styles.inputField}
              placeholder={t("email_placeholder")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              maxLength={255}
            />
          </div>
          <div className={styles.inputGroup}>
            <div className={styles.passwordWrapper}>
              <input
                type={showPassword ? "text" : "password"}
                required
                className={styles.inputField}
                placeholder={t("password_placeholder")}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                maxLength={128}
                minLength={8}
              />
              <button
                type="button"
                className={styles.eyeBtn}
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          {isLogin && (
            <div className={styles.forgotPasswordContainer}>
              <Link href="/auth/forgot-password" className={styles.forgotPassword}>
                {t("forgot_password_link")}
              </Link>
            </div>
          )}

          {(showCaptcha || !isLogin) && (
            <div className="mb-4 flex justify-center">
              <ReCAPTCHA
                ref={recaptchaRef}
                sitekey={process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || ""}
                onChange={(token) => setCaptchaToken(token || "")}
                theme={theme === "dark" ? "dark" : "light"}
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
            disabled={loading || !isFormValid}
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
            setCaptchaToken("");
            recaptchaRef.current?.reset();
          }}
          className={styles.toggleBtn}
        >
          {isLogin ? t("to_register") : t("to_login")}
        </button>
      </motion.div>
    </div>
  );
}



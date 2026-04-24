"use client";

import React, { useState, useRef } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import { Loader2, AlertCircle, CheckCircle, ArrowLeft } from "lucide-react";
import Link from "next/link";
import ReCAPTCHA from "react-google-recaptcha";
import LandingNavbar from "@/components/landing/LandingNavbar";
import { useLanguage } from "@/context/LanguageContext";
import styles from "@/components/auth/auth-form.module.css";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const recaptchaRef = useRef<ReCAPTCHA>(null);
  const { t } = useLanguage();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!captchaToken) {
      setError(t("auth_error")); // or a specific "please complete captcha" message
      return;
    }

    setLoading(true);
    setError("");

    try {
      await axios.post("/api/auth/forgot-password", { 
        email,
        captcha_token: captchaToken 
      });
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || t("forgot_password_error"));
      // Reset captcha on error
      setCaptchaToken(null);
      recaptchaRef.current?.reset();
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
        className={styles.panel}
      >
        <div className={styles.header}>
          <h2 className={styles.title}>{t("forgot_password_title")}</h2>
          <p className={styles.subtitle}>
            {t("forgot_password_subtitle")}
          </p>
        </div>

        {success ? (
          <div className="text-center space-y-6 py-8">
            <div className="flex justify-center">
              <div className="bg-emerald-500/10 p-4 rounded-full">
                <CheckCircle className="text-emerald-500" size={48} />
              </div>
            </div>
            <p className="text-sm opacity-80">
              {t("forgot_password_success_msg")}
            </p>
            <Link href="/auth/login" className="flex items-center justify-center gap-2 text-indigo-500 font-bold hover:underline">
              <ArrowLeft size={16} /> {t("forgot_password_back_to_login")}
            </Link>
          </div>
        ) : (
          <form className={styles.form} onSubmit={handleSubmit}>
            <div className={styles.inputGroup}>
              <input
                type="email"
                required
                className={styles.inputField}
                placeholder={t("forgot_password_email_placeholder")}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div className="flex justify-center py-2">
              <ReCAPTCHA
                ref={recaptchaRef}
                sitekey={process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"}
                onChange={(token) => setCaptchaToken(token)}
                theme="light"
              />
            </div>

            {error && (
              <div className={styles.errorBox}>
                <AlertCircle size={18} /> {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !captchaToken}
              className={styles.submitBtn}
            >
              {loading ? (
                <Loader2 size={24} className="animate-spin" />
              ) : (
                t("forgot_password_btn")
              )}
            </button>

            <Link href="/auth/login" className={styles.toggleBtn} style={{ textAlign: 'center', display: 'block' }}>
              {t("forgot_password_back_to_login")}
            </Link>
          </form>
        )}
      </motion.div>
    </div>
  );
}

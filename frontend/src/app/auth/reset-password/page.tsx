"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import { Loader2, AlertCircle, CheckCircle, ArrowLeft, Lock } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import LandingNavbar from "@/components/landing/LandingNavbar";
import { useLanguage } from "@/context/LanguageContext";
import styles from "@/components/auth/auth-form.module.css";

export default function ResetPasswordPage() {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const { t } = useLanguage();

  useEffect(() => {
    if (!token) {
      setError(t("reset_password_invalid_token"));
    }
  }, [token, t]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError(t("reset_password_mismatch"));
      return;
    }
    if (password.length < 6) {
      setError(t("reset_password_min_length"));
      return;
    }

    setLoading(true);
    setError("");

    try {
      await axios.post("/api/auth/reset-password", { 
        token, 
        new_password: password 
      });
      setSuccess(true);
      setTimeout(() => {
        router.push("/auth/login");
      }, 3000);
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
        className={styles.panel}
      >
        <div className={styles.header}>
          <h2 className={styles.title}>{t("reset_password_title")}</h2>
          <p className={styles.subtitle}>
            {t("reset_password_subtitle")}
          </p>
        </div>

        {success ? (
          <div className="text-center space-y-6 py-8">
            <div className="flex justify-center">
              <div className="bg-emerald-500/10 p-4 rounded-full">
                <CheckCircle className="text-emerald-500" size={48} />
              </div>
            </div>
            <p className="text-sm font-bold text-emerald-500">
              {t("reset_password_success_msg")}
            </p>
            <p className="text-xs opacity-60"> {t("reset_password_redirecting")} </p>
          </div>
        ) : (
          <form className={styles.form} onSubmit={handleSubmit}>
            <div className={styles.inputGroup}>
              <input
                type="password"
                required
                disabled={!token}
                className={styles.inputField}
                placeholder={t("reset_password_new_password_placeholder")}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                maxLength={128}
                minLength={8}
              />
            </div>
            <div className={styles.inputGroup}>
              <input
                type="password"
                required
                disabled={!token}
                className={styles.inputField}
                placeholder={t("reset_password_confirm_password_placeholder")}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                maxLength={128}
                minLength={8}
              />
            </div>

            {error && (
              <div className={styles.errorBox}>
                <AlertCircle size={18} /> {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !token}
              className={styles.submitBtn}
            >
              {loading ? (
                <Loader2 size={24} className="animate-spin" />
              ) : (
                t("reset_password_btn")
              )}
            </button>
          </form>
        )}
      </motion.div>
    </div>
  );
}

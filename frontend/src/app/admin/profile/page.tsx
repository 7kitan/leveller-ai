"use client";

import React, { useState, useEffect } from "react";
import styles from "./admin-profile.module.css";
import { User, Lock, Mail, ShieldCheck, Save, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useLanguage } from "@/context/LanguageContext";
import AuthGuard from "@/components/auth/AuthGuard";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";

export default function AdminProfilePage() {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [profile, setProfile] = useState({
    email: "",
    full_name: "",
  });
  const [passwords, setPasswords] = useState({
    oldPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    fetchProfile();
  }, [token]);

  const fetchProfile = async () => {
    if (!token) return;
    try {
      setIsLoading(true);
      const res = await api.get("auth/me");
      setProfile({
        email: res.data.email,
        full_name: res.data.full_name || "",
      });
    } catch (err: any) {
      setError(t("profile_load_error"));
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Validate passwords if provided
    if (passwords.newPassword && passwords.newPassword !== passwords.confirmPassword) {
      setError(t("profile_confirm_password_mismatch"));
      return;
    }

    try {
      setIsSaving(true);
      const updateData: any = { full_name: profile.full_name };
      if (passwords.newPassword) {
        updateData.old_password = passwords.oldPassword;
        updateData.password = passwords.newPassword;
      }

      await api.patch("auth/profile", updateData);

      setSuccess(t("profile_update_success"));
      setPasswords({ oldPassword: "", newPassword: "", confirmPassword: "" });
    } catch (err: any) {
      setError(err.response?.data?.detail || t("auth_error"));
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <PageHeader 
          title={t("profile_title")}
          subtitle={t("profile_subtitle")}
        />

        <form onSubmit={handleUpdateProfile} className={styles.profileCard}>
          <div className={styles.cardSection}>
            <h2 className={styles.sectionTitle}>
              <User size={16} /> {t("profile_basic_info")}
            </h2>
            
            <div className={styles.inputGroup}>
              <label className={styles.label}>{t("profile_email_label")}</label>
              <div className={styles.inputWrapper}>
                <Mail className={styles.inputIcon} size={18} />
                <input 
                  type="email" 
                  value={profile.email} 
                  disabled 
                  className={styles.input}
                />
              </div>
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>{t("profile_name_label")}</label>
              <div className={styles.inputWrapper}>
                <User className={styles.inputIcon} size={18} />
                <input 
                  type="text" 
                  placeholder={t("profile_name_placeholder")}
                  value={profile.full_name}
                  onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  className={styles.input}
                  maxLength={255}
                />
              </div>
            </div>
          </div>

          <div className={styles.cardSection}>
            <h2 className={styles.sectionTitle}>
              <Lock size={16} /> {t("profile_security_title")}
            </h2>

            <div className={styles.inputGroup}>
              <label className={styles.label}>{t("profile_old_password_label")}</label>
              <div className={styles.inputWrapper}>
                <Lock className={styles.inputIcon} size={18} />
                <input 
                  type="password" 
                  placeholder={t("profile_old_password_placeholder")}
                  value={passwords.oldPassword}
                  onChange={(e) => setPasswords({ ...passwords, oldPassword: e.target.value })}
                  className={styles.input}
                  maxLength={128}
                />
              </div>
            </div>
            
            <div className={styles.inputGroup}>
              <label className={styles.label}>{t("profile_new_password_label")}</label>
              <div className={styles.inputWrapper}>
                <ShieldCheck className={styles.inputIcon} size={18} />
                <input 
                  type="password" 
                  placeholder={t("profile_new_password_placeholder")}
                  value={passwords.newPassword}
                  onChange={(e) => setPasswords({ ...passwords, newPassword: e.target.value })}
                  className={styles.input}
                  maxLength={128}
                  minLength={8}
                />
              </div>
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label}>{t("profile_confirm_password_label")}</label>
              <div className={styles.inputWrapper}>
                <Lock className={styles.inputIcon} size={18} />
                <input 
                  type="password" 
                  placeholder={t("profile_confirm_password_placeholder")}
                  value={passwords.confirmPassword}
                  onChange={(e) => setPasswords({ ...passwords, confirmPassword: e.target.value })}
                  className={styles.input}
                  maxLength={128}
                  minLength={8}
                />
              </div>
            </div>
          </div>

          {error && (
            <div className={styles.errorBox}>
              <AlertCircle size={18} />
              {error}
            </div>
          )}

          {success && (
            <div className={styles.successBox}>
              <CheckCircle2 size={18} />
              {success}
            </div>
          )}

          <div className={styles.actionRow}>
            <button 
              type="submit" 
              disabled={isSaving}
              className={styles.submitBtn}
            >
              {isSaving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save size={16} />
              )}
              {t("profile_save_btn")}
            </button>
          </div>
        </form>
      </PageContainer>
    </AuthGuard>
  );
}



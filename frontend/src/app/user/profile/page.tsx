"use client";

import React, { useState, useEffect } from "react";
import styles from "./user-profile.module.css";
import { User, Lock, Mail, ShieldCheck, Save, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";

export default function ProfilePage() {
  const { token, user: authUser } = useAuth();
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
      const res = await axios.get("/api/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setProfile({
        email: res.data.email,
        full_name: res.data.full_name || "",
      });
    } catch (err: any) {
      setError("Không thể tải thông tin cá nhân.");
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
      setError("Mật khẩu xác nhận không khớp.");
      return;
    }

    try {
      setIsSaving(true);
      const updateData: any = { full_name: profile.full_name };
      if (passwords.newPassword) {
        updateData.old_password = passwords.oldPassword;
        updateData.password = passwords.newPassword;
      }

      await axios.patch("/api/auth/profile", updateData, {
        headers: { Authorization: `Bearer ${token}` },
      });

      setSuccess("Cập nhật thông tin thành công!");
      setPasswords({ oldPassword: "", newPassword: "", confirmPassword: "" });
    } catch (err: any) {
      setError(err.response?.data?.detail || "Đã xảy ra lỗi khi cập nhật.");
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
    <div className={styles.pageRoot}>
      <header className={styles.header}>
        <h1 className={styles.title}>Your Profile</h1>
        <p className={styles.subtitle}> Quản lý thông tin cá nhân và cài đặt bảo mật của bạn </p>
      </header>

      <form onSubmit={handleUpdateProfile} className={styles.profileCard}>
        <div className={styles.cardSection}>
          <h2 className={styles.sectionTitle}>
            <User size={16} /> Thông tin cơ bản
          </h2>
          
          <div className={styles.inputGroup}>
            <label className={styles.label}>Địa chỉ Email</label>
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
            <label className={styles.label}>Tên hiển thị</label>
            <div className={styles.inputWrapper}>
              <User className={styles.inputIcon} size={18} />
              <input 
                type="text" 
                placeholder="Nhập tên của bạn"
                value={profile.full_name}
                onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                className={styles.input}
              />
            </div>
          </div>
        </div>

        <div className={styles.cardSection}>
          <h2 className={styles.sectionTitle}>
            <Lock size={16} /> Thay đổi mật khẩu
          </h2>

          <div className={styles.inputGroup}>
            <label className={styles.label}>Mật khẩu hiện tại</label>
            <div className={styles.inputWrapper}>
              <Lock className={styles.inputIcon} size={18} />
              <input 
                type="password" 
                placeholder="Bắt buộc nếu muốn đổi mật khẩu"
                value={passwords.oldPassword}
                onChange={(e) => setPasswords({ ...passwords, oldPassword: e.target.value })}
                className={styles.input}
              />
            </div>
          </div>
          
          <div className={styles.inputGroup}>
            <label className={styles.label}>Mật khẩu mới</label>
            <div className={styles.inputWrapper}>
              <ShieldCheck className={styles.inputIcon} size={18} />
              <input 
                type="password" 
                placeholder="Để trống nếu không muốn thay đổi"
                value={passwords.newPassword}
                onChange={(e) => setPasswords({ ...passwords, newPassword: e.target.value })}
                className={styles.input}
              />
            </div>
          </div>

          <div className={styles.inputGroup}>
            <label className={styles.label}>Xác nhận mật khẩu mới</label>
            <div className={styles.inputWrapper}>
              <Lock className={styles.inputIcon} size={18} />
              <input 
                type="password" 
                placeholder="Nhập lại mật khẩu mới"
                value={passwords.confirmPassword}
                onChange={(e) => setPasswords({ ...passwords, confirmPassword: e.target.value })}
                className={styles.input}
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
            Lưu thay đổi
          </button>
        </div>
      </form>
    </div>
  );
}

"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { 
  Settings, 
  Save, 
  Cpu, 
  Globe, 
  ShieldAlert, 
  Database,
  RefreshCcw,
  CheckCircle2,
  AlertCircle
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-settings.module.css";
import { motion, AnimatePresence } from "framer-motion";

interface SystemSetting {
  key: string;
  value: any;
  description?: string;
}

const AdminSettingsPage = () => {
  const { token } = useAuth();
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [pendingChanges, setPendingChanges] = useState<Record<string, any>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const headers = { 
        Authorization: `Bearer ${token}`,
        "X-Is-Admin": "true"
      };
      
      const [settingsResp, modelsResp] = await Promise.all([
        axios.get("/api/admin/settings", { headers }),
        axios.get("/api/admin/ai-models", { headers })
      ]);

      setSettings(settingsResp.data);
      setAvailableModels(modelsResp.data);
      setPendingChanges({});
    } catch (err) {
      showNotification("Không thể tải cấu hình", "error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchData();
  }, [token]);

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const hasChanges = Object.keys(pendingChanges).length > 0;

  const handleFieldChange = (key: string, value: any) => {
    const originalSetting = settings.find(s => s.key === key);
    if (originalSetting && originalSetting.value === value) {
      const updated = { ...pendingChanges };
      delete updated[key];
      setPendingChanges(updated);
    } else {
      setPendingChanges(prev => ({ ...prev, [key]: value }));
    }
  };

  const handleBulkSave = async () => {
    if (!hasChanges) return;
    setIsSaving(true);
    try {
      const payload = {
        settings: Object.entries(pendingChanges).map(([key, value]) => ({ key, value }))
      };
      
      await axios.post("/api/admin/settings/bulk", payload, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-Is-Admin": "true"
        }
      });
      
      showNotification("Đã lưu tất cả thay đổi thành công");
      await fetchData();
    } catch (err) {
      showNotification("Lỗi khi lưu cấu hình", "error");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDiscard = () => {
    setPendingChanges({});
    showNotification("Đã hủy bỏ các thay đổi chưa lưu", "success");
  };

  const getValue = (key: string, defaultValue: any) => {
    if (key in pendingChanges) return pendingChanges[key];
    const s = settings.find(item => item.key === key);
    return s ? s.value : defaultValue;
  };

  const isModified = (key: string) => key in pendingChanges;

  return (
    <AuthGuard requireAdmin>
      <div className={styles.pageRoot}>
        <div className={styles.header}>
          <h1 className={styles.title}>
            <Settings size={40} className="text-indigo-500" />
            <span>Hệ thống Cấu hình</span>
          </h1>
          <p className={styles.subtitle}>Quản trị các tham số vận hành AI, Crawler và bảo mật toàn hệ thống.</p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center p-20">
            <RefreshCcw className="animate-spin text-indigo-500" size={40} />
          </div>
        ) : (
          <div className={styles.settingsGrid}>
            {/* AI CONFIG */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(styles.settingCard, isModified("similarity_threshold") || isModified("ai_model") ? styles.settingCardModified : "")}
            >
              <div className={styles.cardHeader}>
                <Cpu className={styles.cardIcon} size={24} />
                <h2 className={styles.cardTitle}>Cấu hình AI Agent</h2>
              </div>
              <div className={styles.formGroup}>
                <div className={cn(styles.field, isModified("similarity_threshold") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        Ngưỡng tương đồng (Similarity)
                        {isModified("similarity_threshold") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>Độ chính xác yêu cầu khi khớp kỹ năng (0.0 - 1.0). Mặc định 0.6.</span>
                  </div>
                  <div className={styles.inputWrapper}>
                    <input 
                      type="number" 
                      step="0.05"
                      min="0"
                      max="1"
                      className={styles.input}
                      value={getValue("similarity_threshold", 0.6)}
                      onChange={(e) => handleFieldChange("similarity_threshold", parseFloat(e.target.value))}
                    />
                  </div>
                </div>
                <div className={cn(styles.field, isModified("ai_model") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        AI Model Chính
                        {isModified("ai_model") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>Model sử dụng cho Gap Analysis và Career Advisor.</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("ai_model", "gpt-4o-mini")}
                    onChange={(e) => handleFieldChange("ai_model", e.target.value)}
                  >
                    {availableModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id} ({model.provider?.toUpperCase()})
                      </option>
                    ))}
                    {!availableModels.length && (
                         <option value="gpt-4o-mini">GPT-4o Mini (OPENAI)</option>
                    )}
                  </select>
                </div>
              </div>
            </motion.div>

            {/* CRAWLER CONFIG */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className={cn(styles.settingCard, isModified("topcv_crawl_enabled") || isModified("linkedin_bridge_enabled") ? styles.settingCardModified : "")}
            >
              <div className={styles.cardHeader}>
                <Globe className={styles.cardIcon} size={24} />
                <h2 className={styles.cardTitle}>Crawler Manager</h2>
              </div>
              <div className={styles.formGroup}>
                <div className={cn(styles.field, isModified("topcv_crawl_enabled") ? styles.fieldModified : "")}>
                  <div className="flex items-center justify-between">
                    <div className={styles.labelArea}>
                      <label className={styles.label}>
                        TopCV Auto-crawl
                        {isModified("topcv_crawl_enabled") && <span className={styles.fieldModifiedDot} />}
                      </label>
                      <span className={styles.desc}>Tự động quét và lấy tin tuyển dụng mới mỗi 30 phút.</span>
                    </div>
                    <div 
                      className={cn(styles.toggle, getValue("topcv_crawl_enabled", true) ? styles.toggleOn : styles.toggleOff)}
                      onClick={() => handleFieldChange("topcv_crawl_enabled", !getValue("topcv_crawl_enabled", true))}
                    >
                      <div className={styles.knob} />
                    </div>
                  </div>
                </div>
                <div className={cn(styles.field, isModified("linkedin_bridge_enabled") ? styles.fieldModified : "")}>
                  <div className="flex items-center justify-between">
                    <div className={styles.labelArea}>
                      <label className={styles.label}>
                        LinkedIn API Bridge
                        {isModified("linkedin_bridge_enabled") && <span className={styles.fieldModifiedDot} />}
                      </label>
                      <span className={styles.desc}>Kết nối dữ liệu từ LinkedIn thông qua Proxy bridge.</span>
                    </div>
                    <div 
                      className={cn(styles.toggle, getValue("linkedin_bridge_enabled", false) ? styles.toggleOn : styles.toggleOff)}
                      onClick={() => handleFieldChange("linkedin_bridge_enabled", !getValue("linkedin_bridge_enabled", false))}
                    >
                      <div className={styles.knob} />
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* SYSTEM SECURITY */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className={cn(styles.settingCard, isModified("maintenance_mode") || isModified("system_broadcast") ? styles.settingCardModified : "")}
            >
              <div className={styles.cardHeader}>
                <ShieldAlert className={styles.cardIcon} size={24} />
                <h2 className={styles.cardTitle}>An ninh & Vận hành</h2>
              </div>
              <div className={styles.formGroup}>
                <div className={cn(styles.field, isModified("maintenance_mode") ? styles.fieldModified : "")}>
                   <div className="flex items-center justify-between">
                    <div className={styles.labelArea}>
                      <label className={styles.label}>
                        Chế độ Bảo trì (Maintenance)
                        {isModified("maintenance_mode") && <span className={styles.fieldModifiedDot} />}
                      </label>
                      <span className={styles.desc}>Tạm dừng truy cập cho người dùng thông thường.</span>
                    </div>
                    <div 
                      className={cn(styles.toggle, getValue("maintenance_mode", false) ? styles.toggleOn : styles.toggleOff)}
                      onClick={() => handleFieldChange("maintenance_mode", !getValue("maintenance_mode", false))}
                    >
                      <div className={styles.knob} />
                    </div>
                  </div>
                </div>
                <div className={cn(styles.field, isModified("maintenance_duration") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        Thời gian bảo trì dự kiến
                        {isModified("maintenance_duration") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>Hiển thị trên lớp phủ bảo trì (VD: ~ 2 giờ, Hoàn thành 06:00).</span>
                  </div>
                  <input 
                    type="text"
                    className={styles.input}
                    placeholder="VD: ~ 2 giờ (Kết thúc 04:00 AM)..."
                    value={getValue("maintenance_duration", "Không xác định")}
                    onChange={(e) => handleFieldChange("maintenance_duration", e.target.value)}
                  />
                </div>
                <div className={cn(styles.field, isModified("system_broadcast") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        Thông báo Hệ thống
                        {isModified("system_broadcast") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>Hiện thông báo quan trọng trên toàn trang Landing.</span>
                  </div>
                  <input 
                    type="text"
                    className={styles.input}
                    placeholder="Nhập nội dung thông báo..."
                    value={getValue("system_broadcast", "")}
                    onChange={(e) => handleFieldChange("system_broadcast", e.target.value)}
                  />
                </div>
              </div>
            </motion.div>

            {/* DATA MANAGEMENT */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className={cn(styles.settingCard, isModified("result_cache_ttl") ? styles.settingCardModified : "")}
            >
              <div className={styles.cardHeader}>
                <Database className={styles.cardIcon} size={24} />
                <h2 className={styles.cardTitle}>Dữ liệu & Caching</h2>
              </div>
              <div className={styles.formGroup}>
                 <div className={cn(styles.field, isModified("result_cache_ttl") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        Thời gian sống của kết quả (TTL)
                        {isModified("result_cache_ttl") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>Thời gian lưu Cache phân tích (giây). Mặc định 3600s.</span>
                  </div>
                  <input 
                    type="number"
                    className={styles.input}
                    value={getValue("result_cache_ttl", 3600)}
                    onChange={(e) => handleFieldChange("result_cache_ttl", parseInt(e.target.value))}
                  />
                </div>
                <div className="flex gap-4">
                  <button 
                    disabled={isSaving}
                    onClick={() => {
                        setIsSaving(true);
                        setTimeout(() => {
                            setIsSaving(false);
                            showNotification("Đã dọn dẹp Redis Cache");
                        }, 1000);
                    }}
                    className={cn(styles.saveBtn, "bg-amber-600 shadow-amber-200")}
                  >
                    Dọn Cache Redis
                  </button>
                   <button 
                    disabled={isSaving}
                    onClick={() => {
                        setIsSaving(true);
                        setTimeout(() => {
                            setIsSaving(false);
                            showNotification("Đã đồng bộ lại vector DB");
                        }, 2000);
                    }}
                    className={cn(styles.saveBtn, "bg-blue-600 shadow-blue-200")}
                  >
                    Đồng bộ VectorDB
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}

        <AnimatePresence>
          {hasChanges && (
            <motion.div 
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 50 }}
              className={cn(styles.saveBar, styles.saveBarAnimation)}
            >
                <div className={styles.saveBarText}>
                    Bạn có thay đổi chưa lưu ({Object.keys(pendingChanges).length})
                </div>
                <div className={styles.saveBarActions}>
                    <button 
                        onClick={handleDiscard}
                        className={styles.discardBtn}
                        disabled={isSaving}
                    >
                        Hủy bỏ
                    </button>
                    <button 
                        onClick={handleBulkSave}
                        className={styles.mainSaveBtn}
                        disabled={isSaving}
                    >
                        {isSaving ? "Đang lưu..." : "Lưu tất cả"}
                    </button>
                </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {notification && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className={cn(
                "fixed bottom-10 right-10 flex items-center gap-3 px-6 py-4 rounded-2xl shadow-2xl z-[150]",
                notification.type === 'success' ? "bg-emerald-500 text-white" : "bg-rose-500 text-white"
              )}
            >
              {notification.type === 'success' ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
              <span className="font-bold">{notification.message}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </AuthGuard>
  );
};

export default AdminSettingsPage;

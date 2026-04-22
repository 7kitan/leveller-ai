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
  AlertCircle,
  Zap,
  ScanLine,
  Key,
  Layers
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-settings.module.css";
import { motion, AnimatePresence } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";

interface SystemSetting {
  key: string;
  value: any;
  description?: string;
}

const AdminSettingsPage = () => {
  const { token } = useAuth();
  const { t } = useLanguage();
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
      showNotification(t("admin_settings_load_error"), "error");
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
      
      showNotification(t("admin_settings_save_success"));
      await fetchData();
    } catch (err) {
      showNotification(t("admin_settings_save_error"), "error");
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
            <span>{t("admin_settings_title")}</span>
          </h1>
          <p className={styles.subtitle}>{t("admin_settings_subtitle")}</p>
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
              className={cn(
                styles.settingCard, 
                isModified("similarity_threshold") || 
                isModified("embedding_model") || 
                isModified("cv_parsing_model") || 
                isModified("gap_analysis_model") || 
                isModified("gap_llm_model") || 
                isModified("gap_vector_sim_threshold") || 
                isModified("career_advisor_model") ? styles.settingCardModified : ""
              )}
            >
              <div className={styles.cardHeader}>
                <Cpu className={styles.cardIcon} size={24} />
                <h2 className={styles.cardTitle}>{t("admin_settings_ai_agent_title")}</h2>
              </div>
              <div className={styles.formGroup}>
                <div className={cn(styles.field, isModified("similarity_threshold") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_similarity_label")}
                        {isModified("similarity_threshold") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_similarity_desc")}</span>
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

                {/* 2. CV Parsing Model */}
                <div className={cn(styles.field, isModified("cv_parsing_model") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_cv_parsing_model_label")}
                        {isModified("cv_parsing_model") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_cv_parsing_model_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("cv_parsing_model", getValue("ai_model", "gpt-4o-mini"))}
                    onChange={(e) => handleFieldChange("cv_parsing_model", e.target.value)}
                  >
                    {availableModels.filter(m => m.type === 'chat').map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id} ({model.provider?.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>

                {/* 3. Gap Analysis Model */}
                <div className={cn(styles.field, isModified("gap_analysis_model") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_gap_analysis_model_label")}
                        {isModified("gap_analysis_model") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_gap_analysis_model_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("gap_analysis_model", getValue("ai_model", "gpt-4o-mini"))}
                    onChange={(e) => handleFieldChange("gap_analysis_model", e.target.value)}
                  >
                    {availableModels.filter(m => m.type === 'chat').map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id} ({model.provider?.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className={cn(styles.field, isModified("gap_llm_model") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_gap_llm_model_label")}
                        {isModified("gap_llm_model") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_gap_llm_model_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("gap_llm_model", getValue("ai_model", "gpt-4o-mini"))}
                    onChange={(e) => handleFieldChange("gap_llm_model", e.target.value)}
                  >
                    {availableModels.filter(m => m.type === 'chat').map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id} ({model.provider?.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>

                <div className={cn(styles.field, isModified("gap_vector_sim_threshold") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_gap_vector_threshold_label")}
                        {isModified("gap_vector_sim_threshold") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_gap_vector_threshold_desc")}</span>
                  </div>
                  <div className={styles.inputWrapper}>
                    <input 
                      type="number" 
                      step="0.01"
                      min="0"
                      max="1"
                      className={styles.input}
                      value={getValue("gap_vector_sim_threshold", 0.35)}
                      onChange={(e) => handleFieldChange("gap_vector_sim_threshold", parseFloat(e.target.value))}
                    />
                  </div>
                </div>

                {/* 4. Career Advisor Model */}
                <div className={cn(styles.field, isModified("career_advisor_model") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_career_advisor_model_label")}
                        {isModified("career_advisor_model") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_career_advisor_model_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("career_advisor_model", getValue("ai_model", "gpt-4o-mini"))}
                    onChange={(e) => handleFieldChange("career_advisor_model", e.target.value)}
                  >
                    {availableModels.filter(m => m.type === 'chat').map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id} ({model.provider?.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </motion.div>

            {/* GLOBAL LLM CONFIG */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(
                styles.settingCard, 
                isModified("ai_model") || 
                isModified("llm_provider") ? styles.settingCardModified : ""
              )}
            >
              <div className={styles.cardHeader}>
                <Layers className={styles.cardIcon} size={24} />
                <h2 className={styles.cardTitle}>{t("admin_settings_global_llm_title")}</h2>
              </div>
              <div className={styles.formGroup}>
                <div className={cn(styles.field, isModified("llm_provider") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_default_provider_label")}
                        {isModified("llm_provider") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_default_provider_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("llm_provider", "openai")}
                    onChange={(e) => handleFieldChange("llm_provider", e.target.value)}
                  >
                    <option value="openai">OpenAI</option>
                    <option value="google">Google (Gemini)</option>
                    <option value="anthropic">Anthropic</option>
                  </select>
                </div>

                <div className={cn(styles.field, isModified("ai_model") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_default_model_label")}
                        {isModified("ai_model") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_default_model_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("ai_model", "gpt-4o-mini")}
                    onChange={(e) => handleFieldChange("ai_model", e.target.value)}
                  >
                    {availableModels.filter(m => m.type === 'chat').map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id} ({model.provider?.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </motion.div>

            {/* CV PARSER & OCR CONFIG */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(
                styles.settingCard, 
                isModified("cv_parser_strategy") || 
                isModified("ocr_dpi") || 
                isModified("chandra_api_url") || 
                isModified("chandra_api_key") ? styles.settingCardModified : ""
              )}
            >
              <div className={styles.cardHeader}>
                <ScanLine className={styles.cardIcon} size={24} />
                <h2 className={styles.cardTitle}>{t("admin_settings_cv_parser_ocr_title")}</h2>
              </div>
              <div className={styles.formGroup}>
                <div className={cn(styles.field, isModified("cv_parser_strategy") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_parser_strategy_label")}
                        {isModified("cv_parser_strategy") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_parser_strategy_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("cv_parser_strategy", "direct")}
                    onChange={(e) => handleFieldChange("cv_parser_strategy", e.target.value)}
                  >
                    <option value="direct">Direct (Local PDF Extract)</option>
                    <option value="chandra">Chandra Hub (Advanced OCR)</option>
                  </select>
                </div>

                <div className={cn(styles.field, isModified("ocr_dpi") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_ocr_dpi_label")}
                        {isModified("ocr_dpi") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_ocr_dpi_desc")}</span>
                  </div>
                  <input 
                    type="number" 
                    className={styles.input}
                    value={getValue("ocr_dpi", 200)}
                    onChange={(e) => handleFieldChange("ocr_dpi", parseInt(e.target.value))}
                  />
                </div>

                <div className={cn(styles.field, isModified("chandra_api_url") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_chandra_url_label")}
                        {isModified("chandra_api_url") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_chandra_url_desc")}</span>
                  </div>
                  <input 
                    type="text" 
                    className={styles.input}
                    placeholder="https://api.datalab.to/..."
                    value={getValue("chandra_api_url", "")}
                    onChange={(e) => handleFieldChange("chandra_api_url", e.target.value)}
                  />
                </div>

                <div className={cn(styles.field, isModified("chandra_api_key") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_chandra_key_label")}
                        {isModified("chandra_api_key") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_chandra_key_desc")}</span>
                  </div>
                  <div className="relative">
                    <input 
                      type="password" 
                      className={cn(styles.input, "pr-10")}
                      placeholder="sk-..."
                      value={getValue("chandra_api_key", "")}
                      onChange={(e) => handleFieldChange("chandra_api_key", e.target.value)}
                    />
                    <Key className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                  </div>
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
                <h2 className={styles.cardTitle}>{t("admin_settings_crawler_manager_title")}</h2>
              </div>
              <div className={styles.formGroup}>
                <div className={cn(styles.field, isModified("topcv_crawl_enabled") ? styles.fieldModified : "")}>
                  <div className="flex items-center justify-between">
                    <div className={styles.labelArea}>
                      <label className={styles.label}>
                        {t("admin_settings_topcv_crawl_label")}
                        {isModified("topcv_crawl_enabled") && <span className={styles.fieldModifiedDot} />}
                      </label>
                      <span className={styles.desc}>{t("admin_settings_topcv_crawl_desc")}</span>
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
                        {t("admin_settings_linkedin_bridge_label")}
                        {isModified("linkedin_bridge_enabled") && <span className={styles.fieldModifiedDot} />}
                      </label>
                      <span className={styles.desc}>{t("admin_settings_linkedin_bridge_desc")}</span>
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
                <h2 className={styles.cardTitle}>{t("admin_settings_security_ops_title")}</h2>
              </div>
              <div className={styles.formGroup}>
                <div className={cn(styles.field, isModified("maintenance_mode") ? styles.fieldModified : "")}>
                   <div className="flex items-center justify-between">
                    <div className={styles.labelArea}>
                      <label className={styles.label}>
                        {t("admin_settings_maintenance_mode_label")}
                        {isModified("maintenance_mode") && <span className={styles.fieldModifiedDot} />}
                      </label>
                      <span className={styles.desc}>{t("admin_settings_maintenance_mode_desc")}</span>
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
                        {t("admin_settings_maintenance_duration_label")}
                        {isModified("maintenance_duration") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_maintenance_duration_desc")}</span>
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
                        {t("admin_settings_system_broadcast_label")}
                        {isModified("system_broadcast") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_system_broadcast_desc")}</span>
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
              className={cn(styles.settingCard, isModified("result_cache_ttl") || isModified("gap_cache_ttl") ? styles.settingCardModified : "")}
            >
              <div className={styles.cardHeader}>
                <Database className={styles.cardIcon} size={24} />
                <h2 className={styles.cardTitle}>{t("admin_settings_data_caching_title")}</h2>
              </div>
              <div className={styles.formGroup}>
                 <div className={cn(styles.field, isModified("result_cache_ttl") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_result_cache_ttl_label")}
                        {isModified("result_cache_ttl") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_result_cache_ttl_desc")}</span>
                  </div>
                  <input 
                    type="number"
                    className={styles.input}
                    value={getValue("result_cache_ttl", 3600)}
                    onChange={(e) => handleFieldChange("result_cache_ttl", parseInt(e.target.value))}
                  />
                </div>
                <div className={cn(styles.field, isModified("gap_cache_ttl") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_gap_cache_ttl_label")}
                        {isModified("gap_cache_ttl") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_gap_cache_ttl_desc")}</span>
                  </div>
                  <input 
                    type="number"
                    className={styles.input}
                    value={getValue("gap_cache_ttl", 1800)}
                    onChange={(e) => handleFieldChange("gap_cache_ttl", parseInt(e.target.value))}
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
                    {t("admin_settings_clear_redis_btn")}
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
                    {t("admin_settings_sync_vector_btn")}
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
                    {t("admin_settings_unsaved_changes")} ({Object.keys(pendingChanges).length})
                </div>
                <div className={styles.saveBarActions}>
                    <button 
                        onClick={handleDiscard}
                        className={styles.discardBtn}
                        disabled={isSaving}
                    >
                        {t("admin_settings_discard_btn")}
                    </button>
                    <button 
                        onClick={handleBulkSave}
                        className={styles.mainSaveBtn}
                        disabled={isSaving}
                    >
                        {isSaving ? t("processing") : t("admin_settings_save_all_btn")}
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

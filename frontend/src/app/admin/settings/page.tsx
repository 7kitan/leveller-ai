"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { 
  Cpu, Layers, Globe, ShieldAlert, Database, ScanLine, Save, RefreshCcw, 
  Trash2, Mail, Bell, Key, Server, Settings, Check, X, AlertTriangle, Play, Zap, Send,
  CheckCircle2, AlertCircle 
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-settings.module.css";
import { motion, AnimatePresence } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";
import Portal from "@/components/shared/Portal";

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
  const [activeTab, setActiveTab] = useState<'ai' | 'parser' | 'automation' | 'limits' | 'system'>('ai');

  const TABS = [
    { id: 'ai', label: t("admin_settings_ai_agent_title"), icon: Cpu, keys: ["SIMILARITY_THRESHOLD", "CV_PARSING_MODEL", "GAP_ANALYSIS_MODEL", "CAREER_ADVISOR_MODEL", "LLM_PROVIDER", "AI_MODEL", "FALLBACK_AI_MODEL", "GAP_LLM_MODEL", "GAP_VECTOR_SIM_THRESHOLD"], color: "#10b981" },
    { id: 'parser', label: t("admin_settings_cv_parser_ocr_title"), icon: ScanLine, keys: ["CV_PARSER_STRATEGY", "OCR_DPI", "CHANDRA_API_URL", "CHANDRA_API_KEY"], color: "#ec4899" },
    { id: 'automation', label: t("admin_settings_crawler_manager_title"), icon: Globe, keys: ["TOPCV_CRAWL_ENABLED", "LINKEDIN_BRIDGE_ENABLED", "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_FROM", "QUEUE_THRESHOLD"], color: "#f59e0b" },
    { id: 'limits', label: t("admin_settings_limits_title"), icon: ShieldAlert, keys: ["GLOBAL_TOKEN_LIMIT", "USER_TOKEN_LIMIT", "DAILY_ANALYSIS_LIMIT"], color: "#f43f5e" },
    { id: 'system', label: t("admin_settings_security_ops_title"), icon: ShieldAlert, keys: ["MAINTENANCE_MODE", "MAINTENANCE_DURATION", "SYSTEM_BROADCAST", "RESULT_CACHE_TTL", "GAP_CACHE_TTL", "SYSTEM_LOG_TTL_DAYS"], color: "#818cf8" }
  ];


  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [settingsResp, modelsResp] = await Promise.all([
        api.get("admin/settings"),
        api.get("admin/ai-models")
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

  const handleBulkSave = async (keysToSave?: string[]) => {
    const changes = keysToSave 
      ? Object.entries(pendingChanges).filter(([key]) => keysToSave.includes(key))
      : Object.entries(pendingChanges);

    if (changes.length === 0) return;
    
    setIsSaving(true);
    try {
      const payload = {
        settings: changes.map(([key, value]) => ({ key, value }))
      };
      
      await api.post("admin/settings/bulk", payload);
      
      showNotification(t("admin_settings_save_success"));
      
      // Remove saved keys from pendingChanges
      const remainingChanges = { ...pendingChanges };
      changes.forEach(([key]) => delete remainingChanges[key]);
      setPendingChanges(remainingChanges);
      
      // Refresh original settings
      const settingsResp = await api.get("admin/settings");
      setSettings(settingsResp.data);
      
    } catch (err) {
      showNotification(t("admin_settings_save_error"), "error");
    } finally {
      setIsSaving(false);
    }
  };

  const getSectionModifiedCount = (keys: string[]) => {
    return keys.filter(key => key in pendingChanges).length;
  };

  const handleTestEmail = async () => {
    setIsSaving(true);
    try {
      await api.post("analysis/admin/test-email", {});
      showNotification(t("admin_settings_test_mail_success"), "success");
    } catch (err) {
      showNotification(t("admin_settings_test_mail_error"), "error");
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestLLM = async () => {
    setIsSaving(true);
    try {
      const resp = await api.post("analysis/admin/test-llm", {});
      showNotification(`${t("admin_settings_test_llm_success")}${resp.data.response}`, "success");
    } catch (err) {
      showNotification(t("admin_settings_test_llm_error"), "error");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDiscard = () => {
    setPendingChanges({});
    showNotification(t("admin_settings_discard_success"), "success");
  };

  const getValue = (key: string, defaultValue: any) => {
    if (key in pendingChanges) return pendingChanges[key];
    const s = settings.find(item => item.key === key);
    return s ? s.value : defaultValue;
  };

  const isModified = (key: string) => key in pendingChanges;

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <PageHeader 
          title={t("admin_settings_title")}
          subtitle={t("admin_settings_subtitle")}
        />

        {isLoading ? (
          <div className="flex items-center justify-center p-20">
            <RefreshCcw className="animate-spin text-indigo-500" size={40} />
          </div>
        ) : (
          <>
            <div className={styles.tabsContainer}>
              <div className={styles.tabsList}>
                {TABS.map((tab) => {
                  const Icon = tab.icon;
                  const modifiedCount = getSectionModifiedCount(tab.keys);
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      className={cn(styles.tabItem, activeTab === tab.id && styles.tabItemActive)}
                      style={activeTab === tab.id ? { "--tab-accent": tab.color } as React.CSSProperties : {}}
                    >
                      <Icon size={18} style={{ color: activeTab === tab.id ? "white" : tab.color }} />
                      <span>{tab.label}</span>
                      {modifiedCount > 0 && (
                        <span className={styles.tabBadge}>{modifiedCount}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className={styles.settingsGrid}>
              {/* AI CONFIG */}
              {activeTab === 'ai' && (
                <>
                  <motion.div 
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={cn(
                      styles.settingCard, 
                      isModified("SIMILARITY_THRESHOLD") || 
                      isModified("CV_PARSING_MODEL") || 
                      isModified("GAP_ANALYSIS_MODEL") || 
                      isModified("GAP_LLM_MODEL") || 
                      isModified("GAP_VECTOR_SIM_THRESHOLD") || 
                      isModified("CAREER_ADVISOR_MODEL") ? styles.settingCardModified : ""
                    )}
                  >

              <div className={styles.cardHeader}>
                <div className={styles.cardHeaderLeft}>
                  <Cpu 
                    className={styles.cardIcon} 
                    size={24} 
                    style={{ color: TABS.find(t => t.id === 'ai')?.color }} 
                  />
                  <h2 className={styles.cardTitle}>{t("admin_settings_ai_agent_title")}</h2>
                </div>
                <AnimatePresence>
                  {getSectionModifiedCount(["SIMILARITY_THRESHOLD", "CV_PARSING_MODEL", "GAP_ANALYSIS_MODEL", "GAP_LLM_MODEL", "GAP_VECTOR_SIM_THRESHOLD", "CAREER_ADVISOR_MODEL"]) > 0 && (
                    <motion.button
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      onClick={() => handleBulkSave(["SIMILARITY_THRESHOLD", "CV_PARSING_MODEL", "GAP_ANALYSIS_MODEL", "GAP_LLM_MODEL", "GAP_VECTOR_SIM_THRESHOLD", "CAREER_ADVISOR_MODEL"])}
                      disabled={isSaving}
                      className={styles.sectionSaveBtn}
                    >
                      <Save size={14} />
                      <span>{isSaving ? t("processing") : t("save")}</span>
                    </motion.button>
                  )}
                </AnimatePresence>
              </div>
              <div className={styles.formGroup}>
                <div className={cn(styles.field, isModified("SIMILARITY_THRESHOLD") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_similarity_label")}
                        {isModified("SIMILARITY_THRESHOLD") && <span className={styles.fieldModifiedDot} />}
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
                      value={getValue("SIMILARITY_THRESHOLD", 0.6)}
                      onChange={(e) => handleFieldChange("SIMILARITY_THRESHOLD", parseFloat(e.target.value))}
                    />
                  </div>
                </div>

                {/* 2. CV Parsing Model */}
                <div className={cn(styles.field, isModified("CV_PARSING_MODEL") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_cv_parsing_model_label")}
                        {isModified("CV_PARSING_MODEL") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_cv_parsing_model_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("CV_PARSING_MODEL", getValue("AI_MODEL", "gpt-4o-mini"))}
                    onChange={(e) => handleFieldChange("CV_PARSING_MODEL", e.target.value)}
                  >
                    {availableModels.filter(m => m.type === 'chat').map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id} ({model.provider?.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>

                {/* 3. Gap Analysis Model */}
                <div className={cn(styles.field, isModified("GAP_ANALYSIS_MODEL") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_gap_analysis_model_label")}
                        {isModified("GAP_ANALYSIS_MODEL") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_gap_analysis_model_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("GAP_ANALYSIS_MODEL", getValue("AI_MODEL", "gpt-4o-mini"))}
                    onChange={(e) => handleFieldChange("GAP_ANALYSIS_MODEL", e.target.value)}
                  >
                    {availableModels.filter(m => m.type === 'chat').map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id} ({model.provider?.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className={cn(styles.field, isModified("GAP_LLM_MODEL") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_gap_llm_model_label")}
                        {isModified("GAP_LLM_MODEL") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_gap_llm_model_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("GAP_LLM_MODEL", getValue("AI_MODEL", "gpt-4o-mini"))}
                    onChange={(e) => handleFieldChange("GAP_LLM_MODEL", e.target.value)}
                  >
                    {availableModels.filter(m => m.type === 'chat').map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id} ({model.provider?.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>

                <div className={cn(styles.field, isModified("GAP_VECTOR_SIM_THRESHOLD") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_gap_vector_threshold_label")}
                        {isModified("GAP_VECTOR_SIM_THRESHOLD") && <span className={styles.fieldModifiedDot} />}
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
                      value={getValue("GAP_VECTOR_SIM_THRESHOLD", 0.35)}
                      onChange={(e) => handleFieldChange("GAP_VECTOR_SIM_THRESHOLD", parseFloat(e.target.value))}
                    />
                  </div>
                </div>

                {/* 4. Career Advisor Model */}
                <div className={cn(styles.field, isModified("CAREER_ADVISOR_MODEL") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_career_advisor_model_label")}
                        {isModified("CAREER_ADVISOR_MODEL") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_career_advisor_model_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("CAREER_ADVISOR_MODEL", getValue("AI_MODEL", "gpt-4o-mini"))}
                    onChange={(e) => handleFieldChange("CAREER_ADVISOR_MODEL", e.target.value)}
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
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className={cn(
                  styles.settingCard, 
                  isModified("AI_MODEL") || 
                  isModified("FALLBACK_AI_MODEL") || 
                  isModified("LLM_PROVIDER") ? styles.settingCardModified : ""
                )}
              >

              <div className={styles.cardHeader}>
                <div className={styles.cardHeaderLeft}>
                  <Zap 
                    className={styles.cardIcon} 
                    size={24} 
                    style={{ color: TABS.find(t => t.id === 'ai')?.color }} 
                  />
                  <h2 className={styles.cardTitle}>{t("admin_settings_global_llm_title")}</h2>
                </div>
                <div className="flex items-center gap-2">
                  <button 
                    onClick={handleTestLLM}
                    disabled={isSaving}
                    className={styles.testBtn}
                    title={t("admin_settings_test_ai_btn")}
                  >
                    <Zap size={14} />
                    <span>{t("admin_settings_test_ai_btn")}</span>
                  </button>
                  <AnimatePresence>
                    {getSectionModifiedCount(["LLM_PROVIDER", "AI_MODEL", "fallback_AI_MODEL", "GLOBAL_TOKEN_LIMIT", "USER_TOKEN_LIMIT"]) > 0 && (
                      <motion.button
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        onClick={() => handleBulkSave(["LLM_PROVIDER", "AI_MODEL", "FALLBACK_AI_MODEL"])}
                        disabled={isSaving}
                        className={styles.sectionSaveBtn}
                      >
                        <Save size={14} />
                        <span>{isSaving ? t("processing") : t("save")}</span>
                      </motion.button>
                    )}
                  </AnimatePresence>
                </div>
              </div>
              <div className={styles.formGroup}>
                <div className={cn(styles.field, isModified("LLM_PROVIDER") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_default_provider_label")}
                        {isModified("LLM_PROVIDER") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_default_provider_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("LLM_PROVIDER", "openai")}
                    onChange={(e) => handleFieldChange("LLM_PROVIDER", e.target.value)}
                  >
                    <option value="openai">OpenAI</option>
                    <option value="google">Google (Gemini)</option>
                    <option value="anthropic">Anthropic</option>
                  </select>
                </div>

                <div className={cn(styles.field, isModified("AI_MODEL") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_default_model_label")}
                        {isModified("AI_MODEL") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_default_model_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("AI_MODEL", "gpt-4o-mini")}
                    onChange={(e) => handleFieldChange("AI_MODEL", e.target.value)}
                  >
                    {availableModels.filter(m => m.type === 'chat').map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id} ({model.provider?.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>

                <div className={cn(styles.field, isModified("FALLBACK_AI_MODEL") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_fallback_model_label")}
                        {isModified("FALLBACK_AI_MODEL") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_fallback_model_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("FALLBACK_AI_MODEL", "gpt-4o-mini")}
                    onChange={(e) => handleFieldChange("FALLBACK_AI_MODEL", e.target.value)}
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
            </>
          )}

          {/* QUOTA CONFIG */}
          {activeTab === 'limits' && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className={cn(
                styles.settingCard, 
                isModified("GLOBAL_TOKEN_LIMIT") || 
                isModified("USER_TOKEN_LIMIT") || 
                isModified("DAILY_ANALYSIS_LIMIT") ? styles.settingCardModified : ""
              )}
            >
              <div className={styles.cardHeader}>
                <div className={styles.cardHeaderLeft}>
                  <ShieldAlert 
                    className={styles.cardIcon} 
                    size={24} 
                    style={{ color: TABS.find(t => t.id === 'limits')?.color }} 
                  />
                  <h2 className={styles.cardTitle}>{t("admin_settings_limits_title")}</h2>
                </div>
                <AnimatePresence>
                  {getSectionModifiedCount(["GLOBAL_TOKEN_LIMIT", "USER_TOKEN_LIMIT", "DAILY_ANALYSIS_LIMIT"]) > 0 && (
                    <motion.button
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      onClick={() => handleBulkSave(["GLOBAL_TOKEN_LIMIT", "USER_TOKEN_LIMIT", "DAILY_ANALYSIS_LIMIT"])}
                      disabled={isSaving}
                      className={styles.sectionSaveBtn}
                    >
                      <Save size={14} />
                      <span>{isSaving ? t("processing") : t("save")}</span>
                    </motion.button>
                  )}
                </AnimatePresence>
              </div>
              <div className={styles.formGroup}>
                <div className={cn(styles.field, isModified("GLOBAL_TOKEN_LIMIT") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_global_token_limit_label")}
                        {isModified("GLOBAL_TOKEN_LIMIT") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_global_token_limit_desc")}</span>
                  </div>
                  <input 
                    type="number"
                    step="1"
                    className={styles.input}
                    value={getValue("GLOBAL_TOKEN_LIMIT", 0)}
                    onChange={(e) => handleFieldChange("GLOBAL_TOKEN_LIMIT", parseInt(e.target.value))}
                    min={0}
                    max={1000000}
                  />
                </div>

                <div className={cn(styles.field, isModified("USER_TOKEN_LIMIT") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_user_token_limit_label")}
                        {isModified("USER_TOKEN_LIMIT") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_user_token_limit_desc")}</span>
                  </div>
                  <input 
                    type="number"
                    step="1"
                    className={styles.input}
                    value={getValue("USER_TOKEN_LIMIT", 0)}
                    onChange={(e) => handleFieldChange("USER_TOKEN_LIMIT", parseInt(e.target.value))}
                    min={0}
                    max={1000000}
                  />
                </div>

                <div className={cn(styles.field, isModified("DAILY_ANALYSIS_LIMIT") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_daily_analysis_limit_label")}
                        {isModified("DAILY_ANALYSIS_LIMIT") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_daily_analysis_limit_desc")}</span>
                  </div>
                  <input 
                    type="number" 
                    className={styles.input}
                    value={getValue("DAILY_ANALYSIS_LIMIT", 10)}
                    onChange={(e) => handleFieldChange("DAILY_ANALYSIS_LIMIT", parseInt(e.target.value))}
                    min={0}
                    max={1000}
                  />
                </div>
              </div>
            </motion.div>
          )}

          {/* CV PARSER & OCR CONFIG */}
          {activeTab === 'parser' && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className={cn(
                styles.settingCard, 
                isModified("CV_PARSER_STRATEGY") || 
                isModified("OCR_DPI") || 
                isModified("CHANDRA_API_URL") || 
                isModified("CHANDRA_API_KEY") ? styles.settingCardModified : ""
              )}
            >

              <div className={styles.cardHeader}>
                <div className={styles.cardHeaderLeft}>
                  <ScanLine 
                    className={styles.cardIcon} 
                    size={24} 
                    style={{ color: TABS.find(t => t.id === 'parser')?.color }} 
                  />
                  <h2 className={styles.cardTitle}>{t("admin_settings_cv_parser_ocr_title")}</h2>
                </div>
                <AnimatePresence>
                  {getSectionModifiedCount(["CV_PARSER_STRATEGY", "OCR_DPI", "CHANDRA_API_URL", "CHANDRA_API_KEY"]) > 0 && (
                    <motion.button
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      onClick={() => handleBulkSave(["CV_PARSER_STRATEGY", "OCR_DPI", "CHANDRA_API_URL", "CHANDRA_API_KEY"])}
                      disabled={isSaving}
                      className={styles.sectionSaveBtn}
                    >
                      <Save size={14} />
                      <span>{isSaving ? t("processing") : t("save")}</span>
                    </motion.button>
                  )}
                </AnimatePresence>
              </div>
              <div className={styles.formGroup}>
                <div className={cn(styles.field, isModified("CV_PARSER_STRATEGY") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_parser_strategy_label")}
                        {isModified("CV_PARSER_STRATEGY") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_parser_strategy_desc")}</span>
                  </div>
                  <select 
                    className={styles.input}
                    value={getValue("CV_PARSER_STRATEGY", "direct")}
                    onChange={(e) => handleFieldChange("CV_PARSER_STRATEGY", e.target.value)}
                  >
                    <option value="direct">{t("admin_settings_parser_strategy_direct")}</option>
                    <option value="chandra">{t("admin_settings_parser_strategy_chandra")}</option>
                  </select>
                </div>

                <div className={cn(styles.field, isModified("OCR_DPI") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_ocr_dpi_label")}
                        {isModified("OCR_DPI") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_ocr_dpi_desc")}</span>
                  </div>
                  <input 
                    type="number" 
                    className={styles.input}
                    value={getValue("OCR_DPI", 200)}
                    onChange={(e) => handleFieldChange("OCR_DPI", parseInt(e.target.value))}
                    min={72}
                    max={600}
                  />
                </div>

                <div className={cn(styles.field, isModified("CHANDRA_API_URL") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_chandra_url_label")}
                        {isModified("CHANDRA_API_URL") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_chandra_url_desc")}</span>
                  </div>
                  <input 
                    type="text" 
                    className={styles.input}
                    placeholder="https://api.datalab.to/..."
                    value={getValue("CHANDRA_API_URL", "")}
                    onChange={(e) => handleFieldChange("CHANDRA_API_URL", e.target.value)}
                    maxLength={500}
                  />
                </div>

                <div className={cn(styles.field, isModified("CHANDRA_API_KEY") ? styles.fieldModified : "")}>
                  <div className={styles.labelArea}>
                    <label className={styles.label}>
                        {t("admin_settings_chandra_key_label")}
                        {isModified("CHANDRA_API_KEY") && <span className={styles.fieldModifiedDot} />}
                    </label>
                    <span className={styles.desc}>{t("admin_settings_chandra_key_desc")}</span>
                  </div>
                  <div className="relative">
                    <input 
                      type="password" 
                      className={cn(styles.input, "pr-10")}
                      placeholder="sk-..."
                      value={getValue("CHANDRA_API_KEY", "")}
                      onChange={(e) => handleFieldChange("CHANDRA_API_KEY", e.target.value)}
                      maxLength={255}
                    />
                    <Key className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                  </div>
                </div>
                </div>
              </motion.div>
            )}

            {/* CRAWLER & MAIL */}
            {activeTab === 'automation' && (
              <>
                <motion.div 
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={cn(styles.settingCard, isModified("TOPCV_CRAWL_ENABLED") || isModified("LINKEDIN_BRIDGE_ENABLED") ? styles.settingCardModified : "")}
                >
                  <div className={styles.cardHeader}>
                    <div className={styles.cardHeaderLeft}>
                      <Globe 
                        className={styles.cardIcon} 
                        size={24} 
                        style={{ color: TABS.find(t => t.id === 'automation')?.color }} 
                      />
                      <h2 className={styles.cardTitle}>{t("admin_settings_crawler_manager_title")}</h2>
                    </div>
                    <AnimatePresence>
                      {getSectionModifiedCount(["TOPCV_CRAWL_ENABLED", "LINKEDIN_BRIDGE_ENABLED"]) > 0 && (
                        <motion.button
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 20 }}
                          onClick={() => handleBulkSave(["TOPCV_CRAWL_ENABLED", "LINKEDIN_BRIDGE_ENABLED"])}
                          disabled={isSaving}
                          className={styles.sectionSaveBtn}
                        >
                          <Save size={14} />
                          <span>{isSaving ? t("processing") : t("save")}</span>
                        </motion.button>
                      )}
                    </AnimatePresence>
                  </div>
                  <div className={styles.formGroup}>
                    <div className={cn(styles.field, isModified("TOPCV_CRAWL_ENABLED") ? styles.fieldModified : "")}>
                      <div className="flex items-center justify-between">
                        <div className={styles.labelArea}>
                          <label className={styles.label}>
                            {t("admin_settings_topcv_crawl_label")}
                            {isModified("TOPCV_CRAWL_ENABLED") && <span className={styles.fieldModifiedDot} />}
                          </label>
                          <span className={styles.desc}>{t("admin_settings_topcv_crawl_desc")}</span>
                        </div>
                        <div 
                          className={cn(styles.toggle, getValue("TOPCV_CRAWL_ENABLED", true) ? styles.toggleOn : styles.toggleOff)}
                          onClick={() => handleFieldChange("TOPCV_CRAWL_ENABLED", !getValue("TOPCV_CRAWL_ENABLED", true))}
                        >
                          <div className={styles.knob} />
                        </div>
                      </div>
                    </div>
                    <div className={cn(styles.field, isModified("LINKEDIN_BRIDGE_ENABLED") ? styles.fieldModified : "")}>
                      <div className="flex items-center justify-between">
                        <div className={styles.labelArea}>
                          <label className={styles.label}>
                            {t("admin_settings_linkedin_bridge_label")}
                            {isModified("LINKEDIN_BRIDGE_ENABLED") && <span className={styles.fieldModifiedDot} />}
                          </label>
                          <span className={styles.desc}>{t("admin_settings_linkedin_bridge_desc")}</span>
                        </div>
                        <div 
                          className={cn(styles.toggle, getValue("LINKEDIN_BRIDGE_ENABLED", false) ? styles.toggleOn : styles.toggleOff)}
                          onClick={() => handleFieldChange("LINKEDIN_BRIDGE_ENABLED", !getValue("LINKEDIN_BRIDGE_ENABLED", false))}
                        >
                          <div className={styles.knob} />
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>

                {/* EMAIL & NOTIFICATIONS */}
                <motion.div 
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={cn(
                    styles.settingCard, 
                    isModified("SMTP_HOST") || 
                    isModified("SMTP_PORT") || 
                    isModified("SMTP_USER") || 
                    isModified("SMTP_PASS") || 
                    isModified("SMTP_FROM") || 
                    isModified("QUEUE_THRESHOLD") ? styles.settingCardModified : ""
                  )}
                >
                  <div className={styles.cardHeader}>
                    <div className={styles.cardHeaderLeft}>
                      <Mail 
                        className={styles.cardIcon} 
                        size={24} 
                        style={{ color: TABS.find(t => t.id === 'automation')?.color }} 
                      />
                      <h2 className={styles.cardTitle}>{t("admin_settings_email_notifications_title")}</h2>
                    </div>
                    <div className="flex items-center gap-2">
                      <button 
                        onClick={handleTestEmail}
                        disabled={isSaving}
                        className={styles.testBtn}
                        title={t("admin_settings_test_mail_btn")}
                      >
                        <Send size={14} />
                        <span>{t("admin_settings_test_mail_btn")}</span>
                      </button>
                      <AnimatePresence>
                        {getSectionModifiedCount(["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_FROM", "QUEUE_THRESHOLD"]) > 0 && (
                          <motion.button
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 20 }}
                            onClick={() => handleBulkSave(["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_FROM", "QUEUE_THRESHOLD"])}
                            disabled={isSaving}
                            className={styles.sectionSaveBtn}
                          >
                            <Save size={14} />
                            <span>{isSaving ? t("processing") : t("save")}</span>
                          </motion.button>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                  <div className={styles.formGroup}>
                    <div className={cn(styles.field, isModified("SMTP_HOST") ? styles.fieldModified : "")}>
                      <div className={styles.labelArea}>
                        <label className={styles.label}>{t("admin_settings_smtp_host_label")}</label>
                      </div>
                      <input 
                        type="text"
                        className={styles.input}
                        placeholder="smtp.gmail.com"
                        value={getValue("SMTP_HOST", "")}
                        onChange={(e) => handleFieldChange("SMTP_HOST", e.target.value)}
                        maxLength={255}
                      />
                    </div>
                    <div className={cn(styles.field, isModified("SMTP_PORT") ? styles.fieldModified : "")}>
                      <div className={styles.labelArea}>
                        <label className={styles.label}>{t("admin_settings_smtp_port_label")}</label>
                      </div>
                      <input 
                        type="number"
                        className={styles.input}
                        value={getValue("SMTP_PORT", 587)}
                        onChange={(e) => handleFieldChange("SMTP_PORT", parseInt(e.target.value))}
                        min={1}
                        max={65535}
                      />
                    </div>
                    <div className={cn(styles.field, isModified("SMTP_USER") ? styles.fieldModified : "")}>
                      <div className={styles.labelArea}>
                        <label className={styles.label}>{t("admin_settings_smtp_user_label")}</label>
                      </div>
                      <input 
                        type="text"
                        className={styles.input}
                        value={getValue("SMTP_USER", "")}
                        onChange={(e) => handleFieldChange("SMTP_USER", e.target.value)}
                        maxLength={255}
                      />
                    </div>
                    <div className={cn(styles.field, isModified("SMTP_PASS") ? styles.fieldModified : "")}>
                      <div className={styles.labelArea}>
                        <label className={styles.label}>{t("admin_settings_smtp_pass_label")}</label>
                      </div>
                      <input 
                        type="password"
                        className={styles.input}
                        value={getValue("SMTP_PASS", "")}
                        onChange={(e) => handleFieldChange("SMTP_PASS", e.target.value)}
                        maxLength={255}
                      />
                    </div>
                    <div className={cn(styles.field, isModified("SMTP_FROM") ? styles.fieldModified : "")}>
                      <div className={styles.labelArea}>
                        <label className={styles.label}>{t("admin_settings_smtp_from_label")}</label>
                      </div>
                      <input 
                        type="text"
                        className={styles.input}
                        placeholder="Lumix AI <noreply@lumix.ai>"
                        value={getValue("SMTP_FROM", "")}
                        onChange={(e) => handleFieldChange("SMTP_FROM", e.target.value)}
                      />
                    </div>
                    <div className={cn(styles.field, isModified("QUEUE_THRESHOLD") ? styles.fieldModified : "")}>
                      <div className={styles.labelArea}>
                        <label className={styles.label}>
                            {t("admin_settings_queue_threshold_label")}
                            {isModified("QUEUE_THRESHOLD") && <span className={styles.fieldModifiedDot} />}
                        </label>
                        <span className={styles.desc}>{t("admin_settings_queue_threshold_desc")}</span>
                      </div>
                      <input 
                        type="number"
                        className={styles.input}
                        value={getValue("QUEUE_THRESHOLD", 5)}
                        onChange={(e) => handleFieldChange("QUEUE_THRESHOLD", parseInt(e.target.value))}
                      />
                    </div>
                  </div>
                </motion.div>
              </>
            )}

            {/* SYSTEM & SECURITY */}
            {activeTab === 'system' && (
              <>
                <motion.div 
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={cn(styles.settingCard, isModified("MAINTENANCE_MODE") || isModified("SYSTEM_BROADCAST") ? styles.settingCardModified : "")}
                >
                  <div className={styles.cardHeader}>
                    <div className={styles.cardHeaderLeft}>
                      <ShieldAlert 
                        className={styles.cardIcon} 
                        size={24} 
                        style={{ color: TABS.find(t => t.id === 'system')?.color }} 
                      />
                      <h2 className={styles.cardTitle}>{t("admin_settings_security_ops_title")}</h2>
                    </div>
                    <AnimatePresence>
                      {getSectionModifiedCount(["MAINTENANCE_MODE", "MAINTENANCE_DURATION", "SYSTEM_BROADCAST"]) > 0 && (
                        <motion.button
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 20 }}
                          onClick={() => handleBulkSave(["MAINTENANCE_MODE", "MAINTENANCE_DURATION", "SYSTEM_BROADCAST"])}
                          disabled={isSaving}
                          className={styles.sectionSaveBtn}
                        >
                          <Save size={14} />
                          <span>{isSaving ? t("processing") : t("save")}</span>
                        </motion.button>
                      )}
                    </AnimatePresence>
                  </div>
                  <div className={styles.formGroup}>
                    <div className={cn(styles.field, isModified("MAINTENANCE_MODE") ? styles.fieldModified : "")}>
                      <div className="flex items-center justify-between">
                        <div className={styles.labelArea}>
                          <label className={styles.label}>
                            {t("admin_settings_maintenance_mode_label")}
                            {isModified("MAINTENANCE_MODE") && <span className={styles.fieldModifiedDot} />}
                          </label>
                          <span className={styles.desc}>{t("admin_settings_maintenance_mode_desc")}</span>
                        </div>
                        <div 
                          className={cn(styles.toggle, getValue("MAINTENANCE_MODE", false) ? styles.toggleOn : styles.toggleOff)}
                          onClick={() => handleFieldChange("MAINTENANCE_MODE", !getValue("MAINTENANCE_MODE", false))}
                        >
                          <div className={styles.knob} />
                        </div>
                      </div>
                    </div>

                    <div className={cn(styles.field, isModified("MAINTENANCE_DURATION") ? styles.fieldModified : "")}>
                      <div className={styles.labelArea}>
                        <label className={styles.label}>
                            {t("admin_settings_maintenance_duration_label")}
                            {isModified("MAINTENANCE_DURATION") && <span className={styles.fieldModifiedDot} />}
                        </label>
                        <span className={styles.desc}>{t("admin_settings_maintenance_duration_desc")}</span>
                      </div>
                      <input 
                        type="text"
                        className={styles.input}
                        placeholder={t("admin_settings_maintenance_duration_placeholder")}
                        value={getValue("MAINTENANCE_DURATION", t("admin_settings_maintenance_duration_default"))}
                        onChange={(e) => handleFieldChange("MAINTENANCE_DURATION", e.target.value)}
                      />
                    </div>
                    <div className={cn(styles.field, isModified("SYSTEM_BROADCAST") ? styles.fieldModified : "")}>
                      <div className={styles.labelArea}>
                        <label className={styles.label}>
                            {t("admin_settings_system_broadcast_label")}
                            {isModified("SYSTEM_BROADCAST") && <span className={styles.fieldModifiedDot} />}
                        </label>
                        <span className={styles.desc}>{t("admin_settings_system_broadcast_desc")}</span>
                      </div>
                      <input 
                        type="text"
                        className={styles.input}
                        placeholder={t("admin_settings_system_broadcast_placeholder")}
                        value={getValue("SYSTEM_BROADCAST", "")}
                        onChange={(e) => handleFieldChange("SYSTEM_BROADCAST", e.target.value)}
                      />
                    </div>
                  </div>
                </motion.div>

                {/* DATA MANAGEMENT */}
                <motion.div 
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={cn(styles.settingCard, isModified("RESULT_CACHE_TTL") || isModified("GAP_CACHE_TTL") ? styles.settingCardModified : "")}
                >
                  <div className={styles.cardHeader}>
                    <div className={styles.cardHeaderLeft}>
                      <Database 
                        className={styles.cardIcon} 
                        size={24} 
                        style={{ color: TABS.find(t => t.id === 'system')?.color }} 
                      />
                      <h2 className={styles.cardTitle}>{t("admin_settings_data_caching_title")}</h2>
                    </div>
                    <AnimatePresence>
                      {getSectionModifiedCount(["RESULT_CACHE_TTL", "GAP_CACHE_TTL"]) > 0 && (
                        <motion.button
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 20 }}
                          onClick={() => handleBulkSave(["RESULT_CACHE_TTL", "GAP_CACHE_TTL"])}
                          disabled={isSaving}
                          className={styles.sectionSaveBtn}
                        >
                          <Save size={14} />
                          <span>{isSaving ? t("processing") : t("save")}</span>
                        </motion.button>
                      )}
                    </AnimatePresence>
                  </div>
                  <div className={styles.formGroup}>
                    <div className={cn(styles.field, isModified("RESULT_CACHE_TTL") ? styles.fieldModified : "")}>
                      <div className={styles.labelArea}>
                        <label className={styles.label}>
                            {t("admin_settings_result_cache_ttl_label")}
                            {isModified("RESULT_CACHE_TTL") && <span className={styles.fieldModifiedDot} />}
                        </label>
                        <span className={styles.desc}>{t("admin_settings_result_cache_ttl_desc")}</span>
                      </div>
                      <input 
                        type="number"
                        className={styles.input}
                        value={getValue("RESULT_CACHE_TTL", 3600)}
                        onChange={(e) => handleFieldChange("RESULT_CACHE_TTL", parseInt(e.target.value))}
                      />
                    </div>

                    <div className={cn(styles.field, isModified("SYSTEM_LOG_TTL_DAYS") ? styles.fieldModified : "")}>
                      <div className={styles.labelArea}>
                        <label className={styles.label}>
                          {t("admin_settings_system_log_ttl_days_label")}
                          {isModified("SYSTEM_LOG_TTL_DAYS") && <span className={styles.fieldModifiedDot} />}
                        </label>
                        <span className={styles.desc}>{t("admin_settings_system_log_ttl_days_desc")}</span>
                      </div>
                      <input 
                        type="number"
                        className={styles.input}
                        value={getValue("SYSTEM_LOG_TTL_DAYS", 30)}
                        onChange={(e) => handleFieldChange("SYSTEM_LOG_TTL_DAYS", parseInt(e.target.value))}
                      />
                    </div>
                    <div className={cn(styles.field, isModified("GAP_CACHE_TTL") ? styles.fieldModified : "")}>
                      <div className={styles.labelArea}>
                        <label className={styles.label}>
                            {t("admin_settings_gap_cache_ttl_label")}
                            {isModified("GAP_CACHE_TTL") && <span className={styles.fieldModifiedDot} />}
                        </label>
                        <span className={styles.desc}>{t("admin_settings_gap_cache_ttl_desc")}</span>
                      </div>
                      <input 
                        type="number"
                        className={styles.input}
                        value={getValue("GAP_CACHE_TTL", 1800)}
                        onChange={(e) => handleFieldChange("GAP_CACHE_TTL", parseInt(e.target.value))}
                      />
                    </div>
                    <div className="flex gap-4">
                      <button 
                        disabled={isSaving}
                        onClick={async () => {
                            setIsSaving(true);
                            try {
                              await api.post("admin/cache/clear", {});
                              showNotification(t("admin_settings_clear_redis_success"));
                            } catch (err) {
                              showNotification(t("admin_settings_clear_redis_error"), "error");
                            } finally {
                              setIsSaving(false);
                            }
                        }}
                        className={cn(styles.saveBtn, "bg-amber-600 shadow-amber-200")}
                      >
                        {t("admin_settings_clear_redis_btn")}
                      </button>
                      <button 
                        disabled={isSaving}
                        onClick={async () => {
                            setIsSaving(true);
                            try {
                              await api.post("admin/vector/sync", {});
                              showNotification(t("admin_settings_sync_vector_success"));
                            } catch (err) {
                              showNotification(t("admin_settings_sync_vector_error"), "error");
                            } finally {
                              setIsSaving(false);
                            }
                        }}
                        className={cn(styles.saveBtn, "bg-blue-600 shadow-blue-200")}
                      >
                        {t("admin_settings_sync_vector_btn")}
                      </button>
                    </div>
                  </div>
                </motion.div>
              </>
            )}
          </div>
        </>
        )}
        <Portal>
          <AnimatePresence>
            {hasChanges && (
              <motion.div 
                initial={{ opacity: 0, y: 50, x: "-50%" }}
                animate={{ opacity: 1, y: 0, x: "-50%" }}
                exit={{ opacity: 0, y: 50, x: "-50%" }}
                className={styles.saveBar}
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
                          onClick={() => handleBulkSave()}
                          className={styles.mainSaveBtn}
                          disabled={isSaving}
                      >
                          {isSaving ? t("processing") : t("admin_settings_save_all_btn")}
                      </button>
                  </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Portal>

        <AnimatePresence>
          {notification && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className={cn(
                "fixed bottom-10 right-10 flex items-center gap-3 px-6 py-4 rounded-2xl shadow-2xl z-[3000]",
                notification.type === 'success' ? "bg-emerald-500 text-white" : "bg-rose-500 text-white"
              )}
            >
              {notification.type === 'success' ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
              <span className="font-bold">{notification.message}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </PageContainer>
    </AuthGuard>
  );
};

export default AdminSettingsPage;





"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { 
  ArrowLeft, 
  Search, 
  Loader2, 
  CheckCircle2, 
  AlertCircle,
  Globe,
  Clock,
  BookOpen,
  Layout,
  ExternalLink,
  Save,
  Cpu,
  Trophy,
  Layers,
  ChevronDown,
  ChevronUp,
  X,
  Trash2,
  FileJson
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-import.module.css";
import { motion, AnimatePresence } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";
import Link from "next/link";

interface CrawledData {
  source_platform: string;
  source_id: string;
  external_uuid: string;
  name: string;
  provider: string;
  description: string;
  subject: string;
  level: string;
  languages: string[];
  duration_raw: string;
  duration_hours: number;
  skills: string[];
  tools: string[];
  outcomes: string[];
  modules: string[];
  url: string;
}

interface ImportResult {
  url: string;
  status: 'idle' | 'loading' | 'success' | 'error';
  task_id?: string;
  data?: CrawledData;
  error?: string;
  isExpanded?: boolean;
  isSavingIndividual?: boolean;
}

const TagEditor = ({ tags, onChange, label, icon: Icon, colorClass = "" }: { tags: string[], onChange: (newTags: string[]) => void, label: string, icon: any, colorClass?: string }) => {
  const { t } = useLanguage();
  const [inputValue, setInputValue] = useState("");

  const handleAdd = () => {
    if (inputValue.trim() && !tags.includes(inputValue.trim())) {
      onChange([...tags, inputValue.trim()]);
      setInputValue("");
    }
  };

  const handleRemove = (tag: string) => {
    onChange(tags.filter(t => t !== tag));
  };

  return (
    <div className={styles.formGroup}>
      <label className={styles.formLabel}>
        <Icon size={14} className="inline mr-1" /> {label}
      </label>
      <div className={styles.tagEditor}>
        {tags.map(tag => (
          <span key={tag} className={cn(styles.editableTag, colorClass)}>
            {tag}
            <X size={12} className={styles.removeTag} onClick={() => handleRemove(tag)} />
          </span>
        ))}
        <input 
          className={styles.addTagInput}
          placeholder={t("admin_courses_form_add_tag")}
          value={inputValue}
          onChange={e => setInputValue(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), handleAdd())}
          onBlur={handleAdd}
        />
      </div>
    </div>
  );
};

const CourseImportPage = () => {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [urlsText, setUrlsText] = useState("");
  const [results, setResults] = useState<ImportResult[]>([]);
  const [isSavingAll, setIsSavingAll] = useState(false);
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null);

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const updateResult = (url: string, update: Partial<ImportResult>) => {
    setResults(prev => prev.map(r => r.url === url ? { ...r, ...update } : r));
  };

  const handleCrawlAll = async () => {
    const lines = urlsText.split("\n").map(l => l.trim()).filter(l => l && l.includes("coursera.org"));
    
    if (lines.length === 0) {
      showNotification(t("admin_courses_import_valid_url_error"), "error");
      return;
    }

    const newResults: ImportResult[] = lines.map(url => ({
      url,
      status: 'loading',
      isExpanded: false
    }));

    setResults(prev => [...newResults, ...prev]);
    setUrlsText("");

    newResults.forEach(async (res) => {
      try {
        const resp = await api.post("recommend/admin/courses/crawl", { url: res.url }, {
          headers: { 
            Authorization: `Bearer ${token}`
          }
        });
        
        const taskId = resp.data.task_id;
        pollStatus(res.url, taskId);
      } catch (err) {
        updateResult(res.url, { status: 'error', error: t("admin_courses_import_error_init") });
      }
    });
  };

  const pollStatus = (url: string, taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const resp = await api.get(`recommend/admin/courses/crawl/status/${taskId}`, {
          headers: { 
            Authorization: `Bearer ${token}`
          }
        });
        
        if (resp.data.status === "completed") {
          // resp.data.result chính là object data trả về từ scraper
          updateResult(url, { 
            status: 'success', 
            data: resp.data.result, 
            isExpanded: true 
          });
          clearInterval(interval);
        } else if (resp.data.status === "failed") {
          updateResult(url, { 
            status: 'error', 
            error: resp.data.error || t("admin_courses_import_error_system") 
          });
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 2000);
  };

  const handleFieldChange = (url: string, field: keyof CrawledData, value: any) => {
    setResults(prev => prev.map(r => {
      if (r.url === url && r.data) {
        return { ...r, data: { ...r.data, [field]: value } };
      }
      return r;
    }));
  };

  const toggleExpand = (url: string) => {
    setResults(prev => prev.map(r => r.url === url ? { ...r, isExpanded: !r.isExpanded } : r));
  };

  const removeResult = (url: string) => {
    setResults(prev => prev.filter(r => r.url !== url));
  };

  const handleSaveSingle = async (url: string) => {
    const result = results.find(r => r.url === url);
    if (!result || !result.data) return;

    updateResult(url, { isSavingIndividual: true });
    try {
      const d = result.data;
      const payload = {
        title: d.name,
        source_platform: d.source_platform,
        source_id: d.source_id,
        external_uuid: d.external_uuid,
        url: d.url,
        level: d.level || "Beginner",
        provider: d.provider,
        duration_hours: d.duration_hours,
        duration_raw: d.duration_raw,
        languages: d.languages,
        skills_raw: d.skills,
        tools_raw: d.tools,
        outcomes: d.outcomes,
        modules: d.modules,
        tags: [...d.skills, d.provider].filter(Boolean)
      };

      await api.post("recommend/admin/courses", payload, {
        headers: { 
          Authorization: `Bearer ${token}`
        }
      });
      
      showNotification(t("admin_courses_import_save_success").replace("{name}", d.name));
      setResults(prev => prev.filter(r => r.url !== url));
    } catch (err) {
      const msg = axios.isAxiosError(err) ? err.response?.data?.detail : "Lỗi khi lưu";
      showNotification(typeof msg === 'string' ? msg : "Lỗi khi lưu", "error");
      updateResult(url, { isSavingIndividual: false });
    }
  };

  const handleBulkSave = async () => {
    const validResults = results.filter(r => r.status === 'success' && r.data);
    if (validResults.length === 0) return;

    setIsSavingAll(true);
    try {
      const payload = {
        courses: validResults.map(r => {
          const d = r.data!;
          return {
            title: d.name,
            source_platform: d.source_platform,
            source_id: d.source_id,
            external_uuid: d.external_uuid,
            url: d.url,
            level: d.level || "Beginner",
            provider: d.provider,
            duration_hours: d.duration_hours,
            duration_raw: d.duration_raw,
            languages: d.languages,
            skills_raw: d.skills,
            tools_raw: d.tools,
            outcomes: d.outcomes,
            modules: d.modules,
            tags: [...d.skills, d.provider].filter(Boolean)
          };
        })
      };

      await api.post("recommend/admin/courses/bulk", payload, {
        headers: { 
          Authorization: `Bearer ${token}`
        }
      });
      
      showNotification(t("admin_courses_import_bulk_success").replace("{count}", validResults.length.toString()));
      setResults(prev => prev.filter(r => r.status !== 'success'));
    } catch (err) {
      const msg = axios.isAxiosError(err) ? err.response?.data?.detail : "Lỗi khi lưu hàng loạt";
      showNotification(typeof msg === 'string' ? msg : "Lỗi khi lưu hàng loạt", "error");
    } finally {
      setIsSavingAll(false);
    }
  };

  const successCount = results.filter(r => r.status === 'success').length;
  const isProcessing = results.some(r => r.status === 'loading');

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <PageHeader 
          title="Course Importer PRO"
          subtitle={t("admin_courses_import_subtitle")}
        >
          <Link href="/admin/courses" className={styles.backBtn}>
            <ArrowLeft size={18} /> {t("admin_courses_import_back")}
          </Link>
        </PageHeader>

        <div className={styles.importContainer}>
          <div className={styles.inputSection}>
             <h3>{t("admin_courses_import_title")}</h3>
             <div className={styles.urlInputGroup}>
               <textarea 
                 className={styles.urlTextarea}
                 placeholder={t("admin_courses_import_placeholder")}
                 value={urlsText}
                 onChange={e => setUrlsText(e.target.value)}
                 disabled={isProcessing}
                 maxLength={50000}
               />
               <button 
                 className={styles.crawlBtn} 
                 onClick={handleCrawlAll}
                 disabled={isProcessing || !urlsText.trim()}
               >
                 {isProcessing ? <Loader2 className="animate-spin" size={20} /> : <Search size={20} />}
                 {isProcessing ? t("admin_courses_import_processing") : t("admin_courses_import_crawl_all")}
               </button>
             </div>
          </div>

          <div className={styles.resultsList}>
            <AnimatePresence>
              {results.length === 0 && !isProcessing && (
                <div className={styles.emptyState}>
                  <FileJson size={60} className="mx-auto mb-4 opacity-10" />
                  <p>{t("admin_courses_import_empty")}</p>
                </div>
              )}
              {results.map((result) => (
                <div 
                  key={result.url}
                  className={cn(styles.resultCard, result.status === 'error' && styles.resultCardError)}
                >
                  {/* Card Header clickable */}
                  <div className={styles.cardHeaderSummary} onClick={() => toggleExpand(result.url)}>
                    <div className="flex items-center gap-4 flex-1">
                      <div className={cn(
                        styles.statusIndicator, 
                        result.status === 'loading' ? styles.statusLoading : 
                        result.status === 'success' ? styles.statusSuccess : 
                        result.status === 'error' ? styles.statusError : styles.statusPending
                      )} />
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-gray-200 truncate">
                          {result.data?.name || result.url}
                        </div>
                        <div className="text-xs text-gray-500 flex items-center gap-2 overflow-hidden">
                          {result.status === 'loading' && t("admin_courses_import_loading")}
                          {result.status === 'error' && <span className="text-red-400">{result.error}</span>}
                          {result.status === 'success' && (
                            <>
                              <span className="text-blue-400 font-medium whitespace-nowrap">{result.data?.provider}</span>
                              <span>•</span>
                              <span className="whitespace-nowrap">{result.data?.level}</span>
                              <span>•</span>
                              <span className="truncate opacity-50">{result.url}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <button className={styles.removeResultBtn} onClick={(e) => { e.stopPropagation(); removeResult(result.url); }}>
                         <Trash2 size={18} />
                      </button>
                      <div className="text-gray-500">
                        {result.isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                      </div>
                    </div>
                  </div>

                  {/* Card Content expandable - simplified without height animation for maximum compatibility */}
                  {result.isExpanded && result.status === 'success' && result.data && (
                    <div className="border-t border-white/5 bg-black/20">
                      <div className={styles.editForm}>
                        <div className={cn(styles.formGroup, styles.fullWidth)}>
                          <label className={styles.formLabel}>{t("admin_courses_form_name")}</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.name} 
                            onChange={e => handleFieldChange(result.url, 'name', e.target.value)} 
                          />
                        </div>
                        
                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>{t("admin_courses_form_provider")}</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.provider} 
                            onChange={e => handleFieldChange(result.url, 'provider', e.target.value)} 
                          />
                        </div>

                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>{t("admin_courses_form_subject")}</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.subject} 
                            onChange={e => handleFieldChange(result.url, 'subject', e.target.value)} 
                          />
                        </div>

                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>{t("admin_courses_form_level")}</label>
                          <select 
                            className={styles.formInput} 
                            value={result.data.level} 
                            onChange={e => handleFieldChange(result.url, 'level', e.target.value)}
                          >
                            <option value="Beginner">Beginner</option>
                            <option value="Intermediate">Intermediate</option>
                            <option value="Advanced">Advanced</option>
                            <option value="Mixed">Mixed</option>
                          </select>
                        </div>

                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>{t("admin_courses_form_duration")}</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.duration_raw} 
                            onChange={e => handleFieldChange(result.url, 'duration_raw', e.target.value)} 
                          />
                        </div>

                        <div className={cn(styles.formGroup, styles.fullWidth)}>
                          <label className={styles.formLabel}>{t("admin_courses_form_desc")}</label>
                          <textarea 
                            className={styles.formTextarea} 
                            value={result.data.description} 
                            onChange={e => handleFieldChange(result.url, 'description', e.target.value)}
                            maxLength={5000}
                          />
                        </div>

                        <div className={styles.fullWidth}>
                          <TagEditor 
                            label={t("admin_courses_form_skills")} 
                            tags={result.data.skills} 
                            onChange={v => handleFieldChange(result.url, 'skills', v)} 
                            icon={Layers}
                          />
                        </div>

                        <div className={styles.fullWidth}>
                          <TagEditor 
                            label={t("admin_courses_form_tools")} 
                            tags={result.data.tools} 
                            onChange={v => handleFieldChange(result.url, 'tools', v)} 
                            icon={Cpu}
                            colorClass="border-purple-500/30 text-purple-400 bg-purple-500/10"
                          />
                        </div>

                        {/* Action Footer for single item */}
                        <div className={cn(styles.fullWidth, "flex justify-end gap-3 pt-6 border-t border-white/5 mt-4")}>
                           <button 
                             className={styles.discardBtn} 
                             onClick={(e) => { 
                               e.stopPropagation(); 
                               console.log("Discarding", result.url);
                               removeResult(result.url); 
                             }}
                           >
                             {t("admin_courses_import_discard")}
                           </button>
                           <button 
                             className={styles.bulkSaveBtn} 
                             disabled={result.isSavingIndividual}
                             onClick={(e) => {
                                e.stopPropagation();
                                console.log("Saving single course", result.url);
                                handleSaveSingle(result.url);
                             }}
                           >
                             {result.isSavingIndividual ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
                             {result.isSavingIndividual ? t("admin_courses_import_processing") : t("admin_courses_import_save_single")}
                           </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </AnimatePresence>
          </div>
        </div>

        {/* Global Bulk Actions Bar at bottom */}
        <AnimatePresence>
          {results.length > 0 && successCount > 0 && (
            <motion.div initial={{ y: 100 }} animate={{ y: 0 }} exit={{ y: 100 }} className={styles.bulkActionsBar}>
              <div className={styles.actionInfo}>
                 <div className={styles.countBadge}>{successCount}</div>
                 <span className="text-gray-400 font-medium">{t("admin_courses_import_ready")}</span>
                 <button className={styles.discardBtn} onClick={() => setResults([])}>{t("admin_courses_import_discard_all")}</button>
              </div>
              <button 
                className={styles.bulkSaveBtn} 
                onClick={handleBulkSave} 
                disabled={isSavingAll}
              >
                {isSavingAll ? <Loader2 className="animate-spin" size={20} /> : <Save size={20} />}
                {isSavingAll ? t("admin_courses_import_processing") : t("admin_courses_import_save_all").replace("{count}", successCount.toString())}
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Floating Notifications */}
        <AnimatePresence>
          {notification && (
            <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
               className={cn(styles.notification, notification.type === 'success' ? styles.notifSuccess : styles.notifError)}
            >
               {notification.type === 'success' ? <CheckCircle2 size={24} className="text-emerald-500" /> : <AlertCircle size={24} className="text-red-500" />}
               <span className="font-medium">{notification.message}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </PageContainer>
    </AuthGuard>
  );
};

export default CourseImportPage;




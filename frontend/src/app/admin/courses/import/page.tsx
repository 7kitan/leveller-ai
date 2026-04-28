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
  FileJson,
  Upload,
  Download,
  FileUp
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-import.module.css";
import { motion, AnimatePresence } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";
import Link from "next/link";
import Modal from "@/components/shared/Modal";

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

interface ExportInfo {
  total_courses: number;
  recommended_parts: number;
  recommended_per_part: number;
  estimated_total_size_mb: number;
  estimated_size_per_part_mb: number;
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
  const { user } = useAuth();
  const { t } = useLanguage();
  const [urlsText, setUrlsText] = useState("");
  const [results, setResults] = useState<ImportResult[]>([]);
  const [isSavingAll, setIsSavingAll] = useState(false);
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [pendingUrls, setPendingUrls] = useState<string[]>([]);
  const [isExporting, setIsExporting] = useState(false);
  const [isImportingFull, setIsImportingFull] = useState(false);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [exportInfo, setExportInfo] = useState<ExportInfo | null>(null);
  const [numParts, setNumParts] = useState(1);
  const [exportProgress, setExportProgress] = useState<{current: number, total: number} | null>(null);

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const updateResult = (url: string, update: Partial<ImportResult>) => {
    setResults(prev => prev.map(r => r.url === url ? { ...r, ...update } : r));
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.txt')) {
      showNotification("Please upload a .txt file", "error");
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setUrlsText(content);
      showNotification(`Loaded ${file.name} successfully`);
    };
    reader.onerror = () => {
      showNotification("Failed to read file", "error");
    };
    reader.readAsText(file);
  };

  const handleFullDataUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsImportingFull(true);
    let totalImported = 0;
    let totalSkipped = 0;
    let totalErrors = 0;

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        if (!file.name.endsWith('.json')) {
          showNotification(`Skipped ${file.name} - not a JSON file`, "error");
          continue;
        }

        const content = await file.text();
        const data = JSON.parse(content);
        
        if (!data.courses || !Array.isArray(data.courses)) {
          showNotification(`Invalid format in ${file.name}. Expected {courses: [...]}`, "error");
          continue;
        }

        const resp = await api.post("recommend/admin/courses/import-full", 
          { courses: data.courses }
        );

        totalImported += resp.data.imported || 0;
        totalSkipped += resp.data.skipped || 0;
        totalErrors += resp.data.errors || 0;
      }

      showNotification(
        `Imported: ${totalImported}, Skipped: ${totalSkipped}, Errors: ${totalErrors}`
      );
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to import courses";
      showNotification(msg, "error");
    } finally {
      setIsImportingFull(false);
      e.target.value = ''; // Reset file input
    }
  };

  const handleExport = async () => {
    try {
      const resp = await api.get("recommend/admin/export-info");
      setExportInfo(resp.data);
      setNumParts(resp.data.recommended_parts || 1);
      setShowExportDialog(true);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to get export info";
      showNotification(msg, "error");
    }
  };

  const handleExportWithParts = async () => {
    if (!exportInfo) return;
    
    setIsExporting(true);
    setExportProgress({ current: 0, total: numParts });
    
    try {
      const perPart = Math.ceil(exportInfo.total_courses / numParts);
      
      for (let i = 0; i < numParts; i++) {
        const offset = i * perPart;
        const resp = await api.get("recommend/admin/export", {
          params: {
            limit: perPart,
            offset: offset,
            part: i + 1
          }
        });

        const dataStr = JSON.stringify(resp.data, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `courses_export_part${i + 1}_of_${numParts}_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        setExportProgress({ current: i + 1, total: numParts });
        
        // Small delay between downloads
        if (i < numParts - 1) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }

      showNotification(`Exported ${exportInfo.total_courses} courses in ${numParts} parts successfully`);
      setShowExportDialog(false);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to export courses";
      showNotification(msg, "error");
    } finally {
      setIsExporting(false);
      setExportProgress(null);
    }
  };

  const handleCrawlAll = async () => {
    const lines = urlsText.split("\n").map(l => l.trim()).filter(l => l && l.includes("coursera.org"));
    
    if (lines.length === 0) {
      showNotification(t("admin_courses_import_valid_url_error"), "error");
      return;
    }

    // Show confirmation dialog
    setPendingUrls(lines);
    setShowConfirmDialog(true);
  };

  const confirmCrawl = async () => {
    setShowConfirmDialog(false);
    
    const newResults: ImportResult[] = pendingUrls.map(url => ({
      url,
      status: 'loading',
      isExpanded: false
    }));

    setResults(prev => [...newResults, ...prev]);
    setUrlsText("");
    setPendingUrls([]);

    newResults.forEach(async (res) => {
      try {
        const resp = await api.post("recommend/admin/courses/crawl", { url: res.url });
        
        const taskId = resp.data.task_id;
        pollStatus(res.url, taskId);
      } catch (err) {
        updateResult(res.url, { status: 'error', error: t("admin_courses_import_error_init") });
      }
    });
  };

  const cancelCrawl = () => {
    setShowConfirmDialog(false);
    setPendingUrls([]);
  };

  const pollStatus = (url: string, taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const resp = await api.get(`recommend/admin/courses/crawl/status/${taskId}`);
        
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

      await api.post("recommend/admin/courses", payload);
      
      showNotification(t("admin_courses_import_save_success").replace("{name}", d.name));
      setResults(prev => prev.filter(r => r.url !== url));
    } catch (err) {
      const msg = axios.isAxiosError(err) ? err.response?.data?.detail : t("course_import_save_error");
      showNotification(typeof msg === 'string' ? msg : t("course_import_save_error"), "error");
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

      await api.post("recommend/admin/courses/bulk", payload);
      
      showNotification(t("admin_courses_import_bulk_success").replace("{count}", validResults.length.toString()));
      setResults(prev => prev.filter(r => r.status !== 'success'));
    } catch (err) {
      const msg = axios.isAxiosError(err) ? err.response?.data?.detail : t("course_import_bulk_error");
      showNotification(typeof msg === 'string' ? msg : t("course_import_bulk_error"), "error");
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
          {/* Action Buttons Bar */}
          <div className={styles.actionButtonsBar}>
            <div className={styles.actionGroup}>
              <label className={styles.uploadBtn}>
                <Upload size={18} />
                Upload .txt URLs
                <input 
                  type="file" 
                  accept=".txt" 
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
              </label>
              
              <label className={cn(styles.uploadBtn, styles.uploadBtnSecondary)}>
                <FileUp size={18} />
                {isImportingFull ? <Loader2 className="animate-spin" size={18} /> : "Import Full Data"}
                <input 
                  type="file" 
                  accept=".json" 
                  onChange={handleFullDataUpload}
                  disabled={isImportingFull}
                  multiple
                  style={{ display: 'none' }}
                />
              </label>
            </div>

            <button 
              className={styles.exportBtn}
              onClick={handleExport}
              disabled={isExporting}
            >
              {isExporting ? <Loader2 className="animate-spin" size={18} /> : <Download size={18} />}
              {isExporting ? "Exporting..." : "Export All with Vectors"}
            </button>
          </div>

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

        {/* Confirmation Dialog */}
        <AnimatePresence>
          {showConfirmDialog && (
            <motion.div 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              exit={{ opacity: 0 }}
              className={styles.dialogOverlay}
              onClick={cancelCrawl}
            >
              <motion.div 
                initial={{ scale: 0.9, opacity: 0 }} 
                animate={{ scale: 1, opacity: 1 }} 
                exit={{ scale: 0.9, opacity: 0 }}
                className={styles.dialogBox}
                onClick={(e) => e.stopPropagation()}
              >
                <div className={styles.dialogHeader}>
                  <AlertCircle size={24} className="text-yellow-500" />
                  <h3>Confirm Crawl Operation</h3>
                </div>
                <div className={styles.dialogContent}>
                  <p>You are about to crawl <strong>{pendingUrls.length}</strong> URLs from Coursera.</p>
                  <p className="text-sm text-gray-400 mt-2">
                    This will fetch full course details for each URL. Estimated time: ~{Math.ceil(pendingUrls.length * 3 / 60)} minutes.
                  </p>
                  <div className={styles.dialogStats}>
                    <div className={styles.statItem}>
                      <span className="text-2xl font-bold">{pendingUrls.length}</span>
                      <span className="text-xs text-gray-500">URLs to crawl</span>
                    </div>
                    <div className={styles.statItem}>
                      <span className="text-2xl font-bold">~{Math.ceil(pendingUrls.length * 3 / 60)}m</span>
                      <span className="text-xs text-gray-500">Estimated time</span>
                    </div>
                  </div>
                </div>
                <div className={styles.dialogActions}>
                  <button className={styles.dialogBtnCancel} onClick={cancelCrawl}>
                    Cancel
                  </button>
                  <button className={styles.dialogBtnConfirm} onClick={confirmCrawl}>
                    <Search size={18} />
                    Start Crawling
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Export Dialog */}
        {exportInfo && (
          <Modal
            isOpen={showExportDialog}
            onClose={() => !isExporting && setShowExportDialog(false)}
            title="Export Courses"
            maxWidth="28rem"
            showCloseButton={!isExporting}
          >
            <div className={styles.exportModalContent}>
              <div className={styles.exportInfoBox}>
                <div className={styles.exportInfoRow}>
                  <span className={styles.exportInfoLabel}>Total courses:</span>
                  <span className={styles.exportInfoValue}>{exportInfo.total_courses.toLocaleString()}</span>
                </div>
                <div className={styles.exportInfoRow}>
                  <span className={styles.exportInfoLabel}>Estimated size:</span>
                  <span className={styles.exportInfoValue}>~{exportInfo.estimated_total_size_mb.toFixed(1)} MB</span>
                </div>
                <div className={styles.exportInfoRow}>
                  <span className={styles.exportInfoLabel}>Recommended parts:</span>
                  <span className={styles.exportInfoValueHighlight}>{exportInfo.recommended_parts}</span>
                </div>
              </div>

              <div className={styles.exportInputGroup}>
                <label className={styles.exportInputLabel}>
                  Number of parts to split:
                </label>
                <input 
                  type="number"
                  min="1"
                  max="20"
                  value={numParts}
                  onChange={(e) => setNumParts(Math.max(1, Math.min(20, parseInt(e.target.value) || 1)))}
                  disabled={isExporting}
                  className={styles.exportInput}
                />
                <p className={styles.exportInputHint}>
                  {Math.ceil(exportInfo.total_courses / numParts).toLocaleString()} courses per part
                  (~{(exportInfo.estimated_total_size_mb / numParts).toFixed(1)} MB each)
                </p>
              </div>

              {exportProgress && (
                <div className={styles.exportProgressBox}>
                  <div className={styles.exportProgressHeader}>
                    <span className={styles.exportProgressLabel}>Exporting...</span>
                    <span className={styles.exportProgressValue}>
                      {exportProgress.current} / {exportProgress.total}
                    </span>
                  </div>
                  <div className={styles.exportProgressBar}>
                    <div 
                      className={styles.exportProgressFill}
                      style={{ width: `${(exportProgress.current / exportProgress.total) * 100}%` }}
                    />
                  </div>
                </div>
              )}

              <div className={styles.exportModalActions}>
                <button
                  onClick={() => setShowExportDialog(false)}
                  disabled={isExporting}
                  className={styles.exportModalBtnCancel}
                >
                  Cancel
                </button>
                <button
                  onClick={handleExportWithParts}
                  disabled={isExporting}
                  className={styles.exportModalBtnExport}
                >
                  {isExporting ? (
                    <>
                      <Loader2 className="animate-spin" size={18} />
                      Exporting...
                    </>
                  ) : (
                    <>
                      <Download size={18} />
                      Export
                    </>
                  )}
                </button>
              </div>
            </div>
          </Modal>
        )}
      </PageContainer>
    </AuthGuard>
  );
};

export default CourseImportPage;




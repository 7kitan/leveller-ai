"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useLanguage } from "@/context/LanguageContext";
import { 
  ArrowLeft, 
  Search, 
  Loader2, 
  CheckCircle2, 
  AlertCircle,
  Globe,
  MapPin,
  DollarSign,
  Briefcase,
  Layers,
  ChevronDown,
  ChevronUp,
  X,
  Trash2,
  FileJson,
  Save,
  Clock,
  Upload,
  Download,
  FileUp
} from "lucide-react";
import { cn, formatNumber } from "@/lib/utils";
import styles from "./admin-import.module.css";
import { motion, AnimatePresence } from "framer-motion";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";
import Link from "next/link";
import Modal from "@/components/shared/Modal";

interface CrawledJobData {
  source_id: string;
  title_raw: string;
  company_name: string;
  source_url: string;
  source_label: string;
  raw_text: string;
  
  // Structured fields from parsing
  job_description?: string;
  requirements?: string;
  benefits?: string;
  
  // Salary & location
  min_salary_vnd: number;
  max_salary_vnd: number;
  location_raw: string;
  location_normalized?: string;
  location_district?: string;
  employment_type?: string;
  
  status: string;
}

interface ImportResult {
  url: string;
  status: 'idle' | 'loading' | 'success' | 'error';
  data?: CrawledJobData;
  error?: string;
  isExpanded?: boolean;
  isSavingIndividual?: boolean;
}

interface ExportInfo {
  total_jobs: number;
  recommended_parts: number;
  recommended_per_part: number;
  estimated_total_size_mb: number;
  estimated_size_per_part_mb: number;
}

const JobImportPage = () => {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [urlsText, setUrlsText] = useState("");
  const [results, setResults] = useState<ImportResult[]>([]);
  const [isSavingAll, setIsSavingAll] = useState(false);
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [isImportingFull, setIsImportingFull] = useState(false);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [exportInfo, setExportInfo] = useState<ExportInfo | null>(null);
  const [numParts, setNumParts] = useState(1);
  const [exportProgress, setExportProgress] = useState<{current: number, total: number} | null>(null);
  const [isUploadingUrls, setIsUploadingUrls] = useState(false);

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
      showNotification(t("jobs_import_txt_only"), "error");
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setUrlsText(content);
      showNotification(t("jobs_import_loaded").replace("{filename}", file.name));
    };
    reader.onerror = () => {
      showNotification(t("jobs_import_read_error"), "error");
    };
    reader.readAsText(file);
  };

  const handleUploadUrlsForCrawl = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.txt')) {
      showNotification(t("jobs_import_txt_only"), "error");
      return;
    }

    setIsUploadingUrls(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const resp = await api.post("jd/admin/crawl/upload-urls", formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      showNotification(
        `Queued ${resp.data.queued} URLs for crawling. Skipped: ${resp.data.skipped}`
      );
    } catch (err: any) {
      const msg = err.response?.data?.detail || t("jobs_import_upload_error");
      showNotification(msg, "error");
    } finally {
      setIsUploadingUrls(false);
      e.target.value = ''; // Reset file input
    }
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
          showNotification(t("jobs_import_skipped_not_json").replace("{filename}", file.name), "error");
          continue;
        }

        const content = await file.text();
        const data = JSON.parse(content);
        
        if (!data.jobs || !Array.isArray(data.jobs)) {
          showNotification(`Invalid format in ${file.name}. Expected {jobs: [...]}`, "error");
          continue;
        }

        const resp = await api.post("jd/admin/import-full", 
          { jobs: data.jobs }
        );

        totalImported += resp.data.imported || 0;
        totalSkipped += resp.data.skipped || 0;
        totalErrors += resp.data.errors || 0;
      }

      showNotification(
        `Imported: ${totalImported}, Skipped: ${totalSkipped}, Errors: ${totalErrors}`
      );
    } catch (err: any) {
      const msg = err.response?.data?.detail || t("jobs_import_failed");
      showNotification(msg, "error");
    } finally {
      setIsImportingFull(false);
      e.target.value = ''; // Reset file input
    }
  };

  const handleExport = async () => {
    try {
      const resp = await api.get("jd/admin/export-info");
      setExportInfo(resp.data);
      setNumParts(resp.data.recommended_parts || 1);
      setShowExportDialog(true);
    } catch (err: any) {
      const msg = err.response?.data?.detail || t("jobs_import_export_info_error");
      showNotification(msg, "error");
    }
  };

  const handleExportWithParts = async () => {
    if (!exportInfo) return;
    
    setIsExporting(true);
    setExportProgress({ current: 0, total: numParts });
    
    try {
      const perPart = Math.ceil(exportInfo.total_jobs / numParts);
      
      for (let i = 0; i < numParts; i++) {
        const offset = i * perPart;
        const resp = await api.get("jd/admin/export", {
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
        link.download = `jobs_export_part${i + 1}_of_${numParts}_${new Date().toISOString().split('T')[0]}.json`;
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

      showNotification(`Exported ${exportInfo.total_jobs} jobs in ${numParts} parts successfully`);
      setShowExportDialog(false);
    } catch (err: any) {
      const msg = err.response?.data?.detail || t("jobs_import_export_error");
      showNotification(msg, "error");
    } finally {
      setIsExporting(false);
      setExportProgress(null);
    }
  };

  const handleCrawlAll = async () => {
    const lines = urlsText.split("\n").map(l => l.trim()).filter(l => l && l.includes("topcv.vn"));
    
    if (lines.length === 0) {
      showNotification(t('admin_jobs_import_notif_invalid_url'), "error");
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
        const resp = await api.post("jd/admin/crawl/fetch", { url: res.url });
        
        updateResult(res.url, { 
          status: 'success', 
          data: resp.data, 
          isExpanded: true 
        });
      } catch (err) {
        const errorMsg = axios.isAxiosError(err) ? err.response?.data?.detail : t('admin_jobs_import_notif_fetch_error');
        updateResult(res.url, { status: 'error', error: typeof errorMsg === 'string' ? errorMsg : t('admin_jobs_import_notif_fetch_error') });
      }
    });
  };

  const handleFieldChange = (url: string, field: keyof CrawledJobData, value: any) => {
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
      await api.post("jd/admin/bulk", { jobs: [result.data] });
      
      showNotification(t('admin_jobs_import_notif_save_success').replace('{title}', result.data.title_raw));
      setResults(prev => prev.filter(r => r.url !== url));
    } catch (err) {
      const msg = axios.isAxiosError(err) ? err.response?.data?.detail : t('admin_jobs_import_notif_save_error');
      showNotification(typeof msg === 'string' ? msg : t('admin_jobs_import_notif_save_error'), "error");
      updateResult(url, { isSavingIndividual: false });
    }
  };

  const handleBulkSave = async () => {
    const validResults = results.filter(r => r.status === 'success' && r.data);
    if (validResults.length === 0) return;

    setIsSavingAll(true);
    try {
      await api.post("jd/admin/bulk", {
        jobs: validResults.map(r => r.data)
      });
      
      showNotification(t('admin_jobs_import_notif_bulk_success').replace('{count}', validResults.length.toString()));
      setResults(prev => prev.filter(r => r.status !== 'success'));
    } catch (err) {
      const msg = axios.isAxiosError(err) ? err.response?.data?.detail : t('admin_jobs_import_notif_bulk_error');
      showNotification(typeof msg === 'string' ? msg : t('admin_jobs_import_notif_bulk_error'), "error");
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
          title={t("jobs_import_title")}
          subtitle={t('admin_jobs_import_subtitle')}
        >
          <Link href="/admin/jobs" className={styles.backBtn}>
            <ArrowLeft size={18} /> {t('admin_jobs_import_back')}
          </Link>
        </PageHeader>

        <div className={styles.importContainer}>
          {/* Action Buttons Bar */}
          <div className={styles.actionButtonsBar}>
            <div className={styles.actionGroup}>
              <label className={styles.uploadBtn}>
                <Upload size={18} />
                {t("jobs_import_upload_txt")}
                <input 
                  type="file" 
                  accept=".txt" 
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
              </label>
              
              <label className={cn(styles.uploadBtn, styles.uploadBtnSecondary)}>
                <FileUp size={18} />
                {isUploadingUrls ? <Loader2 className="animate-spin" size={18} /> : "Upload & Auto Crawl"}
                <input 
                  type="file" 
                  accept=".txt" 
                  onChange={handleUploadUrlsForCrawl}
                  disabled={isUploadingUrls}
                  style={{ display: 'none' }}
                />
              </label>
              
              <label className={cn(styles.uploadBtn, styles.uploadBtnSecondary)}>
                <FileUp size={18} />
                {isImportingFull ? <Loader2 className="animate-spin" size={18} /> : t("jobs_import_import_full")}
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
             <h3>{t('admin_jobs_import_input_title')}</h3>
             <div className={styles.urlInputGroup}>
               <textarea 
                 className={styles.urlTextarea}
                 placeholder={t('admin_jobs_import_input_placeholder')}
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
                 {isProcessing ? t('admin_jobs_import_processing') : t('admin_jobs_import_fetch_all')}
               </button>
             </div>
          </div>

          <div className={styles.resultsList}>
            <AnimatePresence>
              {results.length === 0 && !isProcessing && (
                <div className={styles.emptyState}>
                  <FileJson size={60} className="mx-auto mb-4 opacity-10" />
                  <p>{t('admin_jobs_import_empty_state')}</p>
                </div>
              )}
              {results.map((result) => (
                <div 
                  key={result.url}
                  className={cn(styles.resultCard, result.status === 'error' && styles.resultCardError)}
                >
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
                          {result.data?.title_raw || result.url}
                        </div>
                        <div className="text-sm text-gray-500 flex items-center gap-2 overflow-hidden">
                          {result.status === 'loading' && t('admin_jobs_import_fetching_data')}
                          {result.status === 'error' && <span className="text-red-400">{result.error}</span>}
                          {result.status === 'success' && (
                            <>
                              <span className="text-emerald-400 font-medium whitespace-nowrap">{result.data?.company_name}</span>
                              <span>•</span>
                              <span className="whitespace-nowrap">{result.data?.location_raw}</span>
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

                  {result.isExpanded && result.status === 'success' && result.data && (
                    <div className="border-t border-white/5 bg-black/20">
                      <div className={styles.editForm}>
                        <div className={cn(styles.formGroup, styles.fullWidth)}>
                          <label className={styles.formLabel}>{t('admin_jobs_import_job_title')}</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.title_raw} 
                            onChange={e => handleFieldChange(result.url, 'title_raw', e.target.value)}
                            maxLength={200}
                          />
                        </div>
                        
                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>{t('admin_jobs_import_company')}</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.company_name} 
                            onChange={e => handleFieldChange(result.url, 'company_name', e.target.value)}
                            maxLength={255}
                          />
                        </div>

                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>{t('admin_jobs_import_employment_type')}</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.employment_type || ''} 
                            onChange={e => handleFieldChange(result.url, 'employment_type', e.target.value)} 
                            placeholder={t("placeholder_job_employment_type")}
                          />
                        </div>

                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>{t('admin_jobs_import_salary_min')}</label>
                          <input 
                            type="number"
                            className={styles.formInput} 
                            value={result.data.min_salary_vnd || 0} 
                            onChange={e => handleFieldChange(result.url, 'min_salary_vnd', parseInt(e.target.value) || 0)}
                            min={0}
                            max={999999999}
                          />
                        </div>

                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>{t('admin_jobs_import_salary_max')}</label>
                          <input 
                            type="number"
                            className={styles.formInput} 
                            value={result.data.max_salary_vnd || 0} 
                            onChange={e => handleFieldChange(result.url, 'max_salary_vnd', parseInt(e.target.value) || 0)}
                            min={0}
                            max={999999999}
                          />
                        </div>

                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>{t('admin_jobs_import_location_raw')}</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.location_raw} 
                            onChange={e => handleFieldChange(result.url, 'location_raw', e.target.value)} 
                          />
                        </div>

                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>{t('admin_jobs_import_city')}</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.location_normalized || ''} 
                            onChange={e => handleFieldChange(result.url, 'location_normalized', e.target.value)} 
                            placeholder={t("placeholder_job_location")}
                          />
                        </div>

                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>{t('admin_jobs_import_district')}</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.location_district || ''} 
                            onChange={e => handleFieldChange(result.url, 'location_district', e.target.value)} 
                          />
                        </div>

                        {/* Structured sections */}
                        <div className={cn(styles.formGroup, styles.fullWidth)}>
                          <label className={styles.formLabel}>
                            <span className="flex items-center gap-2">
                              <Briefcase size={16} />
                              {t('admin_jobs_import_job_desc')}
                            </span>
                          </label>
                          <textarea 
                            className={styles.formTextarea} 
                            value={result.data.job_description || ''} 
                            onChange={e => handleFieldChange(result.url, 'job_description', e.target.value)}
                            rows={6}
                            placeholder={t('admin_jobs_import_job_desc')}
                            maxLength={10000}
                          />
                        </div>

                        <div className={cn(styles.formGroup, styles.fullWidth)}>
                          <label className={styles.formLabel}>
                            <span className="flex items-center gap-2">
                              <CheckCircle2 size={16} />
                              {t('admin_jobs_import_requirements')}
                            </span>
                          </label>
                          <textarea 
                            className={styles.formTextarea} 
                            value={result.data.requirements || ''} 
                            onChange={e => handleFieldChange(result.url, 'requirements', e.target.value)}
                            rows={6}
                            placeholder={t('admin_jobs_import_requirements')}
                            maxLength={10000}
                          />
                        </div>

                        <div className={cn(styles.formGroup, styles.fullWidth)}>
                          <label className={styles.formLabel}>
                            <span className="flex items-center gap-2">
                              <DollarSign size={16} />
                              {t('admin_jobs_import_benefits')}
                            </span>
                          </label>
                          <textarea 
                            className={styles.formTextarea} 
                            value={result.data.benefits || ''} 
                            onChange={e => handleFieldChange(result.url, 'benefits', e.target.value)}
                            rows={6}
                            placeholder={t('admin_jobs_import_benefits')}
                            maxLength={5000}
                          />
                        </div>

                        <div className={cn(styles.formGroup, styles.fullWidth)}>
                          <label className={styles.formLabel}>{t('admin_jobs_import_raw_text')}</label>
                          <textarea 
                            className={styles.formTextarea} 
                            value={result.data.raw_text} 
                            onChange={e => handleFieldChange(result.url, 'raw_text', e.target.value)} 
                            rows={4}
                          />
                        </div>

                        <div className={cn(styles.fullWidth, "flex justify-end gap-3 pt-6 border-t border-white/5 mt-4")}>
                           <button className={styles.discardBtn} onClick={() => removeResult(result.url)}>{t('admin_jobs_import_remove')}</button>
                           <button 
                             className={styles.bulkSaveBtn} 
                             disabled={result.isSavingIndividual}
                             onClick={() => handleSaveSingle(result.url)}
                           >
                             {result.isSavingIndividual ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
                             {result.isSavingIndividual ? t('admin_jobs_import_saving') : t('admin_jobs_import_save_single')}
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

        {results.length > 0 && successCount > 0 && (
          <motion.div initial={{ y: 100 }} animate={{ y: 0 }} exit={{ y: 100 }} className={styles.bulkActionsBar}>
            <div className={styles.actionInfo}>
               <div className={styles.countBadge}>{successCount}</div>
               <span className="text-gray-400 font-medium">{t('admin_jobs_import_ready_count')}</span>
               <button className={styles.discardBtn} onClick={() => setResults([])}>{t('admin_jobs_import_discard_all')}</button>
            </div>
            <button 
              className={styles.bulkSaveBtn} 
              onClick={handleBulkSave} 
              disabled={isSavingAll}
            >
              {isSavingAll ? <Loader2 className="animate-spin" size={20} /> : <Save size={20} />}
              {isSavingAll ? t('admin_jobs_import_saving') : t('admin_jobs_import_save_bulk').replace('{count}', successCount.toString())}
            </button>
          </motion.div>
        )}

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

        {/* Export Dialog */}
        {exportInfo && (
          <Modal
            isOpen={showExportDialog}
            onClose={() => !isExporting && setShowExportDialog(false)}
            title="Export Jobs"
            maxWidth="28rem"
            showCloseButton={!isExporting}
          >
            <div className={styles.exportModalContent}>
              <div className={styles.exportInfoBox}>
                <div className={styles.exportInfoRow}>
                  <span className={styles.exportInfoLabel}>Total jobs:</span>
                  <span className={styles.exportInfoValue}>{exportInfo.total_jobs.toLocaleString()}</span>
                </div>
                <div className={styles.exportInfoRow}>
                  <span className={styles.exportInfoLabel}>Estimated size:</span>
                  <span className={styles.exportInfoValue}>~{formatNumber(exportInfo.estimated_total_size_mb)} MB</span>
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
                  {Math.ceil(exportInfo.total_jobs / numParts).toLocaleString()} jobs per part
                  (~{formatNumber(exportInfo.estimated_total_size_mb / numParts)} MB each)
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

export default JobImportPage;



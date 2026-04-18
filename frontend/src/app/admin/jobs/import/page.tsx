"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
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
  Clock
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-import.module.css";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";

interface CrawledJobData {
  source_id: string;
  title_raw: string;
  company_name: string;
  source_url: string;
  source_label: string;
  raw_text: string;
  min_salary_vnd: number;
  max_salary_vnd: number;
  location_raw: string;
  location_normalized: string;
  location_district: string;
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

const JobImportPage = () => {
  const { token } = useAuth();
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
    const lines = urlsText.split("\n").map(l => l.trim()).filter(l => l && l.includes("topcv.vn"));
    
    if (lines.length === 0) {
      showNotification("Vui lòng nhập ít nhất một URL TopCV hợp lệ", "error");
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
        const resp = await axios.post("/api/jd/admin/crawl/fetch", { url: res.url }, {
          headers: { 
            Authorization: `Bearer ${token}`,
            "X-Is-Admin": "true"
          }
        });
        
        updateResult(res.url, { 
          status: 'success', 
          data: resp.data, 
          isExpanded: true 
        });
      } catch (err) {
        const errorMsg = axios.isAxiosError(err) ? err.response?.data?.detail : "Lỗi cào dữ liệu";
        updateResult(res.url, { status: 'error', error: typeof errorMsg === 'string' ? errorMsg : "Lỗi cào dữ liệu" });
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
      await axios.post("/api/jd/admin/bulk", { jobs: [result.data] }, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-Is-Admin": "true"
        }
      });
      
      showNotification(`Đã lưu "${result.data.title_raw}" thành công!`);
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
      await axios.post("/api/jd/admin/bulk", {
        jobs: validResults.map(r => r.data)
      }, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-Is-Admin": "true"
        }
      });
      
      showNotification(`Đã lưu thành công ${validResults.length} tin tuyển dụng!`);
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
      <div className={styles.pageRoot}>
        <div className={styles.header}>
            <div className="flex flex-col gap-2">
              <Link href="/admin/jobs" className={styles.backBtn}>
                <ArrowLeft size={18} /> Quay lại danh sách
              </Link>
              <h1 className={styles.title}>
                <Globe size={40} className="text-emerald-500" />
                <span>Job Importer PRO</span>
              </h1>
              <p className={styles.subtitle}>Click vào từng tin để xem/sửa chi tiết trước khi lưu.</p>
            </div>
        </div>

        <div className={styles.importContainer}>
          <div className={styles.inputSection}>
             <h3>Nhập Danh Sách Link TopCV</h3>
             <div className={styles.urlInputGroup}>
               <textarea 
                 className={styles.urlTextarea}
                 placeholder="Một URL trên mỗi dòng (https://topcv.vn/viec-lam/...)"
                 value={urlsText}
                 onChange={e => setUrlsText(e.target.value)}
                 disabled={isProcessing}
               />
               <button 
                 className={styles.crawlBtn} 
                 onClick={handleCrawlAll}
                 disabled={isProcessing || !urlsText.trim()}
               >
                 {isProcessing ? <Loader2 className="animate-spin" size={20} /> : <Search size={20} />}
                 {isProcessing ? "Đang Xử Lý..." : "Fetch Info Tất Cả"}
               </button>
             </div>
          </div>

          <div className={styles.resultsList}>
            <AnimatePresence>
              {results.length === 0 && !isProcessing && (
                <div className={styles.emptyState}>
                  <FileJson size={60} className="mx-auto mb-4 opacity-10" />
                  <p>Hãy nhập URL phía trên để bắt đầu lấy dữ liệu.</p>
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
                        <div className="text-xs text-gray-500 flex items-center gap-2 overflow-hidden">
                          {result.status === 'loading' && "Đang lấy dữ liệu..."}
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
                          <label className={styles.formLabel}>Tiêu đề công việc</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.title_raw} 
                            onChange={e => handleFieldChange(result.url, 'title_raw', e.target.value)} 
                          />
                        </div>
                        
                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>Công ty</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.company_name} 
                            onChange={e => handleFieldChange(result.url, 'company_name', e.target.value)} 
                          />
                        </div>

                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>Lương Min (VND)</label>
                          <input 
                            type="number"
                            className={styles.formInput} 
                            value={result.data.min_salary_vnd} 
                            onChange={e => handleFieldChange(result.url, 'min_salary_vnd', parseInt(e.target.value))} 
                          />
                        </div>

                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>Lương Max (VND)</label>
                          <input 
                            type="number"
                            className={styles.formInput} 
                            value={result.data.max_salary_vnd} 
                            onChange={e => handleFieldChange(result.url, 'max_salary_vnd', parseInt(e.target.value))} 
                          />
                        </div>

                        <div className={cn(styles.formGroup, styles.fullWidth)}>
                          <label className={styles.formLabel}>Địa chỉ / Khu vực</label>
                          <input 
                            className={styles.formInput} 
                            value={result.data.location_raw} 
                            onChange={e => handleFieldChange(result.url, 'location_raw', e.target.value)} 
                          />
                        </div>

                        <div className={cn(styles.formGroup, styles.fullWidth)}>
                          <label className={styles.formLabel}>Mô tả công việc (Raw text)</label>
                          <textarea 
                            className={styles.formTextarea} 
                            value={result.data.raw_text} 
                            onChange={e => handleFieldChange(result.url, 'raw_text', e.target.value)} 
                          />
                        </div>

                        <div className={cn(styles.fullWidth, "flex justify-end gap-3 pt-6 border-t border-white/5 mt-4")}>
                           <button className={styles.discardBtn} onClick={() => removeResult(result.url)}>Gỡ bỏ</button>
                           <button 
                             className={styles.bulkSaveBtn} 
                             disabled={result.isSavingIndividual}
                             onClick={() => handleSaveSingle(result.url)}
                           >
                             {result.isSavingIndividual ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
                             {result.isSavingIndividual ? "Đang lưu..." : "Lưu tin này"}
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
               <span className="text-gray-400 font-medium">Tin sẵn sàng</span>
               <button className={styles.discardBtn} onClick={() => setResults([])}>Hủy tất cả</button>
            </div>
            <button 
              className={styles.bulkSaveBtn} 
              onClick={handleBulkSave} 
              disabled={isSavingAll}
            >
              {isSavingAll ? <Loader2 className="animate-spin" size={20} /> : <Save size={20} />}
              {isSavingAll ? "Đang lưu..." : `LƯU ${successCount} TIN TUYỂN DỤNG`}
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
      </div>
    </AuthGuard>
  );
};

export default JobImportPage;

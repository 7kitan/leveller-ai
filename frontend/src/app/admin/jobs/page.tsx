"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import Pagination from "@/components/shared/Pagination";
import { 
  Plus, 
  Trash2, 
  Search, 
  RefreshCcw,
  Edit2,
  Layers,
  MapPin,
  DollarSign,
  Briefcase,
  CheckCircle2,
  AlertCircle,
  Globe,
  Settings
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-jobs.module.css";
import { motion, AnimatePresence } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";

interface Job {
  id: string;
  title: string;
  company_name: string;
  location: string;
  min_salary_vnd: number | null;
  max_salary_vnd: number | null;
  status: string;
  source_label?: string;
  created_at: string;
}

interface SystemSetting {
  key: string;
  value: any;
  description?: string;
}

const AdminJobsPage = () => {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingJob, setEditingJob] = useState<Job | null>(null);
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null);
  const [crawlEnabled, setCrawlEnabled] = useState<boolean>(true);
  const [isUpdatingSetting, setIsUpdatingSetting] = useState(false);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [pageSize] = useState(10);

  const [formData, setFormData] = useState({
    title: "",
    company_name: "",
    location: "",
    description: "",
    status: "active"
  });

  const fetchJobs = async (page = 1) => {
    setIsLoading(true);
    try {
      const offset = (page - 1) * pageSize;
      const resp = await axios.get("/api/jd/admin/list", {
        params: {
          limit: pageSize,
          offset: offset,
          q: searchTerm || undefined
        },
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-Is-Admin": "true"
        }
      });
      setJobs(resp.data.items);
      setTotalPages(resp.data.pages);
      setCurrentPage(page);
    } catch (err) {
      showNotification(t("error"), "error");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const resp = await axios.get("/api/admin/settings", {
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-Is-Admin": "true"
        }
      });
      const topcvSetting = resp.data.find((s: SystemSetting) => s.key === "topcv_crawl_enabled");
      if (topcvSetting) {
        setCrawlEnabled(topcvSetting.value);
      }
    } catch (err) {
      console.error("Failed to fetch settings", err);
    }
  };

  const toggleCrawlSetting = async () => {
    setIsUpdatingSetting(true);
    try {
      const newValue = !crawlEnabled;
      await axios.patch(`/api/admin/settings/topcv_crawl_enabled`, 
        { value: newValue },
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            "X-Is-Admin": "true"
          }
        }
      );
      setCrawlEnabled(newValue);
      showNotification(newValue ? t("admin_jobs_crawl_success") : t("admin_jobs_status_inactive"));
    } catch (err) {
      showNotification(t("error"), "error");
    } finally {
      setIsUpdatingSetting(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchJobs(1);
      fetchSettings();
    }
  }, [token]);

  // Handle search resets pagination
  useEffect(() => {
    const timer = setTimeout(() => {
      if (token) fetchJobs(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleSave = async () => {
    try {
      const payload = {
        title_raw: formData.title,
        company_name: formData.company_name,
        location_raw: formData.location,
        raw_text: formData.description,
        status: formData.status
      };

      if (editingJob) {
        await axios.patch(`/api/jd/admin/${editingJob.id}`, payload, {
          headers: { 
            Authorization: `Bearer ${token}`,
            "X-Is-Admin": "true"
          }
        });
        showNotification(t("admin_jobs_save_success"));
      } else {
        await axios.post("/api/jd/admin", payload, {
          headers: { 
            Authorization: `Bearer ${token}`,
            "X-Is-Admin": "true"
          }
        });
        showNotification(t("admin_jobs_save_success"));
      }
      setIsModalOpen(false);
      fetchJobs(currentPage);
    } catch (err) {
      showNotification(t("error"), "error");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t("admin_jobs_delete_confirm"))) return;
    try {
      await axios.delete(`/api/jd/admin/${id}`, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-Is-Admin": "true"
        }
      });
      showNotification(t("admin_jobs_delete_success"));
      fetchJobs();
    } catch (err) {
      showNotification(t("error"), "error");
    }
  };

  const openCreate = () => {
    setEditingJob(null);
    setFormData({
      title: "",
      company_name: "",
      location: "",
      description: "",
      status: "active"
    });
    setIsModalOpen(true);
  };

  const openEdit = (job: Job) => {
    setEditingJob(job);
    setFormData({
      title: job.title,
      company_name: job.company_name,
      location: job.location,
      description: "", // Description is typically long, we might want to fetch it or leave blank for update
      status: job.status
    });
    setIsModalOpen(true);
  };

  const handleCrawl = async () => {
    if (!confirm(t("admin_jobs_crawl_success"))) return;
    setIsLoading(true);
    try {
      await axios.post("/api/jd/admin/crawl", {}, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-Is-Admin": "true"
        }
      });
      showNotification(t("admin_jobs_crawl_success"));
      // Refresh sau 5s để xem có tin mới chưa
      setTimeout(() => fetchJobs(1), 5000);
    } catch (err) {
      showNotification(t("admin_jobs_crawl_error"), "error");
    } finally {
      setIsLoading(false);
    }
  };


  const handleManualImport = () => {
    window.location.href = "/admin/jobs/import";
  };


  return (
    <AuthGuard requireAdmin>
      <div className={styles.pageRoot}>
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>
              <Briefcase size={40} className={styles.headerIcon} /> 
              <span>{t("admin_jobs_title")}</span>
            </h1>
            <p className={styles.subtitle}>{t("admin_jobs_subtitle")}</p>
          </div>
          <div className="flex gap-4">
            <div className={styles.settingToggle}>
               <div className={styles.toggleLabel}>{t("admin_jobs_auto_crawl")}</div>
               <button 
                 onClick={toggleCrawlSetting} 
                 disabled={isUpdatingSetting}
                 className={cn(styles.toggleBtn, crawlEnabled ? styles.toggleOn : styles.toggleOff)}
               >
                 <div className={styles.toggleKnob} />
               </button>
            </div>
            
            <button 
              onClick={openCreate}
              className={cn(styles.addBtn, "bg-indigo-600 hover:bg-indigo-700 shadow-indigo-200")}
            >
              <Plus size={18} /> 
              {t("admin_jobs_add_btn")}
            </button>
            
            <button 
              onClick={handleManualImport}
              className={cn(styles.addBtn, "bg-blue-600 hover:bg-blue-700")}
            >
              <Globe size={18} /> 
              {t("admin_jobs_import_btn")}
            </button>
            
            <button 
              onClick={handleCrawl}
              className={cn(styles.addBtn, "bg-emerald-600 hover:bg-emerald-700 shadow-emerald-200")}
            >
              <RefreshCcw size={18} className={cn(isLoading && "animate-spin")} /> 
              {t("admin_jobs_crawl_now")}
            </button>
          </div>
        </div>

        <div className={styles.contentStack}>
          <div className={styles.controlBar}>
            <div className={styles.searchContainer}>
              <Search className={styles.searchIcon} />
              <input 
                type="text" 
                placeholder={t("admin_jobs_search_placeholder")}
                className={styles.searchInput}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <button onClick={() => fetchJobs(currentPage)} className={styles.refreshBtn}>
              <RefreshCcw size={18} className={cn(isLoading && "animate-spin")} />
            </button>
          </div>

          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr className={styles.tableHeader}>
                  <th className={styles.th}>{t("admin_jobs_table_job_company")}</th>
                  <th className={styles.th}>{t("admin_jobs_table_source")}</th>
                  <th className={styles.th}>{t("admin_jobs_table_location")}</th>
                  <th className={styles.th}>{t("admin_jobs_table_salary")}</th>
                  <th className={styles.th}>{t("admin_jobs_table_status")}</th>
                  <th className={cn(styles.th, styles.thRight)}>{t("admin_jobs_table_edit")}</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} className={styles.tr}>
                    <td className={styles.td}>
                      <div className={styles.jobMainInfo}>
                         <div className={styles.jobIconBox}>
                            <Layers size={14} />
                         </div>
                         <div>
                            <div className={styles.jobTitleText}>{job.title}</div>
                            <div className={styles.companyName}>{job.company_name}</div>
                         </div>
                      </div>
                    </td>
                    <td className={styles.td}>
                       <span className={cn(
                         styles.sourceLabel,
                         job.source_label === 'topcv' ? styles.sourceTopcv : styles.sourceManual
                       )}>
                         {job.source_label || "MANUAL"}
                       </span>
                    </td>
                    <td className={styles.td}>
                       <div className={styles.metaInfo}>
                          <MapPin size={14} />
                          {job.location}
                       </div>
                    </td>
                    <td className={styles.td}>
                        <div className={styles.metaInfo}>
                          <DollarSign size={14} />
                          {job.max_salary_vnd ? `${(job.max_salary_vnd/1000000).toFixed(0)}M` : t("jobs_salary_negotiable")}
                       </div>
                    </td>
                    <td className={styles.td}>
                       <span className={cn(
                         styles.statusBadge,
                         job.status === 'active' ? styles.statusActive : styles.statusInactive
                       )}>
                         {job.status}
                       </span>
                    </td>
                    <td className={styles.td}>
                      <div className={styles.actionGroup}>
                        <button onClick={() => openEdit(job)} className={styles.actionBtn}>
                          <Edit2 size={16} />
                        </button>
                        <button onClick={() => handleDelete(job.id)} className={cn(styles.actionBtn, styles.actionBtnDelete)}>
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Pagination 
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={(page) => fetchJobs(page)}
          />
        </div>

        <AnimatePresence>
          {isModalOpen && (
            <div className={styles.modalOverlay}>
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className={styles.modalContent}
              >
                <div className={styles.modalHeader}>
                    <h3 className={styles.modalTitle}>{editingJob ? t("admin_jobs_modal_edit_title") : t("admin_jobs_modal_create_title")}</h3>
                </div>
                <div className={styles.modalBody}>
                   <div className={styles.formGrid}>
                      <div className={styles.formFieldFull}>
                         <label>{t("admin_jobs_modal_desc_label")}</label>
                         <textarea 
                           className={styles.textarea}
                           rows={6}
                           placeholder={t("admin_jobs_modal_desc_placeholder")}
                           value={formData.description}
                           onChange={e => setFormData({...formData, description: e.target.value})}
                         />
                      </div>
                      <div className={styles.formField}>
                         <label>{t("admin_jobs_modal_title_label")}</label>
                         <input 
                           value={formData.title}
                           onChange={e => setFormData({...formData, title: e.target.value})}
                         />
                      </div>
                      <div className={styles.formField}>
                         <label>{t("admin_jobs_modal_company_label")}</label>
                         <input 
                           value={formData.company_name}
                           onChange={e => setFormData({...formData, company_name: e.target.value})}
                         />
                      </div>
                      <div className={styles.formField}>
                         <label>{t("admin_jobs_modal_status_label")}</label>
                         <select 
                           value={formData.status}
                           onChange={e => setFormData({...formData, status: e.target.value})}
                         >
                            <option value="active">Active</option>
                            <option value="inactive">Inactive</option>
                         </select>
                      </div>
                   </div>
                </div>
                <div className={styles.modalFooter}>
                   <button onClick={() => setIsModalOpen(false)} className={styles.cancelBtn}>{t("cancel")}</button>
                   <button onClick={handleSave} className={styles.submitBtn}>
                     {editingJob ? t("admin_jobs_modal_edit_title") : t("admin_jobs_save_btn")}
                   </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {notification && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className={cn(
                styles.notification,
                notification.type === 'success' ? styles.notifSuccess : styles.notifError
              )}
            >
              {notification.type === 'success' ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
              <span>{notification.message}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </AuthGuard>
  );
};

export default AdminJobsPage;

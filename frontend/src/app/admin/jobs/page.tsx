"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import api from "@/lib/api";
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
import { useAlert } from "@/context/AlertContext";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";
import Portal from "@/components/shared/Portal";
import Modal from "@/components/shared/Modal";

interface Job {
  id: string;
  source_id: string;
  title: string;
  company_name: string;
  location: string;
  source_url?: string;
  source_label?: string;
  raw_text?: string;
  job_description?: string;
  requirements?: string;
  benefits?: string;
  min_salary_vnd: number | null;
  max_salary_vnd: number | null;
  required_exp_years: number | null;
  employment_type?: string;
  status: string;
  has_insurance?: boolean;
  has_13th_month?: boolean;
  remote_friendly?: boolean;
  created_at: string;
}

interface SystemSetting {
  key: string;
  value: any;
  description?: string;
}

const AdminJobsPage = () => {
  const { user } = useAuth();
  const { t } = useLanguage();
  const { confirm, showSuccess, showError } = useAlert();
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
    requirements: "",
    benefits: "",
    min_salary: 0,
    max_salary: 0,
    employment_type: "Full-time",
    required_exp: 0,
    source_url: "",
    has_insurance: false,
    has_13th_month: false,
    remote_friendly: false,
    status: "active"
  });

  const fetchJobs = async (page = 1) => {
    setIsLoading(true);
    try {
      const offset = (page - 1) * pageSize;
      const resp = await api.get("jd/admin/list", {
        params: {
          limit: pageSize,
          offset: offset,
          q: searchTerm || undefined
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
      const resp = await api.get("admin/settings");
      const topcvSetting = resp.data.find((s: SystemSetting) => s.key === "TOPCV_CRAWL_ENABLED");
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
      await api.patch(`admin/settings/TOPCV_CRAWL_ENABLED`, 
        { value: newValue }
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
    if (user) {
      fetchJobs(1);
      fetchSettings();
    }
  }, [user]);

  // Handle search resets pagination
  useEffect(() => {
    const timer = setTimeout(() => {
      if (user) fetchJobs(1);
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
        job_description: formData.description,
        requirements: formData.requirements,
        benefits: formData.benefits,
        min_salary_vnd: formData.min_salary,
        max_salary_vnd: formData.max_salary,
        employment_type: formData.employment_type,
        required_exp_years: formData.required_exp,
        source_url: formData.source_url,
        has_insurance: formData.has_insurance,
        has_13th_month: formData.has_13th_month,
        remote_friendly: formData.remote_friendly,
        status: formData.status
      };

      if (editingJob) {
        await api.patch(`jd/admin/${editingJob.id}`, payload);
        showNotification(t("admin_jobs_save_success"));
      } else {
        await api.post("jd/admin", payload);
        showNotification(t("admin_jobs_save_success"));
      }
      setIsModalOpen(false);
      fetchJobs(currentPage);
    } catch (err) {
      showNotification(t("error"), "error");
    }
  };

  const handleDelete = async (id: string) => {
    const confirmed = await confirm({
      title: t("admin_jobs_delete_confirm"),
      message: t("admin_jobs_delete_confirm"),
      confirmText: t("delete"),
      cancelText: t("cancel"),
      variant: "danger"
    });
    
    if (!confirmed) return;
    
    try {
      await api.delete(`jd/admin/${id}`);
      showSuccess(t("admin_jobs_delete_success"));
      fetchJobs();
    } catch (err) {
      showError(t("error"));
    }
  };

  const openCreate = () => {
    setEditingJob(null);
    setFormData({
      title: "",
      company_name: "",
      location: "",
      description: "",
      requirements: "",
      benefits: "",
      min_salary: 0,
      max_salary: 0,
      employment_type: "Full-time",
      required_exp: 0,
      source_url: "",
      has_insurance: false,
      has_13th_month: false,
      remote_friendly: false,
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
      description: job.job_description || "",
      requirements: job.requirements || "",
      benefits: job.benefits || "",
      min_salary: job.min_salary_vnd || 0,
      max_salary: job.max_salary_vnd || 0,
      employment_type: job.employment_type || "Full-time",
      required_exp: job.required_exp_years || 0,
      source_url: job.source_url || "",
      has_insurance: job.has_insurance || false,
      has_13th_month: job.has_13th_month || false,
      remote_friendly: job.remote_friendly || false,
      status: job.status
    });
    setIsModalOpen(true);
  };

  const handleCrawl = async () => {
    const confirmed = await confirm({
      title: t("admin_jobs_crawl_now"),
      message: t("admin_jobs_crawl_success"),
      confirmText: t("admin_jobs_crawl_now"),
      cancelText: t("cancel"),
      variant: "primary"
    });
    
    if (!confirmed) return;
    
    setIsLoading(true);
    try {
      await api.post("jd/admin/crawl");
      showSuccess(t("admin_jobs_crawl_success"));
      setTimeout(() => fetchJobs(), 3000);
    } catch (err) {
      showError(t("admin_jobs_crawl_error"));
    } finally {
      setIsLoading(false);
    }
  };


  const handleManualImport = () => {
    window.location.href = "/admin/jobs/import";
  };


  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <PageHeader 
          title={t("admin_jobs_title")}
          subtitle={t("admin_jobs_subtitle")}
        >
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
        </PageHeader>

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
                maxLength={200}
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
                         {job.source_label || t("admin_jobs_source_manual")}
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
                         {job.status === 'active' ? t("admin_jobs_status_active") : t("admin_jobs_status_inactive")}
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

        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          maxWidth="64rem"
          title={
            <h3 className={styles.modalTitle}>{editingJob ? t("admin_jobs_modal_edit_title") : t("admin_jobs_modal_create_title")}</h3>
          }
        >
          <div className={styles.modalBodyContent}>
            <div className={styles.formGrid}>
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
                  <label>{t("admin_jobs_table_location")}</label>
                  <input 
                    value={formData.location}
                    onChange={e => setFormData({...formData, location: e.target.value})}
                  />
                </div>
                <div className={styles.formField}>
                  <label>Employment Type</label>
                  <select 
                    value={formData.employment_type}
                    onChange={e => setFormData({...formData, employment_type: e.target.value})}
                  >
                      <option value="Full-time">Full-time</option>
                      <option value="Part-time">Part-time</option>
                      <option value="Contract">Contract</option>
                      <option value="Freelance">Freelance</option>
                  </select>
                </div>
                
                <div className={styles.formField}>
                  <label>Min Salary (VND)</label>
                  <input 
                    type="number"
                    value={formData.min_salary}
                    onChange={e => setFormData({...formData, min_salary: parseInt(e.target.value) || 0})}
                  />
                </div>
                <div className={styles.formField}>
                  <label>Max Salary (VND)</label>
                  <input 
                    type="number"
                    value={formData.max_salary}
                    onChange={e => setFormData({...formData, max_salary: parseInt(e.target.value) || 0})}
                  />
                </div>
                
                <div className={styles.formField}>
                  <label>Required Experience (Years)</label>
                  <input 
                    type="number"
                    step="0.5"
                    value={formData.required_exp}
                    onChange={e => setFormData({...formData, required_exp: parseFloat(e.target.value) || 0})}
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

                <div className={styles.formFieldFull}>
                  <label>Source URL</label>
                  <input 
                    value={formData.source_url}
                    onChange={e => setFormData({...formData, source_url: e.target.value})}
                  />
                </div>

                <div className={styles.formFieldFull}>
                  <label>{t("admin_jobs_modal_desc_label")}</label>
                  <textarea 
                    className={styles.textarea}
                    rows={4}
                    value={formData.description}
                    onChange={e => setFormData({...formData, description: e.target.value})}
                  />
                </div>

                <div className={styles.formFieldFull}>
                  <label>Requirements</label>
                  <textarea 
                    className={styles.textarea}
                    rows={4}
                    value={formData.requirements}
                    onChange={e => setFormData({...formData, requirements: e.target.value})}
                  />
                </div>

                <div className={styles.formFieldFull}>
                  <label>Benefits</label>
                  <textarea 
                    className={styles.textarea}
                    rows={3}
                    value={formData.benefits}
                    onChange={e => setFormData({...formData, benefits: e.target.value})}
                  />
                </div>

                <div className={styles.checkboxGroup}>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input 
                      type="checkbox"
                      checked={formData.has_insurance}
                      onChange={e => setFormData({...formData, has_insurance: e.target.checked})}
                    />
                    <span>Insurance</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input 
                      type="checkbox"
                      checked={formData.has_13th_month}
                      onChange={e => setFormData({...formData, has_13th_month: e.target.checked})}
                    />
                    <span>13th Month Salary</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input 
                      type="checkbox"
                      checked={formData.remote_friendly}
                      onChange={e => setFormData({...formData, remote_friendly: e.target.checked})}
                    />
                    <span>Remote Friendly</span>
                  </label>
                </div>
            </div>
          </div>
          <div className={styles.modalFooter}>
            <button onClick={() => setIsModalOpen(false)} className={styles.cancelBtn}>{t("cancel")}</button>
            <button onClick={handleSave} className={styles.submitBtn}>
              {editingJob ? t("admin_jobs_modal_edit_title") : t("admin_jobs_save_btn")}
            </button>
          </div>
        </Modal>

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
      </PageContainer>
    </AuthGuard>
  );
};

export default AdminJobsPage;


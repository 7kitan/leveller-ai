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
import { cn, formatSalaryVND } from "@/lib/utils";
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
  extracted_skills?: Array<{
    skill_name: string;
    category: string;
    required_level?: string;
    min_years_exp?: number;
    is_mandatory?: boolean;
    importance_weight?: number;
    // Skill group fields
    is_group?: boolean;
    group_strategy?: string;
    alternative_skills?: string[];
    min_required?: number;
  }>;
  // Classification fields
  is_tech_job?: boolean;
  job_classification_confidence?: number;
  job_primary_domain?: string;
  job_classification_reason?: string;
  classified_at?: string;
}

interface SystemSetting {
  key: string;
  value: any;
  description?: string;
}

const AdminJobsPage = () => {
  const { token } = useAuth();
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
      showNotification(newValue ? t("admin_jobs_crawl_success") : t("admin_jobs_auto_crawl_disabled"));
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
      await api.post("jd/admin/crawl", {});
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
                          {job.max_salary_vnd ? formatSalaryVND(job.max_salary_vnd) : t("jobs_salary_negotiable")}
                       </div>
                    </td>
                    <td className={styles.td}>
                       <div className="flex flex-col gap-1">
                         <span className={cn(
                           styles.statusBadge,
                           job.status === 'active' ? styles.statusActive : styles.statusInactive
                         )}>
                           {job.status === 'active' ? t("admin_jobs_status_active") : t("admin_jobs_status_inactive")}
                         </span>
                         {job.is_tech_job !== undefined && (
                           <span className={cn(
                             "text-xs px-2 py-0.5 rounded",
                             job.is_tech_job 
                               ? "bg-blue-100 text-blue-700" 
                               : "bg-orange-100 text-orange-700"
                           )}>
                             {job.is_tech_job ? "Tech" : "Non-Tech"}
                             {job.job_classification_confidence && 
                               ` (${(job.job_classification_confidence * 100).toFixed(0)}%)`
                             }
                           </span>
                         )}
                       </div>
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

            {/* Extracted Skills Section */}
            {editingJob?.extracted_skills && editingJob.extracted_skills.length > 0 && (
              <div className={styles.formFieldFull}>
                <label className="text-lg font-semibold mb-3 block">
                  Extracted Skills ({editingJob.extracted_skills.length})
                </label>
                <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {editingJob.extracted_skills.map((skill, idx) => (
                      <div 
                        key={idx}
                        className={cn(
                          "bg-white rounded-lg p-3 border-2 transition-colors",
                          skill.is_group 
                            ? "border-purple-300 bg-purple-50 hover:border-purple-400" 
                            : "border-gray-200 hover:border-indigo-300"
                        )}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <div className="font-semibold text-gray-900">
                                {skill.skill_name}
                              </div>
                              {skill.is_group && (
                                <span className="text-xs bg-purple-600 text-white px-2 py-0.5 rounded font-semibold">
                                  GROUP
                                </span>
                              )}
                            </div>
                            <div className="text-xs text-gray-500 mb-2">
                              {skill.category}
                            </div>
                            
                            {/* Alternative Skills for Groups */}
                            {skill.is_group && skill.alternative_skills && skill.alternative_skills.length > 0 && (
                              <div className="mt-2 pt-2 border-t border-purple-200">
                                <div className="text-xs text-purple-700 font-medium mb-1">
                                  Alternatives ({skill.group_strategy === 'any_one' ? 'ANY ONE' : skill.group_strategy}):
                                </div>
                                <div className="flex flex-wrap gap-1">
                                  {skill.alternative_skills.map((alt, altIdx) => (
                                    <span 
                                      key={altIdx}
                                      className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded border border-purple-300"
                                    >
                                      {alt}
                                    </span>
                                  ))}
                                </div>
                                {skill.min_required && skill.min_required > 1 && (
                                  <div className="text-xs text-purple-600 mt-1">
                                    Min required: {skill.min_required}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            {skill.is_mandatory && (
                              <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                                Required
                              </span>
                            )}
                            {skill.importance_weight && (
                              <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded">
                                Weight: {skill.importance_weight}/10
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-gray-600">
                          {skill.required_level && (
                            <span className="flex items-center gap-1">
                              <Briefcase size={12} />
                              {skill.required_level}
                            </span>
                          )}
                          {skill.min_years_exp !== undefined && skill.min_years_exp > 0 && (
                            <span className="flex items-center gap-1">
                              📅 {skill.min_years_exp}+ years
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Job Classification Section */}
            {editingJob && editingJob.is_tech_job !== undefined && (
              <div className={styles.formFieldFull}>
                <label className="text-lg font-semibold mb-3 block">
                  Job Classification
                </label>
                <div className={cn(
                  "rounded-lg p-4 border-2",
                  editingJob.is_tech_job 
                    ? "bg-blue-50 border-blue-200" 
                    : "bg-orange-50 border-orange-200"
                )}>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-sm text-gray-600 mb-1">Type</div>
                      <div className={cn(
                        "font-semibold text-lg",
                        editingJob.is_tech_job ? "text-blue-700" : "text-orange-700"
                      )}>
                        {editingJob.is_tech_job ? "Tech Job" : "Non-Tech Job"}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600 mb-1">Domain</div>
                      <div className="font-semibold text-gray-900">
                        {editingJob.job_primary_domain || "Unknown"}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600 mb-1">Confidence</div>
                      <div className="font-semibold text-gray-900">
                        {editingJob.job_classification_confidence 
                          ? `${(editingJob.job_classification_confidence * 100).toFixed(1)}%`
                          : "N/A"
                        }
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600 mb-1">Classified At</div>
                      <div className="text-sm text-gray-700">
                        {editingJob.classified_at 
                          ? new Date(editingJob.classified_at).toLocaleDateString()
                          : "N/A"
                        }
                      </div>
                    </div>
                  </div>
                  {editingJob.job_classification_reason && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <div className="text-sm text-gray-600 mb-1">Reason</div>
                      <div className="text-sm text-gray-700 italic">
                        {editingJob.job_classification_reason}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
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


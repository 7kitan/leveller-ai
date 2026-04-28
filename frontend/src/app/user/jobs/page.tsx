"use client";

import React, { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import styles from "./user-jobs.module.css";
import { motion, AnimatePresence } from "framer-motion";
import { Briefcase, MapPin, Search, Loader2, Info, Sparkles, Building2, DollarSign, Clock, Layers } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import Pagination from "@/components/shared/Pagination";
import { useLanguage } from "@/context/LanguageContext";
import api from "@/lib/api";
import { formatDistanceToNow } from 'date-fns';
import Modal from "@/components/shared/Modal";
import CustomDropdown from "@/components/shared/CustomDropdown";
import { vi, enUS } from 'date-fns/locale';
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";

interface Job {
  id: string;
  title_raw: string;
  company_name?: string;
  status: string;
  min_salary_vnd?: number;
  max_salary_vnd?: number;
  location_raw?: string;
  employment_type?: string;
  source_label?: string;
  created_at?: string;
  source_url?: string;
  job_description?: string;
  requirements?: string;
  benefits?: string;
}

function FormattedText({ text }: { text: string }) {
  if (!text) return null;
  return (
    <div className={styles.formattedContent} style={{ whiteSpace: 'pre-wrap' }}>
      {text}
    </div>
  );
}

export default function JobsPage() {
  const { t, language } = useLanguage();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [location, setLocation] = useState("");
  const [minSalary, setMinSalary] = useState("");
  const [role, setRole] = useState("");
  const { user } = useAuth();

  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [pageSize] = useState(12);

  const fetchJobs = async (page = 1) => {
    setLoading(true);
    try {
      const offset = (page - 1) * pageSize;
      const res = await api.get("jd/search", {
        params: {
          q: searchTerm || undefined,
          location: location || undefined,
          min_salary: minSalary || undefined,
          role: role || undefined,
          limit: pageSize,
          offset: offset
        }
      });
      setJobs(res.data.items);
      setTotalPages(res.data.pages);
      setCurrentPage(page);
    } catch (err) {
      console.error("Lỗi tìm kiếm jobs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs(1);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs(1);
  };

  const openJobDetails = (job: Job) => {
    setSelectedJob(job);
    setShowDetailsModal(true);
  };

  return (
    <PageContainer>
      <PageHeader 
        title={language === 'vi' ? <>KHÁM PHÁ<span className={styles.gradientText}> CƠ HỘI</span></> : <>EXPLORE<span className={styles.gradientText}> OPPORTUNITIES</span></>}
        subtitle={t("jobs_subtitle")}
      >
        <div className={styles.badge}>
          <Sparkles size={12} />
          <span className={styles.badgeLabel}>{t("opportunity_index_badge")}</span>
        </div>
      </PageHeader>
      
      <form onSubmit={handleSearch} className={styles.searchForm}>
          <div className={styles.searchContainer}>
              <div className={styles.inputWrapper}>
                  <Search size={18} className={styles.inputIcon} />
                   <input 
                       type="text"
                       placeholder={t("jobs_search_keyword")}
                       className={styles.input}
                       value={searchTerm}
                       onChange={(e) => setSearchTerm(e.target.value)}
                   />
              </div>
              <div className={styles.inputWrapper}>
                  <MapPin size={18} className={styles.inputIcon} />
                  <CustomDropdown 
                      value={location}
                      options={[
                          { value: "", label: t("jobs_location_all") },
                          { value: "HN", label: t("jobs_location_hn") },
                          { value: "HCM", label: t("jobs_location_hcm") },
                          { value: "DN", label: t("jobs_location_dn") },
                          { value: "Other", label: t("jobs_location_other") },
                      ]}
                      onChange={(val) => setLocation(val)}
                      buttonClassName={styles.input}
                  />
              </div>
              <div className={styles.inputWrapper}>
                  <Briefcase size={18} className={styles.inputIcon} />
                   <input 
                       type="text"
                       placeholder={t("jobs_search_salary")}
                       className={styles.input}
                       value={minSalary}
                       onChange={(e) => setMinSalary(e.target.value)}
                   />
              </div>
               <button 
                   type="submit"
                   className={styles.searchBtn}
               >
                   {t("jobs_search_btn")}
               </button>
          </div>
      </form>

      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={styles.loadingWrapper}
          >
             <Loader2 size={40} className={cn("animate-spin", styles.loadingIcon)} />
             <p className={styles.loadingText}>{t("jobs_loading_db")}</p>
          </motion.div>
        ) : jobs.length > 0 ? (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={styles.grid}
          >
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} onShowDetails={openJobDetails} />
            ))}
          </motion.div>
        ) : (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={styles.emptyState}
          >
             <Info size={48} className={styles.emptyIcon} />
             <h3 className={styles.emptyTitle}>{t("jobs_no_results")}</h3>
             <p className={styles.emptySub}>{t("jobs_no_results_sub")}</p>
          </motion.div>
        )}
      </AnimatePresence>

      <Pagination 
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(p) => fetchJobs(p)}
        className="mt-12"
      />

      {/* ── Job Details Modal ────────────────────────────────────────── */}
      <Modal
        isOpen={showDetailsModal}
        onClose={() => setShowDetailsModal(false)}
        title={t("job_details_title")}
        maxWidth="800px"
      >
        {selectedJob && (
          <div className={styles.modalBodyContent}>
            <div className={styles.modalSection}>
                <div className={styles.modalSectionLabel}>{selectedJob.company_name}</div>
                <h2 className={styles.modalTitle}>{selectedJob.title_raw}</h2>
            </div>

            <div className={styles.modalMetaGrid}>
                <div className={styles.modalMetaItem}>
                    <div className={styles.modalMetaIcon}><MapPin size={20} /></div>
                    <div className={styles.modalMetaText}>
                        <span className={styles.modalMetaLabel}>{t("location")}</span>
                        <span className={styles.modalMetaValue}>{selectedJob.location_raw || t("jobs_location_nationwide")}</span>
                    </div>
                </div>
                <div className={styles.modalMetaItem}>
                    <div className={styles.modalMetaIcon}><DollarSign size={20} /></div>
                    <div className={styles.modalMetaText}>
                        <span className={styles.modalMetaLabel}>{t("salary")}</span>
                        <span className={styles.modalMetaValue}>
                             {(() => {
                                const min = selectedJob.min_salary_vnd;
                                const max = selectedJob.max_salary_vnd;
                                if (!min && !max) return t("jobs_salary_negotiable");
                                const format = (val: number) => `${(val / 1000000).toFixed(0)}M`;
                                if (min && !max) return `${t("jobs_salary_from")} ${format(min)}`;
                                if (!min && max) return `${t("jobs_salary_up_to")} ${format(max)}`;
                                return `${format(min!)} - ${format(max!)}`;
                             })()}
                        </span>
                    </div>
                </div>
                <div className={styles.modalMetaItem}>
                    <div className={styles.modalMetaIcon}><Clock size={20} /></div>
                    <div className={styles.modalMetaText}>
                        <span className={styles.modalMetaLabel}>{t("posted_at")}</span>
                        <span className={styles.modalMetaValue}>
                            {selectedJob.created_at ? formatDistanceToNow(new Date(selectedJob.created_at), { 
                                locale: language === 'vi' ? vi : enUS, 
                                addSuffix: true 
                            }) : t("jobs_time_recently")}
                        </span>
                    </div>
                </div>
                <div className={styles.modalMetaItem}>
                    <div className={styles.modalMetaIcon}><Briefcase size={20} /></div>
                    <div className={styles.modalMetaText}>
                        <span className={styles.modalMetaLabel}>{t("employment_type")}</span>
                        <span className={styles.modalMetaValue}>{selectedJob.employment_type || t("jobs_employment_fulltime")}</span>
                    </div>
                </div>
            </div>

            {/* Structured Sections */}
            {selectedJob.job_description && (
              <div className={styles.modalSection}>
                <div className={styles.modalSectionLabel}>{t("job_description")}</div>
                <div className={styles.modalDescription}>
                  <FormattedText text={selectedJob.job_description} />
                </div>
              </div>
            )}

            {selectedJob.requirements && (
              <div className={styles.modalSection}>
                <div className={styles.modalSectionLabel}>{t("job_requirements")}</div>
                <div className={styles.modalDescription}>
                  <FormattedText text={selectedJob.requirements} />
                </div>
              </div>
            )}

            {selectedJob.benefits && (
              <div className={styles.modalSection}>
                <div className={styles.modalSectionLabel}>{t("job_benefits")}</div>
                <div className={styles.modalDescription}>
                  <FormattedText text={selectedJob.benefits} />
                </div>
              </div>
            )}

            {/* No structured data available */}
            {!selectedJob.job_description && !selectedJob.requirements && !selectedJob.benefits && (
              <div className={styles.modalSection}>
                <div className={styles.modalDescription} style={{ opacity: 0.6, fontStyle: 'italic' }}>
                  {t("no_description_available")}
                </div>
              </div>
            )}

            <div className={styles.modalFooterActions}>
                <button onClick={() => setShowDetailsModal(false)} className={styles.modalCloseBtn}>
                    {t("close")}
                </button>
                <Link
                    href={`/user/analysis?job_id=${selectedJob.id}`}
                    className={styles.modalAnalyzeBtn}
                    onClick={() => setShowDetailsModal(false)}
                >
                    {t("jobs_run_analysis")} <Sparkles size={16} />
                </Link>
                {selectedJob.source_url && (
                    <a 
                        href={selectedJob.source_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className={styles.modalSourceBtn}
                    >
                        {t("view_original")} <Briefcase size={16} />
                    </a>
                )}
            </div>
          </div>
        )}
      </Modal>
    </PageContainer>
  );
}

function JobCard({ job, onShowDetails }: { job: Job; onShowDetails: (j: Job) => void }) {
  const { t, language } = useLanguage();
  
  const formatSalary = (min?: number, max?: number) => {
    if (!min && !max) return t("jobs_salary_negotiable");
    const format = (val: number) => `${(val / 1000000).toFixed(0)}M`;
    if (min && !max) return `${t("jobs_salary_from")} ${format(min)}`;
    if (!min && max) return `${t("jobs_salary_up_to")} ${format(max)}`;
    return `${format(min!)} - ${format(max!)}`;
  };

  const getRelativeTime = (dateString?: string) => {
    if (!dateString) return t("jobs_time_just_now");
    try {
      return formatDistanceToNow(new Date(dateString), { 
        locale: language === 'vi' ? vi : enUS, 
        addSuffix: true 
      });
    } catch {
      return t("jobs_time_recently");
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className={styles.card}
    >
      <div className={styles.cardTop}>
        <div className={styles.iconBox}>
          {job.source_label?.toLowerCase() === 'topcv' ? <Layers size={22} /> : <Briefcase size={22} />}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <span className={cn(
              styles.statusBadge,
              job.status?.toLowerCase() === "active" ? styles.statusActive : styles.statusOther
            )}>
              {job.status || t("status_closed")}
            </span>
            {job.source_label && (
                <span className={cn(
                    styles.sourceBadge,
                    job.source_label.toLowerCase() === 'topcv' ? styles.sourceTopcv : styles.sourceManual
                )}>
                    {job.source_label}
                </span>
            )}
        </div>
      </div>
      
      <div style={{ flex: 1 }}>
          <h3 className={styles.cardTitle} title={job.title_raw}>
            {job.title_raw}
          </h3>
          <div className={styles.companyName}>
            <Building2 size={14} style={{ marginRight: '6px', opacity: 0.6 }} />
            <span className="truncate" title={job.company_name}>{job.company_name || t("jobs_company_confidential")}</span>
          </div>

          <div className={styles.metaGrid}>
            <div className={styles.cardMeta} title={job.location_raw}>
                <MapPin size={14} style={{ opacity: 0.6 }} /> 
                <span className="truncate">{job.location_raw || t("jobs_location_nationwide")}</span>
            </div>
            <div className={styles.cardMeta}>
                <DollarSign size={14} style={{ opacity: 0.6 }} /> 
                <span style={{ color: 'var(--color-success)', fontWeight: 700 }}>
                    {formatSalary(job.min_salary_vnd, job.max_salary_vnd)}
                </span>
            </div>
            <div className={styles.cardMeta}>
                <Clock size={14} style={{ opacity: 0.6 }} /> 
                <span>{getRelativeTime(job.created_at)}</span>
            </div>
            <div className={styles.cardMeta}>
                <Briefcase size={14} style={{ opacity: 0.6 }} /> 
                <span>{job.employment_type || t("jobs_employment_fulltime")}</span>
            </div>
          </div>
      </div>
      
      <div className={styles.cardFooter}>
        <button 
          onClick={() => onShowDetails(job)}
          className={styles.detailsBtn}
          title={t("view_details")}
        >
          <Info size={18} />
        </button>
        <Link
          href={`/user/analysis?job_id=${job.id}`}
          className={styles.actionBtn}
        >
          {t("jobs_run_analysis")} <Sparkles size={14} />
        </Link>
      </div>
    </motion.div>
  );
}



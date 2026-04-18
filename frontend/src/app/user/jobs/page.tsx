"use client";

import React, { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import styles from "./user-jobs.module.css";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { Briefcase, MapPin, Search, Loader2, Info, Sparkles, Building2, DollarSign, Clock, Layers } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import Pagination from "@/components/shared/Pagination";
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';

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
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [location, setLocation] = useState("");
  const [minSalary, setMinSalary] = useState("");
  const [role, setRole] = useState("");
  const { token } = useAuth();

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [pageSize] = useState(12);

  const fetchJobs = async (page = 1) => {
    setLoading(true);
    try {
      const offset = (page - 1) * pageSize;
      const res = await axios.get("/api/jd/search", {
        params: {
          q: searchTerm || undefined,
          location: location || undefined,
          min_salary: minSalary || undefined,
          role: role || undefined,
          limit: pageSize,
          offset: offset
        },
        headers: { "Authorization": `Bearer ${token}` }
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

  return (
    <div className={styles.pageRoot}>
      <div className={styles.header}>
        <div>
           <div className={styles.badge}>
              <Sparkles size={12} />
              <span className={styles.badgeLabel}>Global Opportunity Index v3.1</span>
           </div>
           <h1 className={styles.title}>
              KHÁM PHÁ<br />
              <span className={styles.gradientText}>CƠ HỘI.</span>
           </h1>
           <p className={styles.subtitle}>Tìm kiếm và phân tích độ phù hợp với các vị trí hàng đầu trên quy mô toàn cầu.</p>
        </div>
        
        <form onSubmit={handleSearch} className={styles.searchForm}>
            <div className={styles.searchContainer}>
                <div className={styles.inputWrapper}>
                    <Search size={18} className={styles.inputIcon} />
                    <input 
                        type="text"
                        placeholder="Từ khóa (Vị trí, Công ty...)"
                        className={styles.input}
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                <div className={styles.inputWrapper}>
                    <MapPin size={18} className={styles.inputIcon} />
                    <input 
                        type="text"
                        placeholder="Địa điểm"
                        className={styles.input}
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                    />
                </div>
                <div className={styles.inputWrapper}>
                    <Briefcase size={18} className={styles.inputIcon} />
                    <input 
                        type="text"
                        placeholder="Lương tối thiểu"
                        className={styles.input}
                        value={minSalary}
                        onChange={(e) => setMinSalary(e.target.value)}
                    />
                </div>
                <button 
                    type="submit"
                    className={styles.searchBtn}
                >
                    TÌM KIẾM
                </button>
            </div>
        </form>
      </div>

      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={styles.loadingWrapper}
          >
            <Loader2 size={40} className={cn("animate-spin", styles.loadingIcon)} />
            <p className={styles.loadingText}>Đang đồng bộ cơ sở dữ liệu...</p>
          </motion.div>
        ) : jobs.length > 0 ? (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={styles.grid}
          >
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </motion.div>
        ) : (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={styles.emptyState}
          >
            <Info size={48} className={styles.emptyIcon} />
            <h3 className={styles.emptyTitle}>Không tìm thấy kết quả</h3>
            <p className={styles.emptySub}>Hệ thống không tìm thấy công việc phù hợp với tiêu chí của bạn.</p>
          </motion.div>
        )}
      </AnimatePresence>

      <Pagination 
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(p) => fetchJobs(p)}
        className="mt-12"
      />
    </div>
  );
}

function JobCard({ job }: { job: Job }) {
  const formatSalary = (min?: number, max?: number) => {
    if (!min && !max) return "Thỏa thuận";
    const format = (val: number) => `${(val / 1000000).toFixed(0)}M`;
    if (min && !max) return `Từ ${format(min)}`;
    if (!min && max) return `Lên tới ${format(max)}`;
    return `${format(min!)} - ${format(max!)}`;
  };

  const getRelativeTime = (dateString?: string) => {
    if (!dateString) return "Mới đây";
    try {
      return formatDistanceToNow(new Date(dateString), { locale: vi, addSuffix: true });
    } catch {
      return "Gần đây";
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
          {job.source_label?.toLowerCase() === 'topcv' ? <Layers size={24} /> : <Briefcase size={24} />}
        </div>
        <div className="flex flex-col items-end gap-2">
            <span className={cn(
              styles.statusBadge,
              job.status?.toLowerCase() === "active" ? styles.statusActive : styles.statusOther
            )}>
              {job.status || "Closed"}
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
      
      <div>
          <h3 className={styles.cardTitle}>
            {job.title_raw}
          </h3>
          <div className={styles.companyName}>
            <Building2 size={14} className="inline mr-1 opacity-50" />
            {job.company_name || "Công ty bảo mật"}
          </div>
      </div>
      
      <div className={styles.metaGrid}>
        <div className={styles.cardMeta}>
          <MapPin size={14} className="opacity-50" /> 
          <span className="truncate">{job.location_raw || "Không xác định"}</span>
        </div>
        <div className={styles.cardMeta}>
          <DollarSign size={14} className="opacity-50" /> 
          <span>{formatSalary(job.min_salary_vnd, job.max_salary_vnd)}</span>
        </div>
        <div className={styles.cardMeta}>
          <Briefcase size={14} className="opacity-50" /> 
          <span>{job.employment_type || "Toàn thời gian"}</span>
        </div>
        <div className={styles.cardMeta}>
          <Clock size={14} className="opacity-50" /> 
          <span>{getRelativeTime(job.created_at)}</span>
        </div>
      </div>
      
      <Link
        href={`/user/analysis?job_id=${job.id}&job_title=${encodeURIComponent(job.title_raw || "")}`}
        className={styles.actionBtn}
      >
        Khởi chạy Phân tích <Sparkles size={14} className="inline ml-1" />
      </Link>
    </motion.div>
  );
}

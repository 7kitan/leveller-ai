"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
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
  AlertCircle
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-jobs.module.css";
import { motion, AnimatePresence } from "framer-motion";

interface Job {
  id: string;
  title: string;
  company_name: string;
  location: string;
  min_salary_vnd: number | null;
  max_salary_vnd: number | null;
  status: string;
  created_at: string;
}

const AdminJobsPage = () => {
  const { token } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingJob, setEditingJob] = useState<Job | null>(null);
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null);

  const [formData, setFormData] = useState({
    title: "",
    company_name: "",
    location: "",
    description: "",
    status: "active"
  });

  const fetchJobs = async () => {
    setIsLoading(true);
    try {
      const resp = await axios.get("/api/jd/admin/list", {
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-Is-Admin": "true"
        }
      });
      setJobs(resp.data);
    } catch (err) {
      showNotification("Không thể tải danh sách công việc", "error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchJobs();
  }, [token]);

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleSave = async () => {
    try {
      if (editingJob) {
        await axios.patch(`/api/jd/admin/${editingJob.id}`, formData, {
          headers: { 
            Authorization: `Bearer ${token}`,
            "X-Is-Admin": "true"
          }
        });
        showNotification("Đã cập nhật công việc");
      } else {
        // Backend doesn't have a public admin create JD endpoint yet in my last update
        // but let's assume it exists or use list endpoint to see.
        // For now, only focus on Update/Delete as I implemented in jd_service
        showNotification("Tính năng tạo mới JD đang được phát triển", "error");
      }
      setIsModalOpen(false);
      fetchJobs();
    } catch (err) {
      showNotification("Lỗi khi lưu công việc", "error");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Xóa tin tuyển dụng này?")) return;
    try {
      await axios.delete(`/api/jd/admin/${id}`, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-Is-Admin": "true"
        }
      });
      showNotification("Đã xóa tin tuyển dụng");
      fetchJobs();
    } catch (err) {
      showNotification("Lỗi khi xóa", "error");
    }
  };

  const openEdit = (job: Job) => {
    setEditingJob(job);
    setFormData({
      title: job.title,
      company_name: job.company_name,
      location: job.location,
      description: "", 
      status: job.status
    });
    setIsModalOpen(true);
  };

  const filtered = jobs.filter(j =>
    (j.title ?? "").toLowerCase().includes(searchTerm.toLowerCase()) ||
    (j.company_name ?? "").toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <AuthGuard requireAdmin>
      <div className={styles.pageRoot}>
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>
              <Briefcase size={40} className={styles.headerIcon} /> 
              <span>Job Hub Manager</span>
            </h1>
            <p className={styles.subtitle}>Quản trị hệ thống tin tuyển dụng và trạng thái listing.</p>
          </div>
          <button 
            disabled 
            className={cn(styles.addBtn, "opacity-50 cursor-not-allowed")}
          >
            <Plus size={18} /> 
            Đăng tin mới
          </button>
        </div>

        <div className={styles.contentStack}>
          <div className={styles.controlBar}>
            <div className={styles.searchContainer}>
              <Search className={styles.searchIcon} />
              <input 
                type="text" 
                placeholder="Tìm tên công việc, công ty..." 
                className={styles.searchInput}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <button onClick={fetchJobs} className={styles.refreshBtn}>
              <RefreshCcw size={18} className={cn(isLoading && "animate-spin")} />
            </button>
          </div>

          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr className={styles.tableHeader}>
                  <th className={styles.th}>Công việc / Công ty</th>
                  <th className={styles.th}>Địa điểm</th>
                  <th className={styles.th}>Lương</th>
                  <th className={styles.th}>Trạng thái</th>
                  <th className={cn(styles.th, styles.thRight)}>Sửa</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((job) => (
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
                       <div className={styles.metaInfo}>
                          <MapPin size={14} />
                          {job.location}
                       </div>
                    </td>
                    <td className={styles.td}>
                       <div className={styles.metaInfo}>
                          <DollarSign size={14} />
                          {job.max_salary_vnd ? `${(job.max_salary_vnd/1000000).toFixed(0)}M` : "Thỏa thuận"}
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
                    <h3 className={styles.modalTitle}>Cấu hình tin tuyển dụng</h3>
                </div>
                <div className={styles.modalBody}>
                   <div className={styles.formGrid}>
                      <div className={styles.formField}>
                         <label>Tiêu đề công việc</label>
                         <input 
                           value={formData.title}
                           onChange={e => setFormData({...formData, title: e.target.value})}
                         />
                      </div>
                      <div className={styles.formField}>
                         <label>Công ty</label>
                         <input 
                           value={formData.company_name}
                           onChange={e => setFormData({...formData, company_name: e.target.value})}
                         />
                      </div>
                      <div className={styles.formField}>
                         <label>Trạng thái</label>
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
                   <button onClick={() => setIsModalOpen(false)}>Hủy</button>
                   <button onClick={handleSave} className={styles.submitBtn}>Cập nhật công việc</button>
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

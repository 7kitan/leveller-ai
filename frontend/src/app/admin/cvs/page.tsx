"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import Pagination from "@/components/shared/Pagination";
import { 
  FileText, 
  Search, 
  RefreshCcw,
  Clock,
  ExternalLink,
  Trash2
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-cvs.module.css";
import { format } from "date-fns";

interface AdminCV {
  id: string;
  user_email: string;
  full_name: string;
  status: string;
  created_at: string;
  file_url: string;
}

const AdminCVsPage = () => {
  const { token } = useAuth();
  const [cvs, setCvs] = useState<AdminCV[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [pageSize] = useState(10);

  const fetchCVs = async (page = 1) => {
    setLoading(true);
    try {
      const offset = (page - 1) * pageSize;
      const resp = await axios.get("/api/analysis/admin/cvs", {
        params: {
          limit: pageSize,
          offset: offset,
          q: searchTerm || undefined
        },
        headers: { Authorization: `Bearer ${token}` }
      });
      setCvs(resp.data.items || []);
      setTotalPages(resp.data.pages || 0);
      setCurrentPage(page);
    } catch (err) {
      console.error("Fetch CVS error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchCVs(1);
  }, [token]);

  // Handle search resets pagination
  useEffect(() => {
    const timer = setTimeout(() => {
      if (token) fetchCVs(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const handleDelete = async (id: string) => {
    if (!confirm("Xóa hồ sơ này? Hành động này không thể hoàn tác.")) return;
    try {
      await axios.delete(`/api/analysis/admin/cvs/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchCVs();
    } catch (err) {
      console.error("Delete CV error:", err);
    }
  };

  const filtered = cvs;

  const getStatusClass = (status: string) => {
    switch (status) {
      case "completed": return styles.statusCompleted;
      case "processing": return styles.statusProcessing;
      case "failed": return styles.statusFailed;
      default: return styles.statusPending;
    }
  };

  return (
    <AuthGuard requireAdmin>
      <div className={styles.pageRoot}>
        {/* Header */}
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>
              <FileText size={40} className={styles.titleIcon} /> 
              <span>Giám sát Kho hồ sơ</span>
            </h1>
            <p className={styles.subtitle}>Quản lý trạng thái bóc tách CV và liên kết thực thể người dùng.</p>
          </div>
          <div className={styles.statsGrid}>
             <div className={styles.statCard}>
                <div className={styles.statLabel}>Tổng hồ sơ</div>
                <div className={styles.statValue}>{cvs.length}</div>
             </div>
             <div className={styles.statCard}>
                <div className={styles.statLabel}>Đã bóc tách</div>
                <div className={cn(styles.statValue, styles.statValueSuccess)}>{cvs.filter(c => c.status === "completed").length}</div>
             </div>
             <div className={styles.statCard}>
                <div className={styles.statLabel}>Đang xử lý</div>
                <div className={cn(styles.statValue, styles.statValueWarning)}>{cvs.filter(c => c.status === "processing").length}</div>
             </div>
             <div className={styles.statCard}>
                <div className={styles.statLabel}>Lỗi AI</div>
                <div className={cn(styles.statValue, styles.statValueDanger)}>{cvs.filter(c => c.status === "failed").length}</div>
             </div>
          </div>
        </div>

        <div className={styles.verticalStack8}>
           {/* Controls */}
           <div className={styles.controlBar}>
              <div className={styles.searchContainer}>
                 <Search className={styles.searchIcon} />
                 <input 
                    type="text" 
                    placeholder="Tìm theo tên hoặc email..." 
                    className={styles.searchInput}
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                 />
              </div>
              <button onClick={() => fetchCVs(currentPage)} className={styles.refreshBtn}>
                 <RefreshCcw size={18} className={cn(loading && "animate-spin")} />
              </button>
           </div>

           {/* Table */}
           <div className={styles.tableContainer}>
              <table className={styles.table}>
                 <thead>
                    <tr className={styles.tableHeader}>
                       <th className={styles.th}>Chủ sở hữu</th>
                       <th className={styles.th}>Trạng thái</th>
                       <th className={styles.th}>Ngày tải lên</th>
                       <th className={styles.th}>ID Parser</th>
                       <th className={cn(styles.th, styles.thRight)}>Thao tác</th>
                    </tr>
                 </thead>
                 <tbody>
                    {loading ? (
                       <tr>
                          <td colSpan={5}>
                             <div className={styles.emptyState}>
                                <div className={styles.spinner}></div>
                                <span className={styles.emptyStateTextSmall}>Fetching repository...</span>
                             </div>
                          </td>
                       </tr>
                    ) : filtered.length === 0 ? (
                       <tr>
                          <td colSpan={5}>
                             <div className={styles.emptyState}>
                                <FileText size={48} />
                                <span className={styles.emptyStateTextMain}>Không tìm thấy hồ sơ phù hợp.</span>
                             </div>
                          </td>
                       </tr>
                    ) : (
                       filtered.map((cv) => (
                          <tr key={cv.id} className={styles.tr}>
                             <td className={styles.td}>
                                <div className={styles.userCell}>
                                   <span className={styles.userName}>{cv.full_name || "Unknown User"}</span>
                                   <span className={styles.userEmail}>{cv.user_email}</span>
                                </div>
                             </td>
                             <td className={styles.td}>
                                <span className={cn(styles.statusBadge, getStatusClass(cv.status))}>
                                   {cv.status}
                                </span>
                             </td>
                             <td className={styles.td}>
                                <div className={cn(styles.flexRowGap, styles.dateCell)}>
                                   <Clock size={14} />
                                   {format(new Date(cv.created_at), "dd/MM/yyyy")}
                                </div>
                             </td>
                             <td className={styles.td}>
                                <code className={styles.idBadge}>
                                   {cv.id.substring(0, 10)}...
                                </code>
                             </td>
                             <td className={styles.td}>
                                <div className={styles.actionGroup}>
                                   {cv.file_url && (
                                      <a 
                                         href={cv.file_url} 
                                         target="_blank" 
                                         rel="noopener noreferrer"
                                         className={styles.actionBtn}
                                      >
                                         <ExternalLink size={18} />
                                      </a>
                                   )}
                                   <button 
                                      onClick={() => handleDelete(cv.id)}
                                      className={cn(styles.actionBtn, styles.actionBtnDelete)}
                                   >
                                      <Trash2 size={18} />
                                   </button>
                                </div>
                             </td>
                          </tr>
                       ))
                    )}
                 </tbody>
              </table>
           </div>
           <Pagination 
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={(page) => fetchCVs(page)}
              className="mt-6"
            />
        </div>
      </div>
    </AuthGuard>
  );
};

export default AdminCVsPage;

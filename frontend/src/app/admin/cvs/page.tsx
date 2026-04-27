"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import api from "@/lib/api";
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
import { useLanguage } from "@/context/LanguageContext";
import { useAlert } from "@/context/AlertContext";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";

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
  const { t } = useLanguage();
  const { confirm, showSuccess, showError } = useAlert();
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
      const resp = await api.get("analysis/admin/cvs", {
        params: {
          limit: pageSize,
          offset: (page - 1) * pageSize,
          q: searchTerm || undefined
        }
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
    const confirmed = await confirm({
      title: t("delete"),
      message: t("admin_cvs_delete_confirm"),
      confirmText: t("delete"),
      cancelText: t("cancel"),
      variant: "danger"
    });
    
    if (!confirmed) return;
    
    try {
      await api.delete(`analysis/admin/cvs/${id}`);
      showSuccess(t("cv_delete_success"));
      fetchCVs();
    } catch (err) {
      console.error("Delete CV error:", err);
      showError(t("cv_delete_error"));
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
      <PageContainer>
        <PageHeader 
          title={t("admin_cvs_title")}
          subtitle={t("admin_cvs_subtitle")}
        />

        <div className={styles.statsGrid}>
           <div className={styles.statCard}>
              <div className={styles.statLabel}>{t("admin_cvs_total")}</div>
              <div className={styles.statValue}>{cvs.length}</div>
           </div>
           <div className={styles.statCard}>
              <div className={styles.statLabel}>{t("admin_cvs_parsed")}</div>
              <div className={cn(styles.statValue, styles.statValueSuccess)}>{cvs.filter(c => c.status === "completed").length}</div>
           </div>
           <div className={styles.statCard}>
              <div className={styles.statLabel}>{t("admin_cvs_processing")}</div>
              <div className={cn(styles.statValue, styles.statValueWarning)}>{cvs.filter(c => c.status === "processing").length}</div>
           </div>
           <div className={styles.statCard}>
              <div className={styles.statLabel}>{t("admin_cvs_error")}</div>
              <div className={cn(styles.statValue, styles.statValueDanger)}>{cvs.filter(c => c.status === "failed").length}</div>
           </div>
        </div>

        <div className={styles.verticalStack8}>
           {/* Controls */}
           <div className={styles.controlBar}>
              <div className={styles.searchContainer}>
                 <Search className={styles.searchIcon} />
                 <input 
                    type="text" 
                    placeholder={t("admin_cvs_search_placeholder")} 
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
                       <th className={styles.th}>{t("admin_cvs_table_owner")}</th>
                       <th className={styles.th}>{t("admin_cvs_table_status")}</th>
                       <th className={styles.th}>{t("admin_cvs_table_date")}</th>
                       <th className={styles.th}>{t("admin_cvs_table_parser_id")}</th>
                       <th className={cn(styles.th, styles.thRight)}>{t("admin_cvs_table_actions")}</th>
                    </tr>
                 </thead>
                 <tbody>
                    {loading ? (
                       <tr>
                          <td colSpan={5}>
                             <div className={styles.emptyState}>
                                <div className={styles.spinner}></div>
                                <span className={styles.emptyStateTextSmall}>{t("admin_cvs_fetching")}</span>
                             </div>
                          </td>
                       </tr>
                    ) : filtered.length === 0 ? (
                       <tr>
                          <td colSpan={5}>
                             <div className={styles.emptyState}>
                                <FileText size={48} />
                                <span className={styles.emptyStateTextMain}>{t("admin_cvs_no_results")}</span>
                             </div>
                          </td>
                       </tr>
                    ) : (
                       filtered.map((cv) => (
                          <tr key={cv.id} className={styles.tr}>
                             <td className={styles.td}>
                                <div className={styles.userCell}>
                                   <span className={styles.userName}>{cv.full_name || t("admin_cvs_unknown_user")}</span>
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
      </PageContainer>
    </AuthGuard>
  );
};

export default AdminCVsPage;




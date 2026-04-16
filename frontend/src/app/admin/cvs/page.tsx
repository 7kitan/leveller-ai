"use client";

import React, { useEffect, useState } from "react";
import { 
  FileText, 
  User, 
  Clock, 
  CheckCircle2, 
  AlertCircle,
  Search,
  ExternalLink,
  Trash2,
  RefreshCcw,
  Mail
} from "lucide-react";
import { format } from "date-fns";
import toast from "react-hot-toast";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import styles from "./admin-cvs.module.css";

interface AdminCV {
  id: string;
  user_email: string;
  full_name: string | null;
  status: string;
  created_at: string;
}

const AdminCVPage = () => {
  const { token } = useAuth();
  const [cvs, setCvs] = useState<AdminCV[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const fetchCVs = async () => {
    if (!token) return;
    try {
      setLoading(true);
      const res = await fetch("/api/cv/admin/all", {
        headers: { 
          "X-Is-Admin": "true",
          "Authorization": `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error("Failed to fetch CVs");
      const data = await res.json();
      setCvs(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      toast.error("Không thể tải danh sách CV hệ thống");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCVs();
  }, []);

  const handleDeleteCV = async (cvId: string) => {
    if (!window.confirm("Bạn có chắc chắn muốn xóa hồ sơ này? Hành động này không thể hoàn tác.")) return;

    try {
      const res = await fetch(`/api/cv/${cvId}`, {
        method: "DELETE",
        headers: {
          "X-Is-Admin": "true",
          "Authorization": `Bearer ${token}`
        }
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to delete CV");
      }

      toast.success("Đã xóa hồ sơ thành công");
      setCvs(prev => prev.filter(cv => cv.id !== cvId));
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || "Lỗi khi xóa hồ sơ");
    }
  };

  const filteredCVs = cvs.filter(cv => {
    const matchesSearch = 
      cv.user_email.toLowerCase().includes(searchTerm.toLowerCase()) || 
      (cv.full_name?.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesStatus = statusFilter === "all" || cv.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <span className="admin-status-badge admin-badge-ready"><CheckCircle2 size={12}/> Ready</span>;
      case "processing":
        return <span className="admin-status-badge admin-badge-analyzing"><Clock size={12}/> Analyzing</span>;
      case "failed":
        return <span className="admin-status-badge admin-badge-error"><AlertCircle size={12}/> Error</span>;
      default:
        return <span className="admin-status-badge">{status}</span>;
    }
  };

  return (
    <div className={styles.pageRoot}>
      {/* Header */}
      <div className={styles.headerContainer}>
        <div className="space-y-1">
          <div className={styles.headerMeta}>
            <FileText size={14} /> Data Repository
          </div>
          <h1 className={styles.headerTitle}>CV Repository</h1>
          <p className={styles.headerSubtitle}>Giám sát và quản lý dữ liệu hồ sơ toàn hệ thống.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <button 
            onClick={fetchCVs}
            className={styles.syncBtn}
          >
            <RefreshCcw size={18} className={loading ? "animate-spin" : ""} /> Sync Data
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className={styles.statsGrid}>
        <div className="admin-card">
          <div className="text-white/30 text-xs font-black uppercase tracking-widest mb-4">Tổng hồ sơ</div>
          <div className="text-3xl font-black text-white">{cvs.length}</div>
        </div>
        <div className="admin-card">
          <div className="text-white/30 text-xs font-black uppercase tracking-widest mb-4">Đã bóc tách</div>
          <div className="text-3xl font-black text-emerald-400">{cvs.filter(c => c.status === "completed").length}</div>
        </div>
        <div className="admin-card">
          <div className="text-white/30 text-xs font-black uppercase tracking-widest mb-4">Đang xử lý</div>
          <div className="text-3xl font-black text-amber-400">{cvs.filter(c => c.status === "processing").length}</div>
        </div>
        <div className="admin-card">
          <div className="text-white/30 text-xs font-black uppercase tracking-widest mb-4">Lỗi AI</div>
          <div className="text-3xl font-black text-red-500">{cvs.filter(c => c.status === "failed").length}</div>
        </div>
      </div>

      {/* Control Bar */}
      <div className="admin-control-bar">
        <div className={styles.searchWrapper}>
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20 group-focus-within:text-indigo-500 transition-colors" size={18} />
          <input 
            type="text"
            placeholder="Tìm kiếm theo email, tên ứng viên..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={styles.searchInput}
          />
        </div>
        <div className="flex items-center gap-3">
           <div className={styles.statusFilter}>
              {["all", "completed", "processing", "failed"].map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`${styles.filterBtn} ${
                    statusFilter === s ? styles.filterBtnActive : styles.filterBtnInactive
                  }`}
                >
                  {s}
                </button>
              ))}
           </div>
        </div>
      </div>

      {/* CVs Table */}
      <div className="admin-table-container">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr>
                <th className={styles.tableTh}>Candidate</th>
                <th className={styles.tableTh}>Email Owner</th>
                <th className={styles.tableTh}>Status</th>
                <th className={styles.tableTh}>System ID</th>
                <th className={styles.tableTh}>Uploaded</th>
                <th className={`${styles.tableTh} text-right`}>Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-8 py-20 text-center">
                    <div className="flex flex-col items-center gap-4">
                      <div className="w-10 h-10 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin"></div>
                      <span className="text-white/20 font-black uppercase tracking-widest text-xs">Fetching repository...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredCVs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-8 py-20 text-center text-white/20 font-bold italic">
                    Không tìm thấy hồ sơ phù hợp.
                  </td>
                </tr>
              ) : (
                filteredCVs.map((cv) => (
                  <tr key={cv.id} className={styles.tableTr}>
                    <td className={styles.tableTd}>
                       <div className={styles.candidateInfo}>
                          <div className={styles.candidateAvatar}>
                             <User size={18} />
                          </div>
                          <div className={styles.candidateName}>
                             {cv.full_name || "Untitled CV"}
                          </div>
                       </div>
                    </td>
                    <td className={styles.tableTd}>
                       <div className="flex items-center gap-2 text-white/50 text-xs">
                          <Mail size={14} className="opacity-30" />
                          {cv.user_email}
                       </div>
                    </td>
                    <td className={styles.tableTd}>
                       {getStatusBadge(cv.status)}
                    </td>
                    <td className={styles.tableTd}>
                      <code className="text-[10px] font-mono text-white/30 bg-black/20 px-2 py-1 rounded">
                        {cv.id.substring(0, 8)}...
                      </code>
                    </td>
                    <td className={styles.tableTd}>
                      <div className="flex items-center gap-2 text-white/50 text-xs font-medium">
                        <Clock size={14} className="opacity-50" />
                        {format(new Date(cv.created_at), "MMM dd, HH:mm")}
                      </div>
                    </td>
                    <td className={`${styles.tableTd} text-right`}>
                       <div className={styles.actionGroup}>
                          <Link 
                            href={`/user/cv/${cv.id}`}
                            className={styles.actionBtn}
                            title="View Analysis"
                          >
                            <ExternalLink size={18} />
                          </Link>
                          <button 
                            onClick={() => handleDeleteCV(cv.id)}
                            className={styles.deleteBtn}
                            title="Delete CV"
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
      </div>
    </div>
  );
};

export default AdminCVPage;

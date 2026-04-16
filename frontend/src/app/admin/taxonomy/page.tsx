"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { 
  Plus, 
  Search, 
  Edit2, 
  Tag, 
  RefreshCcw,
  CheckCircle2,
  AlertCircle,
  BookOpen,
  ArrowRight
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface SkillNode {
  name: string;
  category: string;
  type: string;
  aliases: string[];
}

interface GroupedRelationship {
  parent: string;
  children: { name: string; type: string }[];
}

const API_BASE = "/api/analysis/admin/taxonomy";

import styles from "./admin-taxonomy.module.css";

const TaxonomyAdminPage = () => {
  const { token } = useAuth();
  
  // Dictionary States
  const [skills, setSkills] = useState<SkillNode[]>([]);
  const [isSkillModalOpen, setIsSkillModalOpen] = useState(false);
  const [currentSkill, setCurrentSkill] = useState<Partial<SkillNode>>({ name: "", category: "Technology", aliases: [] });
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null);

  const fetchSkills = async () => {
    setLoading(true);
    try {
      const resp = await axios.get(`${API_BASE}/skills`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSkills(resp.data);
    } catch (err) {
      showNotification("Không thể tải danh sách kỹ năng", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchSkills();
    }
  }, [token]);

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleSaveSkill = async () => {
    try {
      await axios.post(`${API_BASE}/skills`, currentSkill, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification(`Đã cập nhật ánh xạ cho: ${currentSkill.name}`);
      setIsSkillModalOpen(false);
      fetchSkills();
    } catch (err) {
      showNotification("Lỗi khi cập nhật từ điển", "error");
    }
  };

  const filteredSkills = skills.filter(s => 
    s.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    s.aliases?.some(a => a.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <AuthGuard requireAdmin>
      <div className={styles.pageRoot}>
        {/* Header */}
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>
              <BookOpen className="text-indigo-500 w-8 h-8" /> Từ điển Thực thể Kỹ thuật
            </h1>
            <p className={styles.subtitle}>Quản lý cách AI chuẩn hóa các thuật ngữ, kỹ năng và vị trí chuyên môn.</p>
          </div>
          <button 
            onClick={() => { setCurrentSkill({ name: "", category: "Technology", aliases: [] }); setIsSkillModalOpen(true); }}
            className={styles.addBtn}
          >
            <Plus className="w-4 h-4" /> Thêm ánh xạ mới
          </button>
        </div>

        <div className="space-y-6">
          <div className={styles.controlBar}>
            <div className={styles.searchWrapper}>
              <Search className={styles.searchIcon} />
              <input 
                type="text" 
                placeholder="Tìm từ đồng nghĩa hoặc thuật ngữ chính..." 
                className={styles.searchInput}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <button onClick={fetchSkills} className={styles.refreshBtn}>
              <RefreshCcw className={cn("w-5 h-5", loading && "animate-spin")} />
            </button>
          </div>

          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr className={styles.tableHeader}>
                  <th className="px-8 py-5">Cách diễn đạt / Từ đồng nghĩa (Aliases)</th>
                  <th className="px-8 py-5 text-center w-20"></th>
                  <th className="px-8 py-5">Thực thể chính (Reference Entity)</th>
                  <th className="px-8 py-5 text-right w-24">Sửa</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 text-slate-300">
                {filteredSkills.map((s) => (
                  <tr key={s.name} className={styles.tableRow}>
                    <td className="px-8 py-6">
                      <div className={styles.aliasWrapper}>
                        {s.aliases?.length > 0 ? (
                          s.aliases.map(a => (
                            <span key={a} className={styles.aliasBadge}>
                              <Tag className={styles.aliasIcon} /> {a}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-600 italic text-sm">Chưa có alias</span>
                        )}
                      </div>
                    </td>
                    <td className="px-8 py-6 text-center text-slate-700 group-hover:text-indigo-500">
                      <ArrowRight className={styles.arrowIcon} />
                    </td>
                    <td className="px-8 py-6">
                      <span className={styles.entityName}>{s.name}</span>
                      <div className={styles.entityMeta}>
                        <span className={styles.categoryLabel}>{s.category}</span>
                        <span className="w-1 h-1 rounded-full bg-slate-700"></span>
                        <span className={styles.metaBadge}>ENTITY</span>
                      </div>
                    </td>
                    <td className="px-8 py-6 text-right">
                      <button 
                        onClick={() => { setCurrentSkill(s); setIsSkillModalOpen(true); }} 
                        className={styles.actionBtn}
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
                
                {filteredSkills.length === 0 && !loading && (
                  <tr>
                    <td colSpan={4} className="px-8 py-20 text-center text-slate-500 italic">
                      <Search className="w-12 h-12 mx-auto mb-4 opacity-10" />
                      Không tìm thấy thực thể kỹ thuật nào khớp với từ khóa.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* NOTIFICATION TOAST */}
        {notification && (
          <div className={cn(
            styles.notification,
            notification.type === 'success' ? styles.notifSuccess : styles.notifError
          )}>
            <div className={cn("p-2 rounded-lg", notification.type === 'success' ? "bg-emerald-500/20" : "bg-rose-500/20")}>
              {notification.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
            </div>
            <span className="font-bold tracking-tight">{notification.message}</span>
          </div>
        )}

        {/* MODAL */}
        {isSkillModalOpen && (
          <div className={styles.modalRoot}>
            <div className={styles.modalContent}>
              <div className={styles.modalHeader}>
                <h3 className="text-2xl font-bold text-white tracking-tight">Cấu hình Ánh xạ Thực thể</h3>
              </div>
              <div className={styles.modalBody}>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Tên chuẩn (English / AI ID)</label>
                  <input 
                    type="text" 
                    className={styles.inputField}
                    placeholder="e.g. React.js"
                    value={currentSkill.name}
                    onChange={(e) => setCurrentSkill({...currentSkill, name: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Bí danh (Aliases - Cách nhau bằng dấu phẩy)</label>
                  <textarea 
                    className={styles.textareaField}
                    placeholder="e.g. Lập trình React, UI Development, ReactJS"
                    value={currentSkill.aliases?.join(", ")}
                    onChange={(e) => setCurrentSkill({...currentSkill, aliases: e.target.value.split(",").map(a => a.trim()).filter(a => a !== "")})}
                  />
                  <p className="text-[10px] text-slate-600 px-1 mt-1">Các chuỗi này khi xuất hiện trong CV/Job desc sẽ được AI map về tên chuẩn ở trên.</p>
                </div>
              </div>
              <div className={styles.modalFooter}>
                <button onClick={() => setIsSkillModalOpen(false)} className="px-6 py-3 text-slate-500 hover:text-white font-bold transition-colors">Hủy</button>
                <button 
                  onClick={handleSaveSkill} 
                  className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3 rounded-2xl font-black transition-all shadow-xl shadow-indigo-600/20 transform active:scale-95"
                >Lưu ánh xạ</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AuthGuard>
  );
};

export default TaxonomyAdminPage;

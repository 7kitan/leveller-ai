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
  CheckCircle2,
  AlertCircle,
  Database,
  Edit2,
  Tags,
  BookOpen
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-taxonomy.module.css";
import { motion, AnimatePresence } from "framer-motion";

interface TaxonomyEntity {
  id: string;
  reference_name: string;
  aliases: string[];
}

const API_BASE = "/api/analysis/admin/taxonomy";

const TaxonomyAdminPage = () => {
  const { token } = useAuth();
  const [entities, setEntities] = useState<TaxonomyEntity[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({ reference_name: "", aliases: "" });
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null);

  const fetchTaxonomy = async () => {
    setIsLoading(true);
    try {
      const resp = await axios.get(`${API_BASE}/entities`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEntities(resp.data);
    } catch (err) {
      showNotification("Không thể tải danh sách thực thể", "error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchTaxonomy();
  }, [token]);

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleSave = async () => {
    try {
      const payload = {
        reference_name: formData.reference_name,
        aliases: formData.aliases.split(',').map(s => s.trim()).filter(Boolean)
      };

      if (editingId) {
        await axios.put(`${API_BASE}/entities/${editingId}`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        showNotification("Đã cập nhật thực thể");
      } else {
        await axios.post(`${API_BASE}/entities`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        showNotification("Đã thêm thực thể mới");
      }
      setIsModalOpen(false);
      fetchTaxonomy();
    } catch (err) {
      showNotification("Lỗi khi lưu thực thể", "error");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Xóa thực thể này? Các aliases linked cũng sẽ bị mất.")) return;
    try {
      await axios.delete(`${API_BASE}/entities/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification("Đã xóa thực thể");
      fetchTaxonomy();
    } catch (err) {
      showNotification("Lỗi khi xóa thực thể", "error");
    }
  };

  const openEdit = (entity: TaxonomyEntity) => {
    setEditingId(entity.id);
    setFormData({
      reference_name: entity.reference_name,
      aliases: entity.aliases.join(", ")
    });
    setIsModalOpen(true);
  };

  const filtered = entities.filter(e => 
    e.reference_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e.aliases.some(a => a.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <AuthGuard requireAdmin>
      <div className={styles.pageRoot}>
        {/* Header */}
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>
              <Database size={40} style={{ color: "#818cf8" }} /> 
              <span>Cognitive Reference Hub</span>
            </h1>
            <p className={styles.subtitle}>Chuẩn hóa và quản lý danh mục kĩ năng, công nghệ trong Knowledge Graph.</p>
          </div>
          <button 
            onClick={() => {
              setEditingId(null);
              setFormData({ reference_name: "", aliases: "" });
              setIsModalOpen(true);
            }} 
            className={styles.addBtn}
          >
            <Plus size={18} /> 
            Thêm thực thể
          </button>
        </div>

        <div className={styles.verticalStack8}>
          {/* Controls */}
          <div className={styles.controlBar}>
            <div className={styles.searchContainer}>
              <Search className={styles.searchIcon} />
              <input 
                type="text" 
                placeholder="Tìm thực thể hoặc alias..." 
                className={styles.searchInput}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <button onClick={fetchTaxonomy} className={styles.refreshBtn}>
              <RefreshCcw size={18} className={cn(isLoading && "animate-spin")} />
            </button>
          </div>

          {/* List Table */}
          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr className={styles.tableHeader}>
                  <th className={cn(styles.th, styles.thWidth1_3)}>Thực thể chính (Reference Entity)</th>
                  <th className={styles.th}>Cách diễn đạt / Từ đồng nghĩa (Aliases)</th>
                  <th className={cn(styles.th, styles.thWidthW20)} style={{ textAlign: "center" }}></th>
                  <th className={cn(styles.th, styles.thWidthW24)} style={{ textAlign: "right" }}>Sửa</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((entity) => (
                  <tr key={entity.id} className={styles.tr}>
                    <td className={styles.td}>
                      <div className={styles.flexCenterGap3}>
                         <BookOpen size={14} style={{ color: "#818cf8" }} />
                         <span className={styles.entityName}>{entity.reference_name}</span>
                      </div>
                    </td>
                    <td className={styles.td}>
                      <div className={styles.aliasGroup}>
                        {entity.aliases.map((a, i) => (
                          <span key={i} className={styles.aliasBadge}>
                            {a}
                          </span>
                        ))}
                        {entity.aliases.length === 0 && <span className={styles.emptyAlias}>Chưa có alias</span>}
                      </div>
                    </td>
                    <td className={styles.td}>
                        <div className={styles.separatorDot}></div>
                    </td>
                    <td className={styles.td}>
                      <div className={styles.flexCenterEndGap3}>
                        <button onClick={() => openEdit(entity)} className={styles.actionBtn}>
                          <Edit2 size={16} />
                        </button>
                        <button onClick={() => handleDelete(entity.id)} className={cn(styles.actionBtn, styles.actionBtnDelete)}>
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && !isLoading && (
                  <tr>
                    <td colSpan={4}>
                      <div className={styles.emptyState}>
                        <Tags size={48} />
                        <p style={{ fontSize: "0.875rem", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.2em", fontStyle: "italic" }}>Không tìm thấy thực thể nào</p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal */}
        <AnimatePresence>
          {isModalOpen && (
            <div className={styles.modalOverlay}>
              <motion.div 
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                className={styles.modalContent}
              >
                <div className={styles.modalHeader}>
                    <h3 className={styles.modalTitle}>
                        <Database size={24} style={{ color: "#818cf8" }} /> 
                        <span>Cấu hình Thực thể</span>
                    </h3>
                </div>
                <div className={styles.modalBody}>
                  <div className={styles.verticalStack4}>
                    <div className={styles.verticalStack1}>
                      <label className={styles.inputLabel}>Tên chuẩn (English / ID)</label>
                      <input 
                        type="text" 
                        className={styles.modalInput}
                        placeholder="e.g. JavaScript"
                        value={formData.reference_name}
                        onChange={(e) => setFormData({...formData, reference_name: e.target.value})}
                      />
                    </div>
                    <div className={styles.verticalStack1}>
                      <label className={styles.inputLabel}>Bí danh (Aliases)</label>
                      <textarea 
                        className={styles.modalInput}
                        style={{ minHeight: "8rem", paddingTop: "1rem" }}
                        placeholder="e.g. JS, ES6, VanillaJS..."
                        value={formData.aliases}
                        onChange={(e) => setFormData({...formData, aliases: e.target.value})}
                      />
                      <p style={{ fontSize: "10px", color: "rgba(255,255,255,0.2)", fontStyle: "italic", padding: "0.5rem" }}>
                        Tự động chuẩn hóa về tên chính trong quá trình phân tích.
                      </p>
                    </div>
                  </div>
                </div>
                <div className={styles.modalFooter}>
                  <button 
                    onClick={() => setIsModalOpen(false)} 
                    style={{ fontSize: "10px", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.2em", color: "rgba(255,255,255,0.3)" }}
                  >
                    Hủy
                  </button>
                  <button onClick={handleSave} className={styles.submitBtn}>
                    {editingId ? "Cập nhật" : "Tạo thực thể"}
                  </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>

        {/* Notif */}
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
              <div style={{ padding: "0.5rem", borderRadius: "1rem", backgroundColor: notification.type === 'success' ? "rgba(16, 185, 129, 0.2)" : "rgba(244, 63, 94, 0.2)", color: notification.type === 'success' ? "#10b981" : "#f43f5e" }}>
                {notification.type === 'success' ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
              </div>
              <span style={{ fontWeight: 700 }}>{notification.message}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </AuthGuard>
  );
};

export default TaxonomyAdminPage;

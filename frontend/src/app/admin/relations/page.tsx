"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { 
  Plus, 
  Trash2, 
  Network,
  ChevronDown,
  ChevronUp,
  Layers,
  RefreshCcw,
  CheckCircle2,
  AlertCircle
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-relations.module.css";
import { motion, AnimatePresence } from "framer-motion";

interface GroupedRelationship {
  parent: string;
  parent_type: string;
  parent_category: string;
  is_root: boolean;
  children: { name: string; type: string }[];
}

const API_BASE = "/api/analysis/admin/taxonomy";

const RelationsAdminPage = () => {
  const { token } = useAuth();
  const [groupedRels, setGroupedRels] = useState<GroupedRelationship[]>([]);
  const [expandedParents, setExpandedParents] = useState<Set<string>>(new Set());
  const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'all' | 'positions'>('all');
  const [linkData, setLinkData] = useState({ parent: "", child: "", rel_type: "COMPRISED_OF" });
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null);

  const fetchGroupedRelationships = async (type?: string) => {
    setLoading(true);
    setGroupedRels([]);
    try {
      const resp = await axios.get(`${API_BASE}/relationships/grouped`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { type }
      });
      setGroupedRels(resp.data);
    } catch (err) {
      showNotification("Không thể tải danh sách quan hệ phân cấp", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      if (viewMode === 'positions') {
        fetchGroupedRelationships('Position');
      } else {
        fetchGroupedRelationships();
      }
    }
  }, [token, viewMode]);

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const toggleParent = (parent: string) => {
    const next = new Set(expandedParents);
    if (next.has(parent)) next.delete(parent);
    else next.add(parent);
    setExpandedParents(next);
  };

  const handleLinkSkills = async () => {
    try {
      await axios.post(`${API_BASE}/link`, linkData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      showNotification("Đã thiết lập mối quan hệ");
      setIsLinkModalOpen(false);
      fetchGroupedRelationships(viewMode === 'positions' ? 'Position' : undefined);
    } catch (err) {
      showNotification("Lỗi khi thiết lập quan hệ", "error");
    }
  };

  const handleDeleteRel = async (parent: string, child: string, relType: string) => {
    if (!confirm(`Xóa quan hệ giữa ${parent} and ${child}?`)) return;
    try {
      await axios.delete(`${API_BASE}/relationships`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { parent, child, rel_type: relType }
      });
      showNotification("Đã xóa quan hệ");
      fetchGroupedRelationships(viewMode === 'positions' ? 'Position' : undefined);
    } catch (err) {
      showNotification("Lỗi khi xóa quan hệ", "error");
    }
  };

  const filteredRels = groupedRels.filter(rel => {
    if (viewMode === 'positions') {
      return rel.parent_type === 'Position' || rel.parent_type === 'Role';
    }
    return true; 
  });

  const getParentStyle = (rel: GroupedRelationship) => {
    if (rel.parent_type === 'Position' || rel.parent_type === 'Role') {
      return { text: (rel.parent_type || "POSITION").toUpperCase(), className: styles.badgePosition };
    }
    if (rel.parent_type === 'Domain') {
      return { text: "DOMAIN", className: styles.badgeDomain };
    }
    if (rel.parent_category === 'Technology') {
      return { text: "CORE TECH", className: styles.badgeTech };
    }
    return { text: (rel.parent_type || "PARENT").toUpperCase(), className: styles.badgeDefault };
  };

  return (
    <AuthGuard requireAdmin>
      <div className={styles.pageRoot}>
        {/* Header */}
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>
              <Network size={40} className={styles.headerIcon} /> 
              <span>Semantic Network</span>
            </h1>
            <p className={styles.subtitle}>Định nghĩa mối quan hệ phân cấp (Cha - Con) giữa các kỹ năng và vị trí.</p>
          </div>
          <button 
            onClick={() => {
              setLinkData({ parent: "", child: "", rel_type: "COMPRISED_OF" });
              setIsLinkModalOpen(true);
            }}
            className={styles.addBtn}
          >
            <Plus size={18} /> 
            Thiết lập Quan hệ
          </button>
        </div>

        <div className={styles.contentStack}>
          <div className={styles.controlBar}>
            <div>
              <h3 className={styles.groupTitle}>Cấu trúc tri thức hiện tại</h3>
              <p className={styles.groupSub}>Chỉnh sửa mối liên kết trong Graph.</p>
            </div>
            <div className={styles.flexCenterGap1}>
              <div className={styles.toggleContainer}>
                <button 
                  onClick={() => setViewMode('all')}
                  className={cn(
                    styles.toggleBtn,
                    viewMode === 'all' ? styles.toggleBtnActive : styles.toggleBtnInactive
                  )}
                >Tất cả</button>
                <button 
                  onClick={() => setViewMode('positions')}
                  className={cn(
                    styles.toggleBtn,
                    viewMode === 'positions' ? styles.toggleBtnAmber : styles.toggleBtnInactive
                  )}
                >Vị trí</button>
              </div>
              <button 
                onClick={() => fetchGroupedRelationships(viewMode === 'positions' ? 'Position' : undefined)} 
                className={styles.refreshBtn}
              >
                <RefreshCcw size={18} className={cn(loading && "animate-spin")} />
              </button>
            </div>
          </div>

          <div className={styles.grid}>
            {filteredRels.map((group) => {
              const isExpanded = expandedParents.has(group.parent);
              const badgeInfo = getParentStyle(group);
              return (
                <div key={group.parent} className={styles.groupCard}>
                  {/* Parent Header */}
                  <div 
                    onClick={() => toggleParent(group.parent)}
                    className={styles.groupHeader}
                  >
                    <div className={styles.flexCenterGap1_5}>
                      <div className={cn(styles.groupIconWrapper, group.parent_type === 'Position' ? styles.iconPosition : styles.iconDefault)}>
                        <Layers size={24} className={group.parent_type === 'Position' ? styles.iconColorPosition : styles.iconColorDefault} />
                      </div>
                      <div>
                        <h4 className={styles.groupTitle}>{group.parent}</h4>
                        <p className={styles.groupSub}>Bao gồm {group.children.length} thành phần con</p>
                      </div>
                    </div>
                    <div className={styles.flexCenterGap1}>
                      <span className={cn(styles.badge, badgeInfo.className)}>
                        {badgeInfo.text}
                      </span>
                      {isExpanded ? <ChevronUp size={20} className={styles.loadingSpinner} /> : <ChevronDown size={20} className={styles.loadingSpinner} />}
                    </div>
                  </div>

                  {/* Children List (Expanded) */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div 
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className={styles.childrenWrapper}
                      >
                        <div className={styles.childrenGrid}>
                          {group.children.map((child, idx) => (
                            <div key={idx} className={styles.childCard}>
                              <div className={styles.flexCenterGap1}>
                                <div className={styles.childDot} />
                                <div className={styles.flexColumn}>
                                  <span className={styles.childName}>{child.name}</span>
                                  <span className={styles.childType}>{child.type}</span>
                                </div>
                              </div>
                              <button 
                                onClick={(e) => { e.stopPropagation(); handleDeleteRel(group.parent, child.name, child.type); }}
                                className={styles.actionBtnDelete}
                              >
                                <Trash2 size={16} />
                              </button>
                            </div>
                          ))}
                          <button 
                            onClick={(e) => { e.stopPropagation(); setLinkData({...linkData, parent: group.parent}); setIsLinkModalOpen(true); }}
                            className={styles.addChildBtn}
                          >
                            <Plus size={16} /> 
                            <span>Gắn thành phần</span>
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
            
            {groupedRels.length === 0 && !loading && (
              <div className={styles.emptyState}>
                <Network size={64} />
                <p className={styles.emptyStateText}>Không tìm thấy mối quan hệ nào</p>
              </div>
            )}
          </div>
        </div>

        {/* NOTIFICATION TOAST */}
        <AnimatePresence>
          {notification && (
            <motion.div 
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.9 }}
              className={cn(
                styles.notification,
                notification.type === 'success' ? styles.notifSuccess : styles.notifError
              )}
            >
              <div className={cn(styles.notifIcon, notification.type === 'success' ? styles.iconSuccess : styles.iconError)}>
                {notification.type === 'success' ? <CheckCircle2 size={24} /> : <AlertCircle size={24} />}
              </div>
              <span className={styles.notifText}>{notification.message}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* LINK MODAL */}
        <AnimatePresence>
          {isLinkModalOpen && (
            <div className={styles.modalOverlay}>
              <motion.div 
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                className={styles.modalContent}
              >
                <div className={styles.modalHeader}>
                  <h3 className={styles.modalTitle}>
                    <Network size={28} className={styles.iconColorPosition} /> 
                    <span>Thiết lập Quan hệ Graph</span>
                  </h3>
                </div>
                <div className={styles.modalBody}>
                  <div className={styles.inputGroup}>
                    <label className={styles.inputLabel}>Kỹ năng CHA (Nhóm chính)</label>
                    <input 
                      type="text" 
                      className={styles.inputField}
                      placeholder="e.g. Backend Developer"
                      value={linkData.parent}
                      onChange={(e) => setLinkData({...linkData, parent: e.target.value})}
                    />
                  </div>
                  <div className={styles.inputGroup}>
                    <label className={styles.inputLabel}>Kỹ năng CON (Thành phần)</label>
                    <input 
                      type="text" 
                      className={styles.inputField}
                      placeholder="e.g. PostgreSQL"
                      value={linkData.child}
                      onChange={(e) => setLinkData({...linkData, child: e.target.value})}
                    />
                  </div>
                </div>
                <div className={styles.modalFooter}>
                  <button onClick={() => setIsLinkModalOpen(false)} className={styles.cancelBtn}>
                    Hủy
                  </button>
                  <button onClick={handleLinkSkills} className={styles.submitBtn}>
                    Liên kết Graph
                  </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>
      </div>
    </AuthGuard>
  );
};

export default RelationsAdminPage;

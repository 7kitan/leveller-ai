"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { 
  Plus, 
  Trash2, 
  Link as LinkIcon, 
  RefreshCcw,
  CheckCircle2,
  AlertCircle,
  Network,
  ChevronDown,
  ChevronUp,
  Layers
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface GroupedRelationship {
  parent: string;
  parent_type: string;
  parent_category: string;
  is_root: boolean;
  children: { name: string; type: string }[];
}

const API_BASE = "/api/analysis/admin/taxonomy";

import styles from "./admin-relations.module.css";

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
    setGroupedRels([]); // Xoá dữ liệu cũ
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
    if (!confirm(`Xóa quan hệ giữa ${parent} và ${child}?`)) return;
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

  const getParentLabel = (rel: GroupedRelationship) => {
    if (rel.parent_type === 'Position' || rel.parent_type === 'Role') {
      return { text: (rel.parent_type || "POSITION").toUpperCase(), class: "bg-amber-500/10 text-amber-500 border-amber-500/20" };
    }
    if (rel.parent_type === 'Domain') {
        return { text: "DOMAIN", class: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20" };
    }
    if (rel.parent_category === 'Technology') {
      return { text: "CORE TECH", class: "bg-violet-500/10 text-violet-400 border-violet-500/20" };
    }
    return { text: (rel.parent_type || "PARENT").toUpperCase(), class: "bg-slate-800 text-slate-400 border-slate-700" };
  };

  return (
    <AuthGuard requireAdmin>
      <div className={styles.pageRoot}>
        {/* Header */}
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>
              <Network className="text-amber-500 w-8 h-8" /> Bản đồ Quan hệ Graph
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
            <Plus className="w-4 h-4" /> Thiết lập Quan hệ mới
          </button>
        </div>

        <div className="space-y-6">
          <div className={styles.controlBar}>
            <div>
              <h3 className={styles.controlTitle}>Cấu trúc tri thức hiện tại</h3>
              <p className={styles.controlSub}>Chỉnh sửa mối liên kết giữa các thực thể trong Graph.</p>
            </div>
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
              >Chỉ xem Vị trí</button>
              <div className="w-px h-4 bg-slate-800 mx-1"></div>
              <button onClick={() => fetchGroupedRelationships(viewMode === 'positions' ? 'Position' : undefined)} className={styles.refreshBtn}>
                <RefreshCcw className={cn("w-4 h-4", loading && "animate-spin")} />
              </button>
            </div>
          </div>

          <div className={styles.grid}>
            {filteredRels.map((group) => {
              const isExpanded = expandedParents.has(group.parent);
              const label = getParentLabel(group);
              return (
                <div key={group.parent} className={styles.groupCard}>
                  {/* Parent Header */}
                  <div 
                    onClick={() => toggleParent(group.parent)}
                    className={styles.groupHeader}
                  >
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        styles.groupIconWrapper, 
                        group.parent_type === 'Position' ? styles.iconPosition : styles.iconDefault
                      )}>
                        <Layers className={cn("w-5 h-5", 
                          group.parent_type === 'Position' ? "text-amber-500" : "text-indigo-400"
                        )} />
                      </div>
                      <div>
                        <h4 className={styles.groupTitle}>{group.parent}</h4>
                        <p className={styles.groupSub}>Bao gồm {group.children.length} thành phần con</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className={cn(styles.badge, label.class)}>
                        {label.text}
                      </span>
                      {isExpanded ? <ChevronUp className="w-5 h-5 text-slate-500" /> : <ChevronDown className="w-5 h-5 text-slate-500" />}
                    </div>
                  </div>

                  {/* Children List (Expanded) */}
                  {isExpanded && (
                    <div className={styles.childrenWrapper}>
                      <div className={styles.childrenGrid}>
                        {group.children.map((child, idx) => (
                          <div key={idx} className={styles.childCard}>
                            <div className="flex items-center gap-3">
                              <div className={styles.childDot} />
                              <span className={styles.childName}>{child.name}</span>
                              <span className={styles.childType}>({child.type})</span>
                            </div>
                            <button 
                              onClick={(e) => { e.stopPropagation(); handleDeleteRel(group.parent, child.name, child.type); }}
                              className={styles.removeChildBtn}
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ))}
                        <button 
                          onClick={(e) => { e.stopPropagation(); setLinkData({...linkData, parent: group.parent}); setIsLinkModalOpen(true); }}
                          className={styles.addChildBtn}
                        >
                          <Plus className="w-3.5 h-3.5" /> Thêm thành phần
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            
            {groupedRels.length === 0 && !loading && (
              <div className={styles.emptyState}>
                 <Network className="w-12 h-12 mx-auto mb-4 text-slate-700" />
                 <p className="text-slate-500 font-medium italic">Chưa có kĩ năng cha nào được thiết lập quan hệ.</p>
              </div>
            )}
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

        {/* LINK MODAL */}
        {isLinkModalOpen && (
          <div className={styles.modalRoot}>
            <div className={styles.modalContent}>
              <div className={styles.modalHeader}>
                <h3 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
                  <Network className="w-6 h-6 text-amber-500" /> Thiết lập Quan hệ Graph
                </h3>
              </div>
              <div className={styles.modalBody}>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Kỹ năng CHA (Nhóm chính)</label>
                  <input 
                    type="text" 
                    className={styles.inputField}
                    placeholder="e.g. Backend Developer"
                    value={linkData.parent}
                    onChange={(e) => setLinkData({...linkData, parent: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Kỹ năng CON (Thành phần)</label>
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
                <button onClick={() => setIsLinkModalOpen(false)} className="px-6 py-3 text-slate-500 hover:text-white font-bold transition-colors">Hủy</button>
                <button 
                  onClick={handleLinkSkills} 
                  className="bg-amber-600 hover:bg-amber-500 text-slate-950 px-8 py-3 rounded-2xl font-black transition-all shadow-xl shadow-amber-600/20"
                >Liên kết Graph</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AuthGuard>
  );
};

export default RelationsAdminPage;

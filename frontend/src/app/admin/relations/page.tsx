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
    setGroupedRels([]); // Xoá dữ liệu cũ để tránh hiện tượng chỉ hiện 3 positions từ cache cũ
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
      // Ở chế độ "Chỉ xem Vị trí", hiển thị tất cả các Vị trí/Vai trò để người dùng dễ quản lý
      return rel.parent_type === 'Position' || rel.parent_type === 'Role';
    }
    // Ở chế độ Tất cả, hiển thị toàn bộ mạng lưới quan hệ
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
      <div className="space-y-8 animate-in fade-in duration-500">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
              <Network className="text-amber-500 w-8 h-8" /> Bản đồ Quan hệ Graph
            </h1>
            <p className="text-slate-400">Định nghĩa mối quan hệ phân cấp (Cha - Con) giữa các kỹ năng và vị trí.</p>
          </div>
          <button 
            onClick={() => {
              setLinkData({ parent: "", child: "", rel_type: "COMPRISED_OF" });
              setIsLinkModalOpen(true);
            }}
            className="flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-400 text-slate-950 px-6 py-3 rounded-xl font-black shadow-lg shadow-amber-500/20 transition-all active:scale-95"
          >
            <Plus className="w-4 h-4" /> Thiết lập Quan hệ mới
          </button>
        </div>

        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-slate-900/50 p-6 rounded-2xl border border-slate-800 backdrop-blur-sm gap-4">
            <div>
              <h3 className="text-lg font-bold text-white mb-1">Cấu trúc tri thức hiện tại</h3>
              <p className="text-sm text-slate-500">Chỉnh sửa mối liên kết giữa các thực thể trong Graph.</p>
            </div>
            <div className="flex items-center gap-2 p-1 bg-slate-950 rounded-xl border border-slate-800">
              <button 
                onClick={() => setViewMode('all')}
                className={cn(
                  "px-4 py-2 rounded-lg text-xs font-bold transition-all",
                  viewMode === 'all' ? "bg-slate-800 text-white shadow-lg" : "text-slate-500 hover:text-slate-300"
                )}
              >Tất cả</button>
              <button 
                onClick={() => setViewMode('positions')}
                className={cn(
                  "px-4 py-2 rounded-lg text-xs font-bold transition-all",
                  viewMode === 'positions' ? "bg-amber-500 text-slate-950 shadow-lg shadow-amber-500/20" : "text-slate-500 hover:text-slate-300"
                )}
              >Chỉ xem Vị trí</button>
              <div className="w-px h-4 bg-slate-800 mx-1"></div>
              <button onClick={() => fetchGroupedRelationships(viewMode === 'positions' ? 'Position' : undefined)} className="p-2 text-slate-500 hover:text-white transition-colors">
                <RefreshCcw className={cn("w-4 h-4", loading && "animate-spin")} />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {filteredRels.map((group) => {
              const isExpanded = expandedParents.has(group.parent);
              const label = getParentLabel(group);
              return (
                <div key={group.parent} className="overflow-hidden bg-slate-900/40 rounded-2xl border border-slate-800 transition-all hover:border-slate-700">
                  {/* Parent Header */}
                  <div 
                    onClick={() => toggleParent(group.parent)}
                    className="flex items-center justify-between p-5 cursor-pointer hover:bg-white/5 transition-colors select-none"
                  >
                    <div className="flex items-center gap-4">
                      <div className={cn("p-2.5 rounded-xl border transition-colors", 
                        group.parent_type === 'Position' ? "bg-amber-500/10 border-amber-500/30" : "bg-indigo-600/20 border-indigo-500/30"
                      )}>
                        <Layers className={cn("w-5 h-5", 
                          group.parent_type === 'Position' ? "text-amber-500" : "text-indigo-400"
                        )} />
                      </div>
                      <div>
                        <h4 className="text-lg font-bold text-white tracking-tight">{group.parent}</h4>
                        <p className="text-xs text-slate-500 mt-0.5">Bao gồm {group.children.length} thành phần con</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className={cn("text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest border", label.class)}>
                        {label.text}
                      </span>
                      {isExpanded ? <ChevronUp className="w-5 h-5 text-slate-500" /> : <ChevronDown className="w-5 h-5 text-slate-500" />}
                    </div>
                  </div>

                  {/* Children List (Expanded) */}
                  {isExpanded && (
                    <div className="px-5 pb-5 border-t border-slate-800/50 pt-4 animate-in slide-in-from-top-2 duration-300">
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {group.children.map((child, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-slate-950 rounded-xl border border-slate-800 group/child">
                            <div className="flex items-center gap-3">
                              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]" />
                              <span className="text-sm font-semibold text-slate-200">{child.name}</span>
                              <span className="text-[9px] text-slate-600 italic">({child.type})</span>
                            </div>
                            <button 
                              onClick={(e) => { e.stopPropagation(); handleDeleteRel(group.parent, child.name, child.type); }}
                              className="text-slate-700 hover:text-rose-500 transition-colors p-1"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ))}
                        <button 
                          onClick={(e) => { e.stopPropagation(); setLinkData({...linkData, parent: group.parent}); setIsLinkModalOpen(true); }}
                          className="flex items-center justify-center p-3 rounded-xl border-2 border-dashed border-slate-800 text-slate-500 hover:text-indigo-400 hover:border-indigo-500/30 transition-all text-xs font-bold gap-2"
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
              <div className="p-20 text-center border-2 border-dashed border-slate-800 rounded-3xl opacity-50">
                 <Network className="w-12 h-12 mx-auto mb-4 text-slate-700" />
                 <p className="text-slate-500 font-medium italic">Chưa có kĩ năng cha nào được thiết lập quan hệ.</p>
              </div>
            )}
          </div>
        </div>

        {/* NOTIFICATION TOAST */}
        {notification && (
          <div className={cn(
            "fixed bottom-10 right-10 flex items-center gap-4 px-8 py-4 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] border backdrop-blur-xl animate-in slide-in-from-right-full duration-500 z-[100]",
            notification.type === 'success' ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-rose-500/10 border-rose-500/20 text-rose-400"
          )}>
            <div className={cn("p-2 rounded-lg", notification.type === 'success' ? "bg-emerald-500/20" : "bg-rose-500/20")}>
              {notification.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
            </div>
            <span className="font-bold tracking-tight">{notification.message}</span>
          </div>
        )}

        {/* LINK MODAL */}
        {isLinkModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-lg p-6 animate-in fade-in">
            <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden">
              <div className="p-8 border-b border-slate-800 bg-amber-500/5">
                <h3 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
                  <Network className="w-6 h-6 text-amber-500" /> Thiết lập Quan hệ Graph
                </h3>
              </div>
              <div className="p-8 space-y-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Kỹ năng CHA (Nhóm chính)</label>
                  <input 
                    type="text" 
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-5 py-4 text-white font-bold outline-none focus:ring-2 focus:ring-amber-500/50 shadow-inner"
                    placeholder="e.g. Backend Developer"
                    value={linkData.parent}
                    onChange={(e) => setLinkData({...linkData, parent: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Kỹ năng CON (Thành phần)</label>
                  <input 
                    type="text" 
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-5 py-4 text-white font-bold outline-none focus:ring-2 focus:ring-amber-500/50 shadow-inner"
                    placeholder="e.g. PostgreSQL"
                    value={linkData.child}
                    onChange={(e) => setLinkData({...linkData, child: e.target.value})}
                  />
                </div>
              </div>
              <div className="p-8 bg-slate-800/20 flex justify-end gap-4">
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

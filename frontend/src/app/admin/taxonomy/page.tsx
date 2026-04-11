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
      <div className="space-y-8 animate-in fade-in duration-500">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
              <BookOpen className="text-indigo-500 w-8 h-8" /> Từ điển Thực thể Kỹ thuật
            </h1>
            <p className="text-slate-400">Quản lý cách AI chuẩn hóa các thuật ngữ, kỹ năng và vị trí chuyên môn.</p>
          </div>
          <button 
            onClick={() => { setCurrentSkill({ name: "", category: "Technology", aliases: [] }); setIsSkillModalOpen(true); }}
            className="flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl font-black shadow-lg shadow-indigo-600/20 transition-all active:scale-95"
          >
            <Plus className="w-4 h-4" /> Thêm ánh xạ mới
          </button>
        </div>

        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row gap-4 items-stretch sm:items-center bg-slate-900/50 p-5 rounded-2xl border border-slate-800 backdrop-blur-sm">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input 
                type="text" 
                placeholder="Tìm từ đồng nghĩa hoặc thuật ngữ chính..." 
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-12 pr-4 py-3 text-sm focus:ring-2 focus:ring-indigo-500/50 outline-none"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <button onClick={fetchSkills} className="p-3 bg-slate-800 hover:bg-slate-700 rounded-xl text-slate-300 transition-colors flex items-center justify-center">
              <RefreshCcw className={cn("w-5 h-5", loading && "animate-spin")} />
            </button>
          </div>

          <div className="overflow-hidden bg-slate-900/40 rounded-2xl border border-slate-800 backdrop-blur-md shadow-2xl">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-500 text-[10px] uppercase font-bold tracking-widest">
                  <th className="px-8 py-5">Cách diễn đạt / Từ đồng nghĩa (Aliases)</th>
                  <th className="px-8 py-5 text-center w-20"></th>
                  <th className="px-8 py-5">Thực thể chính (Reference Entity)</th>
                  <th className="px-8 py-5 text-right w-24">Sửa</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 text-slate-300">
                {filteredSkills.map((s) => (
                  <tr key={s.name} className="hover:bg-indigo-500/5 transition-all group">
                    <td className="px-8 py-6">
                      <div className="flex flex-wrap gap-2">
                        {s.aliases?.length > 0 ? (
                          s.aliases.map(a => (
                            <span key={a} className="flex items-center gap-2 bg-slate-950 text-indigo-300 border border-indigo-500/10 px-3 py-1.5 rounded-lg text-xs font-semibold">
                              <Tag className="w-3.5 h-3.5 text-indigo-500/50" /> {a}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-600 italic text-sm">Chưa có alias</span>
                        )}
                      </div>
                    </td>
                    <td className="px-8 py-6 text-center text-slate-700 group-hover:text-indigo-500">
                      <ArrowRight className="w-5 h-5 mx-auto transition-transform group-hover:translate-x-1" />
                    </td>
                    <td className="px-8 py-6">
                      <span className="font-bold text-white text-lg tracking-tight group-hover:text-indigo-400">{s.name}</span>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] text-slate-500 uppercase font-black">{s.category}</span>
                        <span className="w-1 h-1 rounded-full bg-slate-700"></span>
                        <span className="text-[10px] text-indigo-500/70 font-bold uppercase">ENTITY</span>
                      </div>
                    </td>
                    <td className="px-8 py-6 text-right">
                      <button 
                        onClick={() => { setCurrentSkill(s); setIsSkillModalOpen(true); }} 
                        className="p-2.5 bg-slate-800/50 hover:bg-indigo-600 rounded-lg text-slate-400 hover:text-white transition-all shadow-sm"
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
            "fixed bottom-10 right-10 flex items-center gap-4 px-8 py-4 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] border backdrop-blur-xl animate-in slide-in-from-right-full duration-500 z-[100]",
            notification.type === 'success' ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-rose-500/10 border-rose-500/20 text-rose-400"
          )}>
            <div className={cn("p-2 rounded-lg", notification.type === 'success' ? "bg-emerald-500/20" : "bg-rose-500/20")}>
              {notification.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
            </div>
            <span className="font-bold tracking-tight">{notification.message}</span>
          </div>
        )}

        {/* MODAL */}
        {isSkillModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-lg p-6 animate-in fade-in duration-300">
            <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
              <div className="p-8 border-b border-slate-800 bg-slate-900/50">
                <h3 className="text-2xl font-bold text-white tracking-tight">Cấu hình Ánh xạ Thực thể</h3>
              </div>
              <div className="p-8 space-y-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Tên chuẩn (English / AI ID)</label>
                  <input 
                    type="text" 
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-5 py-3.5 text-white font-bold outline-none focus:ring-2 focus:ring-indigo-500/50 shadow-inner"
                    placeholder="e.g. React.js"
                    value={currentSkill.name}
                    onChange={(e) => setCurrentSkill({...currentSkill, name: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Bí danh (Aliases - Cách nhau bằng dấu phẩy)</label>
                  <textarea 
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-5 py-4 text-white text-sm h-32 outline-none focus:ring-2 focus:ring-indigo-500/50 shadow-inner resize-none"
                    placeholder="e.g. Lập trình React, UI Development, ReactJS"
                    value={currentSkill.aliases?.join(", ")}
                    onChange={(e) => setCurrentSkill({...currentSkill, aliases: e.target.value.split(",").map(a => a.trim()).filter(a => a !== "")})}
                  />
                  <p className="text-[10px] text-slate-600 px-1 mt-1">Các chuỗi này khi xuất hiện trong CV/Job desc sẽ được AI map về tên chuẩn ở trên.</p>
                </div>
              </div>
              <div className="p-8 bg-slate-800/20 flex justify-end gap-4">
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

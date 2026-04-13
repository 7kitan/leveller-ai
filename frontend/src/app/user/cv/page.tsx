"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { 
  Upload, FileText, CheckCircle2, Loader2, AlertCircle, 
  User, Briefcase, Sparkles, ArrowRight, RefreshCcw,
  Clock, History, Eye, Trash2, ShieldCheck, ChevronRight,
  Edit2, Plus, Save, X, Trash
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import Link from "next/link";

interface Skill {
  id: string;
  skill_id: string;
  name: string;
  category: string;
  years_exp: number;
  level: string;
}

interface CVData {
  id: string;
  full_name: string;
  summary: string;
  experience_years_total: number;
  status: string;
  error_message: string | null;
  skills: Skill[];
}

interface CVListItem {
  id: string;
  full_name: string | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

export default function UserCVPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [cvId, setCvId] = useState<string | null>(null);
  const [cvData, setCvData] = useState<CVData | null>(null);
  const [cvList, setCvList] = useState<CVListItem[]>([]);
  const [status, setStatus] = useState<"idle" | "uploading" | "processing" | "completed" | "error">("idle");
  const [error, setError] = useState("");
  
  // Edit states
  const [isEditing, setIsEditing] = useState(false);
  const [editTotalExp, setEditTotalExp] = useState<number>(0);
  const [newSkill, setNewSkill] = useState({ name: "", years_exp: 0, level: "Mid-level" });
  const [isAddingSkill, setIsAddingSkill] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const { token } = useAuth();
  const API_BASE = "/api/cv";

  useEffect(() => {
    if (token) {
      fetchCVList();
    }
  }, [token]);

  const fetchCVList = async () => {
    try {
      const res = await axios.get(`${API_BASE}/list`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      setCvList(res.data);
    } catch (err) {
      console.error("Lỗi lấy danh sách CV:", err);
    }
  };

  const handleUpdateTotalExp = async () => {
    if (!cvData) return;
    setSaving(true);
    try {
      await axios.patch(`${API_BASE}/${cvData.id}`, {
        experience_years_total: editTotalExp
      }, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      await fetchCVDetail(cvData.id);
      setIsEditing(false);
    } catch (err) {
      console.error("Lỗi cập nhật kinh nghiệm:", err);
      alert("Không thể cập nhật kinh nghiệm.");
    } finally {
      setSaving(false);
    }
  };

  const handleAddSkill = async () => {
    if (!cvData || !newSkill.name) return;
    setSaving(true);
    try {
      await axios.post(`${API_BASE}/${cvData.id}/skills`, {
        skill_name: newSkill.name,
        years_exp: newSkill.years_exp,
        level: newSkill.level
      }, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      await fetchCVDetail(cvData.id);
      setNewSkill({ name: "", years_exp: 0, level: "Mid-level" });
      setIsAddingSkill(false);
    } catch (err) {
      console.error("Lỗi thêm kỹ năng:", err);
      alert("Không thể thêm kỹ năng.");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSkill = async (profileId: string) => {
    if (!cvData || !confirm("Bạn có chắc chắn muốn xóa kỹ năng này?")) return;
    setSaving(true);
    try {
      await axios.delete(`${API_BASE}/${cvData.id}/skills/${profileId}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      await fetchCVDetail(cvData.id);
    } catch (err) {
      console.error("Lỗi xóa kỹ năng:", err);
      alert("Không thể xóa kỹ năng.");
    } finally {
      setSaving(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError("");
      setStatus("idle");
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setStatus("uploading");
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post(`${API_BASE}/upload`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
          "Authorization": `Bearer ${token}`
        }
      });
      
      const { cv_id, status: serverStatus } = res.data;
      setCvId(cv_id);
      
      if (serverStatus === "completed") {
        setStatus("completed");
        fetchCVDetail(cv_id);
        fetchCVList();
      } else {
        setStatus("processing");
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Lỗi upload CV. Vui lòng thử lại.");
      setStatus("error");
    } finally {
      setUploading(false);
    }
  };

  const fetchCVDetail = async (id: string) => {
    try {
      const res = await axios.get(`${API_BASE}/${id}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.data.status === "completed") {
        setCvData(res.data);
        setStatus("completed");
        fetchCVList();
      } else if (res.data.status === "failed") {
        setCvData(res.data);
        setStatus("idle");
        setError(res.data.error_message || "Xử lý CV thất bại.");
        fetchCVList();
      }
      return res.data;
    } catch (err) {
      console.error("Lỗi lấy chi tiết CV:", err);
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (status === "processing" && cvId) {
      interval = setInterval(async () => {
        const data = await fetchCVDetail(cvId);
        if (data && data.status === "completed") {
          clearInterval(interval);
        }
      }, 3000);
    }
    return () => { if (interval) clearInterval(interval); };
  }, [status, cvId]);

  const reset = () => {
    setFile(null);
    setCvId(null);
    setCvData(null);
    setStatus("idle");
    setError("");
    setIsEditing(false);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('vi-VN', { 
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  };

  return (
    <div className="space-y-10 animate-in fade-in duration-700">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-white/5">
        <div>
          <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-3">
             <FileText className="text-cyan-400 w-8 h-8" /> Portfolio & CVs
          </h1>
          <p className="text-white/40 font-medium mt-1">Quản lý các bản hồ sơ và dữ liệu kỹ năng đã được AI chuẩn hóa.</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-[10px] font-black uppercase tracking-widest text-emerald-400">Dữ liệu được bảo mật</span>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {status === "idle" || status === "uploading" || status === "error" ? (
          <motion.div 
            key="upload-view"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-8"
          >
            {/* Left: Upload Zone */}
            <div className="lg:col-span-2 space-y-6">
              <div className="glass-panel p-10 border-white/5 hover:border-cyan-500/30 transition-all group relative overflow-hidden">
                <div className="absolute top-[-20%] left-[-10%] w-64 h-64 bg-cyan-500/5 blur-[80px] rounded-full pointer-events-none group-hover:bg-cyan-500/10"></div>
                
                <div className="relative z-10 flex flex-col items-center justify-center text-center space-y-6">
                  <div 
                    className={`w-full group relative flex flex-col items-center justify-center rounded-3xl border-2 border-dashed transition-all p-16 
                      ${file ? 'border-cyan-500/50 bg-cyan-500/5' : 'border-white/10 hover:border-cyan-500/30 hover:bg-white/5'}`}
                  >
                    <input 
                      type="file" 
                      accept=".pdf,.png,.jpg,.jpeg,.webp,.bmp" 
                      className="absolute inset-0 cursor-pointer opacity-0"
                      onChange={handleFileChange}
                    />
                    <div className={`p-5 rounded-2xl mb-4 transition-transform group-hover:scale-110 group-hover:rotate-6 ${file ? 'bg-cyan-500/20 text-cyan-400' : 'bg-white/5 text-slate-500'}`}>
                      <Upload className="h-10 w-10" />
                    </div>
                    <h3 className="text-xl font-bold text-white">
                      {file ? file.name : "Tải lên hồ sơ nghề nghiệp"}
                    </h3>
                    <p className="text-sm text-white/30 font-medium mt-2">PDF hoặc Ảnh (PNG, JPG, ...). Tối đa 10MB.</p>
                  </div>

                  {error && (
                    <div className="flex items-center text-rose-400 text-xs font-bold bg-rose-500/10 p-4 rounded-xl border border-rose-500/20 w-full">
                      <AlertCircle className="h-4 w-4 mr-2" /> {error}
                    </div>
                  )}

                  <button
                    onClick={handleUpload}
                    disabled={!file || status === "uploading"}
                    className="flex w-full items-center justify-center gap-3 rounded-2xl bg-cyan-600 py-5 font-black text-xs uppercase tracking-[0.2em] text-white transition-all hover:bg-cyan-500 disabled:opacity-50 shadow-xl shadow-cyan-900/20"
                  >
                    {status === "uploading" ? <Loader2 className="h-5 v-5 animate-spin" /> : <Sparkles className="h-5 v-5" />}
                    {status === "uploading" ? "Đang xử lý..." : "Bắt đầu Phân tích CV qua AI"}
                  </button>
                </div>
              </div>
            </div>

            {/* Right: History Sidebar Style */}
            <div className="space-y-6">
              <h3 className="text-sm font-black uppercase tracking-widest text-white/30 flex items-center gap-2">
                <History className="w-4 h-4" /> Lịch sử hồ sơ
              </h3>
              <div className="space-y-3">
                {cvList.length > 0 ? (
                  cvList.map((item) => (
                    <div 
                      key={item.id}
                      className="glass-panel p-4 flex items-center justify-between border-white/5 hover:bg-white/5 transition-all cursor-pointer group"
                      onClick={() => {
                        setCvId(item.id);
                        if (item.status === 'completed') fetchCVDetail(item.id);
                        else setStatus('processing');
                      }}
                    >
                      <div className="flex items-center gap-3 truncate">
                        <div className={`h-10 w-10 min-w-[40px] rounded-xl flex items-center justify-center text-xs
                          ${item.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                           {item.status === 'completed' ? <CheckCircle2 className="w-5 h-5" /> : <Loader2 className="w-5 h-5 animate-spin" />}
                        </div>
                        <div className="truncate">
                          <p className="font-bold text-sm text-white truncate group-hover:text-cyan-400 transition-colors uppercase tracking-tight">
                            {item.full_name || "DỮ LIỆU ĐANG QUÉT..."}
                          </p>
                          <p className="text-[10px] text-white/30 font-bold">{formatDate(item.created_at)}</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-white/10 group-hover:text-white transition-all transform group-hover:translate-x-1" />
                    </div>
                  ))
                ) : (
                  <div className="text-center py-12 border border-dashed border-white/5 rounded-2xl opacity-30">
                     <p className="text-[10px] font-black uppercase tracking-widest">Trống</p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        ) : status === "processing" ? (
          <motion.div 
            key="processing-view"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass-panel p-20 text-center space-y-8 border-white/5 bg-white/3"
          >
            <div className="relative mx-auto w-32 h-32">
              <div className="absolute inset-0 rounded-full border-4 border-cyan-500/10 border-t-cyan-500 animate-spin" />
              <div className="absolute inset-6 rounded-full bg-cyan-500/5 flex items-center justify-center">
                <Sparkles className="h-10 w-10 text-cyan-400 animate-pulse" />
              </div>
            </div>
            <div className="max-w-md mx-auto">
              <h3 className="text-2xl font-black text-white tracking-tight">AI đang bóc tách kĩ năng...</h3>
              <p className="text-white/40 mt-4 text-sm font-medium leading-relaxed">
                Lumix AI đang chuẩn hóa hồ sơ của bạn vào Knowledge Graph để tìm ra các vị trí phù hợp nhất trên thị trường.
              </p>
            </div>
            {cvData?.error_message && (
              <div className="max-w-md mx-auto p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm font-bold">
                <AlertCircle className="w-4 h-4 inline mr-2" />
                Lỗi: {cvData.error_message}
              </div>
            )}
            <div className="flex justify-center space-x-3">
               {[0, 1, 2].map(i => (
                 <motion.div 
                  key={i} 
                  animate={{ opacity: [0.2, 1, 0.2] }} 
                  transition={{ repeat: Infinity, duration: 1.5, delay: i * 0.3 }}
                  className="w-2 h-2 rounded-full bg-cyan-500" 
                 />
               ))}
            </div>
          </motion.div>
        ) : (
          <motion.div 
            key="result-view"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-8"
          >
            {/* Result Header */}
            <div className="glass-panel p-10 border-white/10 bg-gradient-to-br from-white/5 to-transparent relative overflow-hidden">
               <div className="absolute bottom-[-20%] right-[-10%] w-[40%] h-[100%] bg-emerald-500/5 blur-[100px] pointer-events-none"></div>
               
               <div className="flex flex-col md:flex-row md:items-center justify-between gap-8 relative z-10">
                 <div className="flex items-center gap-6">
                    <div className="h-24 w-24 rounded-3xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                        <User className="h-12 w-12" />
                    </div>
                    <div>
                        <h2 className="text-4xl font-black text-white tracking-tighter uppercase">{cvData?.full_name || "PROFILE MỚI"}</h2>
                        <div className="flex items-center mt-2 gap-4">
                            {isEditing ? (
                                <div className="flex items-center gap-2">
                                    <input 
                                        type="number" 
                                        step="0.1"
                                        value={editTotalExp}
                                        onChange={(e) => setEditTotalExp(parseFloat(e.target.value))}
                                        className="bg-white/5 border border-white/10 rounded-lg px-3 py-1 text-emerald-400 font-black w-20 outline-none focus:border-emerald-500/50"
                                    />
                                    <span className="text-emerald-400 text-xs font-black uppercase tracking-widest">NĂM KINH NGHIỆM</span>
                                    <button 
                                        onClick={handleUpdateTotalExp}
                                        disabled={saving}
                                        className="p-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg hover:bg-emerald-500/30 transition-all"
                                    >
                                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                    </button>
                                    <button 
                                        onClick={() => setIsEditing(false)}
                                        className="p-1.5 bg-white/5 text-white/40 rounded-lg hover:bg-white/10 transition-all"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                            ) : (
                                <span className="flex items-center gap-2 text-emerald-400 text-xs font-black uppercase tracking-widest">
                                    <Briefcase className="w-4 h-4" /> {cvData?.experience_years_total.toFixed(1)} NĂM KINH NGHIỆM
                                    <button 
                                        onClick={() => {
                                            setEditTotalExp(cvData?.experience_years_total || 0);
                                            setIsEditing(true);
                                        }}
                                        className="ml-2 p-1 hover:bg-white/5 rounded-md transition-all text-white/20 hover:text-white"
                                    >
                                        <Edit2 className="w-3 h-3" />
                                    </button>
                                </span>
                            )}
                            <div className="w-1 h-1 rounded-full bg-white/20"></div>
                            <span className="text-white/40 text-xs font-bold uppercase tracking-widest">Đã chuẩn hóa qua Graph</span>
                        </div>
                    </div>
                 </div>
                 
                 <div className="flex flex-wrap gap-4">
                    <button onClick={reset} className="p-4 rounded-2xl border border-white/5 bg-white/3 text-white/40 hover:text-white transition-all">
                        <RefreshCcw className="h-5 w-5" />
                    </button>
                    <Link 
                        href={`/user/analysis?cv_id=${cvData?.id}`}
                        className="flex items-center gap-3 rounded-2xl bg-emerald-600 px-10 py-4 font-black text-xs uppercase tracking-widest text-white transition-all hover:bg-emerald-500 shadow-2xl shadow-emerald-900/40"
                    >
                        PHÂN TÍCH GAP NGAY <ArrowRight className="h-4 h-4" />
                    </Link>
                 </div>
               </div>

               <div className="mt-10 pt-10 border-t border-white/5">
                 <h4 className="text-[10px] font-black text-white/30 uppercase tracking-[0.3em] mb-4">Mô tả tóm tắt sự nghiệp (AI Generated)</h4>
                 <p className="text-white/60 leading-relaxed text-lg font-medium italic">
                   "{cvData?.summary || "Dữ liệu đang được tổng hợp..."}"
                 </p>
               </div>
            </div>

            {/* Skills Matrix Map */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 glass-panel p-8 border-white/5">
                    <h4 className="flex items-center text-sm font-black uppercase tracking-widest text-white mb-8">
                        <Sparkles className="h-5 w-5 mr-3 text-amber-500" />
                        Ma trận Kỹ năng kĩ thuật
                    </h4>
                    <div className="space-y-8">
                        {["Backend", "Frontend", "Cloud & DevOps", "Mobile", "Database"].map((cat) => {
                            const catSkills = cvData?.skills.filter(s => s.category === cat) || [];
                            if (catSkills.length === 0 && !isAddingSkill) return null;
                            
                            return (
                                <div key={cat} className="space-y-4">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-1 h-4 rounded-full ${
                                            cat === 'Backend' ? 'bg-indigo-500' :
                                            cat === 'Frontend' ? 'bg-pink-500' :
                                            cat === 'Cloud & DevOps' ? 'bg-orange-500' :
                                            cat === 'Mobile' ? 'bg-cyan-500' : 'bg-emerald-500'
                                        }`} />
                                        <h5 className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">{cat}</h5>
                                    </div>
                                    <div className="flex flex-wrap gap-3">
                                        {catSkills.map((skill, idx) => (
                                            <motion.div 
                                                key={idx}
                                                initial={{ opacity: 0, scale: 0.8 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                className={`group/skill relative px-5 py-3 rounded-xl text-[11px] font-black uppercase tracking-wider border transition-all hover:scale-105 cursor-default flex items-center gap-2
                                                    ${cat === 'Backend' ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400' : 
                                                    cat === 'Frontend' ? 'bg-pink-500/10 border-pink-500/20 text-pink-400' :
                                                    cat === 'Cloud & DevOps' ? 'bg-orange-500/10 border-orange-500/20 text-orange-400' :
                                                    'bg-white/5 border-white/10 text-white/50'}`}
                                            >
                                                {skill.name} <span className="opacity-40 font-bold italic">({skill.years_exp}y)</span>
                                                <button 
                                                    onClick={() => handleDeleteSkill(skill.id)}
                                                    className="opacity-0 group-hover/skill:opacity-100 ml-1 p-1 hover:bg-rose-500/20 text-rose-500 rounded transition-all"
                                                >
                                                    <Trash2 className="w-3 h-3" />
                                                </button>
                                            </motion.div>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}

                        {/* Uncategorized or generic */}
                        {cvData?.skills.filter(s => !["Backend", "Frontend", "Cloud & DevOps", "Mobile", "Database"].includes(s.category)).length > 0 && (
                             <div className="space-y-4">
                                <div className="flex items-center gap-3">
                                    <div className="w-1 h-4 rounded-full bg-slate-500" />
                                    <h5 className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">Other Specialist Skills</h5>
                                </div>
                                <div className="flex flex-wrap gap-3">
                                    {cvData?.skills.filter(s => !["Backend", "Frontend", "Cloud & DevOps", "Mobile", "Database"].includes(s.category)).map((skill, idx) => (
                                        <motion.div 
                                            key={idx}
                                            className="group/skill relative px-5 py-3 rounded-xl text-[11px] font-black uppercase tracking-wider border border-white/10 bg-white/5 text-white/50 transition-all hover:scale-105 cursor-default flex items-center gap-2"
                                        >
                                            {skill.name} <span className="opacity-40 font-bold italic">({skill.years_exp}y)</span>
                                            <button 
                                                onClick={() => handleDeleteSkill(skill.id)}
                                                className="opacity-0 group-hover/skill:opacity-100 ml-1 p-1 hover:bg-rose-500/20 text-rose-500 rounded transition-all"
                                            >
                                                <Trash2 className="w-3 h-3" />
                                            </button>
                                        </motion.div>
                                    ))}
                                </div>
                             </div>
                        )}

                        <div className="pt-6 border-t border-white/5">
                            {isAddingSkill ? (
                                <motion.div 
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-xl px-4 py-2 w-fit"
                                >
                                    <input 
                                        placeholder="Skill Name..." 
                                        value={newSkill.name}
                                        onChange={e => setNewSkill({...newSkill, name: e.target.value})}
                                        className="bg-transparent border-none outline-none text-[11px] font-black uppercase w-32 text-white"
                                    />
                                    <input 
                                        type="number" 
                                        placeholder="Yrs" 
                                        value={newSkill.years_exp || ""}
                                        onChange={e => setNewSkill({...newSkill, years_exp: parseFloat(e.target.value) || 0})}
                                        className="bg-transparent border-none outline-none text-[11px] font-black w-10 text-cyan-400"
                                    />
                                    <button onClick={handleAddSkill} disabled={saving} className="text-emerald-400 hover:text-emerald-300">
                                        {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                                    </button>
                                    <button onClick={() => setIsAddingSkill(false)} className="text-white/40 hover:text-white">
                                        <X className="w-4 h-4" />
                                    </button>
                                </motion.div>
                            ) : (
                                <button 
                                    onClick={() => setIsAddingSkill(true)}
                                    className="px-5 py-3 rounded-xl text-[11px] font-black uppercase tracking-wider border border-white/5 bg-white/3 text-white/40 hover:text-white hover:bg-white/10 transition-all flex items-center gap-2"
                                >
                                    <Plus className="w-3 h-3" /> Bổ sung kỹ năng
                                </button>
                            )}
                        </div>
                    </div>
                </div>
                
                <div className="glass-panel p-10 border-white/5 bg-gradient-to-t from-cyan-500/5 to-transparent flex flex-col items-center justify-center text-center space-y-6">
                    <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 flex items-center justify-center text-cyan-400 border border-cyan-500/20">
                        <CheckCircle2 className="w-8 h-8" />
                    </div>
                    <div>
                        <h4 className="text-lg font-black text-white uppercase tracking-tighter">Graph Verified</h4>
                        <p className="text-white/30 text-xs font-bold leading-relaxed mt-2 uppercase tracking-wide">
                            Bộ kỹ năng đã được liên kết với Metadata Graph để tối ưu hóa việc gợi ý lộ trình học tập.
                        </p>
                    </div>
                </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

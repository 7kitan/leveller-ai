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
  BarChart3,
  Mail,
  Filter
} from "lucide-react";
import { format } from "date-fns";
import toast from "react-hot-toast";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";

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
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-black uppercase tracking-widest rounded-lg"><CheckCircle2 size={12}/> Ready</span>;
      case "processing":
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-500/10 border border-amber-500/20 text-amber-500 text-[10px] font-black uppercase tracking-widest rounded-lg animate-pulse"><Clock size={12}/> Analyzing</span>;
      case "failed":
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] font-black uppercase tracking-widest rounded-lg"><AlertCircle size={12}/> Error</span>;
      default:
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/5 border border-white/10 text-white/40 text-[10px] font-black uppercase tracking-widest rounded-lg">{status}</span>;
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center gap-3 text-indigo-400 font-black text-xs uppercase tracking-[0.3em] mb-2">
            <FileText size={14} /> Data Repository
          </div>
          <h1 className="text-4xl font-black text-white tracking-tighter">CV Repository</h1>
          <p className="text-white/40 font-medium tracking-tight">Giám sát và quản lý dữ liệu hồ sơ toàn hệ thống.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <button 
            onClick={fetchCVs}
            className="px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-2xl text-sm font-bold text-white transition-all flex items-center gap-2"
          >
            <RefreshCcw size={18} className={loading ? "animate-spin" : ""} /> Sync Data
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white/3 border border-white/5 rounded-3xl p-6 backdrop-blur-xl">
          <div className="text-white/30 text-xs font-black uppercase tracking-widest mb-4">Tổng hồ sơ</div>
          <div className="text-3xl font-black text-white">{cvs.length}</div>
        </div>
        <div className="bg-white/3 border border-white/5 rounded-3xl p-6 backdrop-blur-xl">
          <div className="text-white/30 text-xs font-black uppercase tracking-widest mb-4">Đã bóc tách</div>
          <div className="text-3xl font-black text-emerald-400">{cvs.filter(c => c.status === "completed").length}</div>
        </div>
        <div className="bg-white/3 border border-white/5 rounded-3xl p-6 backdrop-blur-xl">
          <div className="text-white/30 text-xs font-black uppercase tracking-widest mb-4">Đang xử lý</div>
          <div className="text-3xl font-black text-amber-400">{cvs.filter(c => c.status === "processing").length}</div>
        </div>
        <div className="bg-white/3 border border-white/5 rounded-3xl p-6 backdrop-blur-xl">
          <div className="text-white/30 text-xs font-black uppercase tracking-widest mb-4">Lỗi AI</div>
          <div className="text-3xl font-black text-red-500">{cvs.filter(c => c.status === "failed").length}</div>
        </div>
      </div>

      {/* Control Bar */}
      <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-white/3 border border-white/5 p-4 rounded-[2rem] backdrop-blur-xl transition-all">
        <div className="relative w-full md:w-96 group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20 group-focus-within:text-indigo-500 transition-colors" size={18} />
          <input 
            type="text"
            placeholder="Tìm kiếm theo email, tên ứng viên..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 transition-all"
          />
        </div>
        <div className="flex items-center gap-3">
           <div className="flex bg-white/5 rounded-2xl p-1 border border-white/10">
              {["all", "completed", "processing", "failed"].map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
                    statusFilter === s ? "bg-indigo-600 text-white shadow-lg" : "text-white/30 hover:text-white/60"
                  }`}
                >
                  {s}
                </button>
              ))}
           </div>
        </div>
      </div>

      {/* CVs Table */}
      <div className="bg-white/3 border border-white/5 rounded-[2.5rem] overflow-hidden backdrop-blur-xl relative">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/5">
                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">Candidate</th>
                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">Email Owner</th>
                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">Status</th>
                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">System ID</th>
                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">Uploaded</th>
                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-[0.2em] text-white/30 text-right">Actions</th>
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
                  <tr key={cv.id} className="group hover:bg-white/[0.02] transition-colors">
                    <td className="px-8 py-6">
                       <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                             <User size={18} />
                          </div>
                          <div className="text-white font-bold group-hover:text-indigo-400 transition-colors">
                             {cv.full_name || "Untitled CV"}
                          </div>
                       </div>
                    </td>
                    <td className="px-8 py-6">
                       <div className="flex items-center gap-2 text-white/50 text-xs">
                          <Mail size={14} className="opacity-30" />
                          {cv.user_email}
                       </div>
                    </td>
                    <td className="px-8 py-6">
                       {getStatusBadge(cv.status)}
                    </td>
                    <td className="px-8 py-6">
                      <code className="text-[10px] font-mono text-white/30 bg-black/20 px-2 py-1 rounded">
                        {cv.id.substring(0, 8)}...
                      </code>
                    </td>
                    <td className="px-8 py-6">
                      <div className="flex items-center gap-2 text-white/50 text-xs font-medium">
                        <Clock size={14} className="opacity-50" />
                        {format(new Date(cv.created_at), "MMM dd, HH:mm")}
                      </div>
                    </td>
                    <td className="px-8 py-6 text-right">
                       <div className="flex items-center justify-end gap-2">
                          <Link 
                            href={`/user/cv/${cv.id}`}
                            className="p-2 hover:bg-white/10 rounded-lg text-white/20 hover:text-white transition-all"
                            title="View Analysis"
                          >
                            <ExternalLink size={18} />
                          </Link>
                          <button className="p-2 hover:bg-red-500/10 rounded-lg text-white/20 hover:text-red-400 transition-all">
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

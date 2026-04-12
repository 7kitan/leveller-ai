"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { Briefcase, MapPin, Search, Loader2, Info } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";

interface Job {
  id: string;
  title_raw: string;
  status: string;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [location, setLocation] = useState("");
  const [minSalary, setMinSalary] = useState("");
  const [role, setRole] = useState("");
  const { token } = useAuth();

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const res = await axios.get("/api/jd/search", {
        params: {
          search_text: searchTerm || undefined,
          location: location || undefined,
          min_salary: minSalary || undefined,
          role: role || undefined
        },
        headers: { "Authorization": `Bearer ${token}` }
      });
      setJobs(res.data);
    } catch (err) {
      console.error("Lỗi tìm kiếm jobs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);


  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs();
  };


  return (
    <div className="mx-auto max-w-7xl px-6 py-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
        <div>
          <h1 className="text-3xl font-bold text-white">Khám phá Cơ hội</h1>
          <p className="text-gray-400 mt-2">Tìm kiếm và phân tích độ phù hợp với các vị trí hàng đầu</p>
        </div>
        
        <form onSubmit={handleSearch} className="w-full space-y-4">
            <div className="flex flex-col lg:flex-row gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                    <input 
                        type="text"
                        placeholder="Từ khóa (Vị trí, Công ty...)"
                        className="w-full pl-10 pr-4 py-3 glass rounded-xl text-white focus:outline-none focus:ring-1 focus:ring-primary"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                <div className="relative w-full lg:w-48">
                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                    <input 
                        type="text"
                        placeholder="Địa điểm"
                        className="w-full pl-10 pr-4 py-3 glass rounded-xl text-white focus:outline-none focus:ring-1 focus:ring-primary"
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                    />
                </div>
                <div className="relative w-full lg:w-48">
                    <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                    <input 
                        type="text"
                        placeholder="Lương tối thiểu"
                        className="w-full pl-10 pr-4 py-3 glass rounded-xl text-white focus:outline-none focus:ring-1 focus:ring-primary"
                        value={minSalary}
                        onChange={(e) => setMinSalary(e.target.value)}
                    />
                </div>
                <button 
                    type="submit"
                    className="px-8 py-3 bg-primary hover:bg-primary/80 text-white font-bold rounded-xl transition-all shadow-lg shadow-primary/20"
                >
                    TÌM KIẾM
                </button>
            </div>
        </form>

      </div>

      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-20"
          >
            <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
            <p className="text-gray-400">Đang tải dữ liệu việc làm...</p>
          </motion.div>
        ) : jobs.length > 0 ? (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </motion.div>
        ) : (
          <div className="text-center py-20 glass rounded-2xl">
            <Info className="mx-auto h-12 w-12 text-gray-500 mb-4" />
            <h3 className="text-xl font-semibold text-white">Không tìm thấy công việc nào</h3>
            <p className="text-gray-400 mt-2">Vui lòng quay lại sau hoặc nạp thêm dữ liệu.</p>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

function JobCard({ job }: { job: Job }) {
  return (
    <motion.div 
      whileHover={{ y: -5 }}
      className="glass p-6 rounded-2xl border border-white/5 hover:border-primary/50 transition-all group"
    >
      <div className="flex justify-between items-start mb-4">
        <div className="bg-primary/10 p-3 rounded-xl border border-primary/20">
          <Briefcase className="h-6 w-6 text-primary" />
        </div>
        <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
          job.status === "active" ? "bg-green-500/10 text-green-400" : "bg-yellow-500/10 text-yellow-400"
        }`}>
          {job.status}
        </span>
      </div>
      
      <h3 className="text-lg font-bold text-white group-hover:text-primary transition-colors mb-2">
        {job.title_raw}
      </h3>
      
      <div className="flex items-center text-sm text-gray-500 mb-6">
        <MapPin className="h-4 w-4 mr-1" /> Toàn quốc / Remote
      </div>
      
      <Link 
        href={`/user/analysis?job_id=${job.id}`}
        className="block w-full text-center py-3 rounded-xl bg-white/5 hover:bg-white/10 text-sm font-semibold text-white transition-all"
      >
        Phân tích Match
      </Link>
    </motion.div>
  );
}

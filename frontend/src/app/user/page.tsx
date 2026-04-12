"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { 
  Search, 
  UploadCloud, 
  MapPin, 
  Briefcase, 
  Award, 
  TrendingUp, 
  CheckCircle2, 
  Plus,
  ArrowRight,
  Sparkles,
  BarChart3,
  Flame,
  LineChart
} from "lucide-react";
import Link from "next/link";

const UserDashboard = () => {
  const { token } = useAuth();
  const [isUploading, setIsUploading] = useState(false);
  const [marketData, setMarketData] = useState<any>(null);
  const [loadingMarket, setLoadingMarket] = useState(true);

  useEffect(() => {
    const fetchMarketFit = async () => {
       try {
         const res = await axios.get("/api/analysis/market-fit", { 
           headers: { Authorization: `Bearer ${token}` }
         });
         setMarketData(res.data);
       } catch (err) {
         console.error("Market Fit error:", err);
       } finally {
         setLoadingMarket(false);
       }
    };
    if (token) fetchMarketFit();
  }, [token]);


  const matchedJobs = [
    { id: 1, title: "Senior Backend Engineer", company: "Aura Tech", location: "Hồ Chí Minh", match: "92%", skills: ["FastAPI", "Neo4j", "Docker"] },
    { id: 2, title: "DevOps Architect", company: "Cloud Nexus", location: "Hà Nội", match: "85%", skills: ["Kubernetes", "AWS", "Terraform"] },
    { id: 3, title: "Fullstack Developer", company: "Nexus AI", location: "Remote", match: "78%", skills: ["Next.js", "Python", "Redis"] },
  ];

  const stats = [
    { label: "Jobs Matched", value: loadingMarket ? "..." : (marketData?.matched_jobs || "0"), icon: Target, color: "text-cyan-400" },
    { label: "Market Fit Ratio", value: loadingMarket ? "..." : `${marketData?.market_fit_pct || 0}%`, icon: TrendingUp, color: "text-emerald-400" },
    { label: "Database Coverage", value: loadingMarket ? "..." : (marketData?.total_jobs || "0"), icon: Award, color: "text-rose-400" },
  ];


  return (
    <AuthGuard requireRole="user">
      <div className="space-y-12 pb-20">
        {/* Header & CV Upload */}
        <div className="flex flex-col lg:flex-row gap-8 items-start justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl md:text-5xl font-black text-white tracking-tighter">User Hub.</h1>
            <p className="text-white/40 font-medium text-lg max-w-lg">Giải mã khoảng trống kỹ năng và kết nối với cơ hội tương xứng.</p>
          </div>
          
          <div className="w-full lg:max-w-md glass-panel p-8 group border-cyan-500/20 hover:border-cyan-500/40 relative overflow-hidden transition-all">
             <div className="absolute top-[-20%] right-[-10%] w-32 h-32 bg-cyan-500/10 blur-[60px] rounded-full pointer-events-none group-hover:bg-cyan-500/20"></div>
             <div className="flex flex-col items-center justify-center space-y-4 relative z-10">
                <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 flex items-center justify-center text-cyan-400 group-hover:scale-110 group-hover:rotate-6 transition-all duration-500">
                    <UploadCloud className="w-8 h-8" />
                </div>
                <div className="text-center">
                    <h3 className="text-lg font-bold text-white mb-1">Cập nhật CV mới nhất</h3>
                    <p className="text-xs text-white/30 font-medium">Kéo thả hoặc bấm để upload file (PDF hoặc Ảnh)</p>
                </div>
                <Link 
                  href="/user/cv"
                  className="w-full py-3 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl font-black text-xs uppercase tracking-widest transition-all shadow-lg shadow-cyan-900/40 text-center"
                >
                  TẢI LÊN CV & PHÂN TÍCH
                </Link>
             </div>
          </div>
        </div>

        {/* Stats Section */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {stats.map((stat) => (
            <div key={stat.label} className="glass-panel p-8 group bg-white/3">
              <div className="flex items-center justify-between mb-6">
                <stat.icon className={`w-8 h-8 ${stat.color} group-hover:rotate-12 transition-transform`} />
                <BarChart3 className="w-4 h-4 text-white/10" />
              </div>
              <div className="text-4xl font-black text-white mb-1">{stat.value}</div>
              <div className="text-xs font-black uppercase tracking-widest text-white/30">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Main Jobs Section */}
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-black text-white flex items-center gap-3">
                    <Flame className="w-6 h-6 text-rose-500" /> Hot Job Matches
                </h2>
                <Link href="/user/jobs" className="text-xs font-black uppercase tracking-widest text-[#60efff] hover:text-white transition-colors">Xem tất cả</Link>
            </div>

            <div className="grid grid-cols-1 gap-4">
                {matchedJobs.map((job) => (
                    <div key={job.id} className="glass-panel p-1 group relative flex flex-col md:flex-row items-stretch md:items-center gap-6 hover:bg-white/5 border-white/5">
                         <div className="md:w-32 bg-white/5 rounded-2xl flex flex-col items-center justify-center p-6 border-r border-white/5">
                             <div className="text-2xl font-black text-cyan-400">{job.match}</div>
                             <div className="text-[10px] font-black uppercase tracking-widest text-white/30">MATCH</div>
                         </div>
                         
                         <div className="flex-1 p-6 md:py-0">
                            <h3 className="text-xl font-bold text-white mb-2">{job.title}</h3>
                            <div className="flex flex-wrap gap-4 text-sm text-white/50 mb-4">
                                <span className="flex items-center gap-2 font-medium"><Briefcase className="w-4 h-4 text-white/20" /> {job.company}</span>
                                <span className="flex items-center gap-2 font-medium"><MapPin className="w-4 h-4 text-white/20" /> {job.location}</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {job.skills.map(s => (
                                    <span key={s} className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] font-bold text-white/60 uppercase tracking-wider">{s}</span>
                                ))}
                            </div>
                         </div>
                         
                         <div className="p-6 md:pr-10">
                            <Link 
                                href="/user/analysis"
                                className="px-8 py-3 bg-white/5 hover:bg-violet-600 border border-white/10 hover:border-violet-500 text-white rounded-xl font-bold text-sm transition-all flex items-center gap-3 decoration-none outline-none group-hover:shadow-[0_0_20px_rgba(139,92,246,0.3)]"
                            >
                                GAP ANALYSIS <ArrowRight className="w-4 h-4" />
                            </Link>
                         </div>
                    </div>
                ))}
            </div>
        </div>

        {/* Gap Analysis Illustration/Shortcut */}
        <div className="glass-panel p-12 bg-[#0a0b1e] border-violet-500/20 relative overflow-hidden group">
            <div className="absolute top-[-30%] left-[-10%] w-[40%] h-[150%] bg-violet-600/10 blur-[100px] skew-x-12 rotate-[-45deg] animate-pulse"></div>
            
            {/* Background Radar Scanning Effect */}
            <div className="absolute right-[-10%] top-[-10%] w-[500px] h-[500px] pointer-events-none opacity-20">
                <div className="absolute inset-0 border border-violet-500/30 rounded-full animate-ping [animation-duration:4s]"></div>
                <div className="absolute inset-20 border border-cyan-500/20 rounded-full animate-ping [animation-duration:6s]"></div>
                <div className="absolute inset-40 border border-violet-500/10 rounded-full animate-ping [animation-duration:8s]"></div>
            </div>

            <div className="flex flex-col lg:flex-row items-center gap-12 relative z-10">
                <div className="flex-1 space-y-6">
                    <div className="inline-flex gap-2 text-violet-400 font-black text-xs uppercase tracking-widest bg-violet-500/10 px-4 py-2 rounded-full border border-violet-500/20">
                        <Sparkles className="w-4 h-4" /> AI Powered Gap Engine
                    </div>
                    <h2 className="text-3xl md:text-4xl font-black text-white tracking-tight">Thấu hiểu điểm mạnh, làm chủ lộ trình.</h2>
                    <p className="text-white/40 font-medium leading-relaxed max-w-xl">
                        Công cụ Gap Analysis của Lumix AI so sánh hàng nghìn tham số giữa hồ sơ của bạn và yêu cầu thực tế từ thị trường để gợi ý các kỹ năng "chốt hạ" giúp bạn nhận việc. 
                        {marketData?.top_matching_roles?.length > 0 && (
                            <span className="block mt-4 text-emerald-400 text-sm font-bold italic">
                                Vai trò phù hợp nhất: {marketData.top_matching_roles.join(", ")}
                            </span>
                        )}
                    </p>
                    <Link 
                        href="/user/analysis"
                        className="group flex px-8 py-4 bg-violet-600 hover:bg-violet-500 text-white rounded-2xl font-black text-md transition-all items-center gap-3 w-fit shadow-[0_20px_40px_rgba(139,92,246,0.3)]"
                    >
                        Thử phân tích ngay <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </Link>
                </div>
                
                <div className="w-full lg:w-1/2 aspect-square max-w-[400px] relative">
                    {/* Visual Radar Mockup Interface - Enhanced */}
                    <div className="absolute inset-0 rounded-full border-[1px] border-white/5 bg-white/2 backdrop-blur-xl"></div>
                    
                    {/* Pulsing Concentric Circles */}
                    <div className="absolute inset-4 rounded-full border border-white/5"></div>
                    <div className="absolute inset-12 rounded-full border border-white/5"></div>
                    <div className="absolute inset-24 rounded-full border border-white/5"></div>
                    
                    {/* Rotating Scanner Line */}
                    <div className="absolute inset-0 rounded-full animate-spin [animation-duration:4s] border-r-2 border-violet-500/40 bg-gradient-to-r from-transparent via-transparent to-violet-500/5"></div>
                    
                    {/* Floating Skill Points */}
                    <div className="absolute top-[20%] left-[30%] w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_10px_#22d3ee] animate-pulse"></div>
                    <div className="absolute top-[40%] right-[25%] w-2 h-2 rounded-full bg-violet-400 shadow-[0_0_10px_#a78bfa] animate-pulse [animation-delay:1s]"></div>
                    <div className="absolute bottom-[30%] left-[40%] w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_10px_#34d399] animate-pulse [animation-delay:2s]"></div>
                    
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="relative">
                            <div className="absolute inset-0 bg-violet-500/20 blur-2xl rounded-full"></div>
                            <LineChart className="w-20 h-20 text-white/80 relative z-10" />
                        </div>
                    </div>
                    
                    {/* Status Tags */}
                    <div className="absolute top-0 right-0 bg-white/5 backdrop-blur-md border border-white/10 px-3 py-1 rounded-lg text-[8px] font-black text-violet-400 uppercase tracking-widest">Scanning...</div>
                    <div className="absolute bottom-0 left-0 bg-white/5 backdrop-blur-md border border-white/10 px-3 py-1 rounded-lg text-[8px] font-black text-cyan-400 uppercase tracking-widest">Matched 92%</div>
                </div>
            </div>
        </div>
      </div>
    </AuthGuard>
  );
};

const Target = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
  </svg>
);

const ChevronRight = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m9 18 6-6-6-6"/>
  </svg>
);

export default UserDashboard;

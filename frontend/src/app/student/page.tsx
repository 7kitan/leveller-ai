"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { 
  GraduationCap, 
  Search, 
  Map, 
  BookOpen, 
  Star, 
  Clock, 
  Trophy, 
  Cpu,
  Layers,
  ArrowUpRight,
  TrendingUp,
  Sparkles,
  MousePointer2,
  CheckCircle2,
} from "lucide-react";

const StudentDashboard = () => {
  const { token } = useAuth();
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
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


  const mySkills = [
    { name: "Python", level: "Intermediate", progress: 65, relatedRoles: ["AI/ML Engineer", "Data Scientist"], courses: ["Advanced Python Patterns", "Data viz with Pandas"] },
    { name: "SQL", level: "Beginner", progress: 40, relatedRoles: ["Backend Developer", "Data Analyst"], courses: ["PostgreSQL Mastery", "Database Design 101"] },
    { name: "HTML/CSS", level: "Advanced", progress: 95, relatedRoles: ["Frontend Developer"], courses: ["Modern Canvas API", "3D Web Graphics"] },
  ];

  const suggestedCourses = [
    { title: "Neo4j for Beginners", instructor: "Graph Academy", duration: "12h", rating: 4.8, complexity: "Intro" },
    { title: "Microservices with FastAPI", instructor: "Tech Nexus", duration: "24h", rating: 4.9, complexity: "Advanced" },
  ];

  return (
    <AuthGuard requireRole="student">
      <div className="space-y-12 pb-20">
        {/* Student Welcome Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-black uppercase tracking-widest rounded-lg animate-pulse">
                <Star className="w-3 h-3" /> Early Career Growth
            </div>
            <h1 className="text-4xl md:text-6xl font-black text-white tracking-tighter leading-none">Your Growth<br/><span className="bg-gradient-to-r from-amber-400 via-yellow-300 to-orange-400 bg-clip-text text-transparent">Nexus.</span></h1>
            <p className="text-white/40 font-medium max-w-md">Lập kế hoạch chinh phục tri thức và lộ trình sự nghiệp hoàn hảo.</p>
          </div>
          
          <div className="flex bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-xl space-x-8">
            <div className="text-center">
                <div className="text-2xl font-black text-white">12</div>
                <div className="text-[10px] font-black uppercase tracking-widest text-white/30">Skills Mastered</div>
            </div>
            <div className="text-center border-l border-white/10 pl-8">
                <div className="text-2xl font-black text-amber-400">
                    {loadingMarket ? "..." : `${marketData?.market_fit_pct || 0}%`}
                </div>
                <div className="text-[10px] font-black uppercase tracking-widest text-white/30">Market Fit Score</div>
            </div>

          </div>
        </div>

        {/* Skill Explorer Section */}
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-black text-white flex items-center gap-3">
                    <Cpu className="w-6 h-6 text-amber-500" /> Skill Compass
                </h2>
                <div className="text-xs text-white/30 italic flex items-center gap-2">
                    <MousePointer2 className="w-3 h-3" /> Bấm vào kỹ năng để xem lộ trình
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {mySkills.map((skill) => (
                    <div 
                      key={skill.name} 
                      onClick={() => setSelectedSkill(selectedSkill === skill.name ? null : skill.name)}
                      className={`glass-panel p-8 cursor-pointer transition-all relative overflow-hidden group ${
                        selectedSkill === skill.name ? "border-amber-500/50 bg-amber-500/5" : "hover:border-white/20"
                      }`}
                    >
                         <div className="flex justify-between items-start mb-10">
                            <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center border border-white/10">
                                <Layers className={`w-6 h-6 ${selectedSkill === skill.name ? "text-amber-400" : "text-white/30"}`} />
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-widest py-1 px-3 bg-white/5 rounded-full text-white/40">{skill.level}</span>
                         </div>
                         
                         <h3 className="text-2xl font-black text-white mb-4 tracking-tight">{skill.name}</h3>
                         
                         <div className="space-y-4">
                            <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-white/30 px-1">
                                <span>Mastery Progress</span>
                                <span>{skill.progress}%</span>
                            </div>
                            <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                                <div 
                                    className="h-full bg-gradient-to-r from-amber-600 to-yellow-400 rounded-full transition-all duration-1000 ease-out"
                                    style={{ width: `${skill.progress}%` }}
                                ></div>
                            </div>
                         </div>

                         {/* Contextual Drill-down overlay */}
                         {selectedSkill === skill.name && (
                             <div className="mt-8 pt-8 border-t border-amber-500/20 space-y-6 animate-in fade-in slide-in-from-top-4 duration-500">
                                <div>
                                    <h4 className="text-[10px] font-black uppercase tracking-widest text-amber-500/60 mb-3">Related Professional Roles</h4>
                                    <div className="flex flex-wrap gap-2">
                                        {skill.relatedRoles.map(role => (
                                            <span key={role} className="px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 text-white text-xs font-bold rounded-lg flex items-center gap-2">
                                                <TrendingUp className="w-3 h-3" /> {role}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                                <div>
                                    <h4 className="text-[10px] font-black uppercase tracking-widest text-amber-500/60 mb-3">Next Step Courses</h4>
                                    <div className="space-y-2">
                                        {skill.courses.map(course => (
                                            <div key={course} className="flex items-center justify-between p-3 bg-white/5 rounded-xl border border-white/5 hover:border-amber-500/20">
                                                <span className="text-sm font-semibold text-white/80">{course}</span>
                                                <ArrowUpRight className="w-4 h-4 text-amber-500" />
                                            </div>
                                        ))}
                                    </div>
                                </div>
                             </div>
                         )}
                    </div>
                ))}
          {/* Suggestion & Roadmap */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
             <div className="lg:col-span-2 space-y-6">
                <h2 className="text-2xl font-black text-white flex items-center gap-3">
                    <BookOpen className="w-6 h-6 text-cyan-500" /> Suggested for Your Gap
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {suggestedCourses.map((course) => (
                        <div key={course.title} className="glass-panel p-6 bg-white/3 border-white/5 hover:bg-white/5 hover:border-cyan-500/30 transition-all flex flex-col justify-between h-[180px] group/course">
                            <div className="relative">
                                <div className="absolute top-0 right-0 w-12 h-12 bg-cyan-500/5 blur-xl group-hover/course:bg-cyan-500/10 transition-colors"></div>
                                <div className="flex justify-between items-start mb-4">
                                    <div className="text-[9px] font-black uppercase tracking-widest px-2 py-1 bg-cyan-500/10 text-cyan-400 rounded border border-cyan-500/20">{course.complexity}</div>
                                    <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                                </div>
                                <h4 className="text-lg font-bold text-white mb-1 group-hover/course:text-cyan-400 transition-colors">{course.title}</h4>
                                <p className="text-xs text-white/30 font-medium">by {course.instructor}</p>
                            </div>
                            <div className="flex items-center justify-between pt-4 border-t border-white/5">
                                <div className="flex items-center gap-2 text-white/40 text-[10px] font-bold">
                                    <Clock className="w-3 h-3" /> {course.duration}
                                </div>
                                <button className="text-cyan-400 text-xs font-black uppercase tracking-widest flex items-center gap-1 hover:text-white transition-colors">
                                    Enroll <ArrowUpRight className="w-3 h-3" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
                
                {/* Learning Sphere Contextual Widget */}
                <div className="glass-panel p-10 bg-gradient-to-br from-[#0c0d21] to-transparent border-cyan-500/20 relative overflow-hidden flex flex-col md:flex-row items-center gap-10">
                    <div className="absolute top-[-50%] right-[-20%] w-[300px] h-[300px] bg-cyan-500/5 blur-[80px] rounded-full animate-pulse"></div>
                    
                    <div className="relative w-48 h-48 shrink-0">
                        {/* Learning Sphere Visual Concept */}
                        <div className="absolute inset-0 rounded-full border border-cyan-500/20 animate-spin [animation-duration:10s]">
                            <div className="absolute top-0 left-1/2 w-2 h-2 bg-cyan-400 rounded-full -translate-x-1/2 -translate-y-1/2 shadow-[0_0_10px_#22d3ee]"></div>
                        </div>
                        <div className="absolute inset-4 rounded-full border border-violet-500/10 animate-spin [animation-duration:15s] [animation-direction:reverse]">
                            <div className="absolute bottom-0 left-1/2 w-2 h-2 bg-violet-400 rounded-full -translate-x-1/2 translate-y-1/2 shadow-[0_0_10px_#a78bfa]"></div>
                        </div>
                        <div className="absolute inset-8 rounded-full bg-gradient-to-br from-cyan-500/20 to-violet-500/20 backdrop-blur-3xl flex items-center justify-center">
                            <Sparkles className="w-12 h-12 text-white/80 animate-pulse" />
                        </div>
                        {/* Floating context bubbles */}
                        <div className="absolute -top-2 -right-2 px-2 py-1 bg-white/5 backdrop-blur-md rounded border border-white/10 text-[8px] font-black text-white/40 uppercase">Memory Graph</div>
                        <div className="absolute -bottom-2 -left-2 px-2 py-1 bg-white/5 backdrop-blur-md rounded border border-white/10 text-[8px] font-black text-white/40 uppercase">Neuro Match</div>
                    </div>
                    
                    <div className="space-y-4">
                        <h3 className="text-2xl font-black text-white tracking-tight uppercase">Cognitive Sync.</h3>
                        <p className="text-white/40 font-medium text-sm leading-relaxed italic">
                            Hệ thống AI đang theo dõi tiến trình học tập của bạn và tự động ánh xạ vào Market Gap để cập nhật chỉ số Market Fit theo thời gian thực.
                        </p>
                        <div className="flex gap-4">
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                                <span className="text-[10px] font-black text-white/60 uppercase tracking-widest">Live Syncing</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-violet-500"></div>
                                <span className="text-[10px] font-black text-white/60 uppercase tracking-widest">Graph Ready</span>
                            </div>
                        </div>
                    </div>
                </div>
             </div>

             <div className="space-y-6">
                <h2 className="text-2xl font-black text-white flex items-center gap-3">
                    <Map className="w-6 h-6 text-violet-500" /> Target Roadmap
                </h2>
                <div className="glass-panel p-8 relative min-h-[480px] bg-[#0c0d21]/50">
                     {/* Floating Glowing Dots logic for path */}
                     <div className="absolute left-[39px] top-12 bottom-12 w-[1px] bg-gradient-to-b from-violet-500/50 via-violet-500/10 to-transparent"></div>
                     <div className="space-y-12 relative">
                        {[
                            { step: "Fundamentals", desc: "Core CS & Language Master", icon: Cpu, completed: true, color: "bg-violet-600 shadow-[0_0_20px_rgba(139,92,246,0.6)]" },
                            { step: "Deep Architecture", desc: "System Design & Microservices", icon: BookOpen, completed: false, color: "bg-white/5 border border-white/10" },
                            { step: "Market Project", desc: "Showcase in Knowledge Graph", icon: Sparkles, completed: false, color: "bg-white/5 border border-white/10" },
                            { step: "Career Entry", desc: "Verified Seeker Match", icon: Trophy, completed: false, color: "bg-white/5 border border-white/10" }
                        ].map((m, idx) => (
                            <div key={idx} className="flex items-start gap-6 relative group/step">
                                <div className={`w-10 h-10 rounded-2xl flex items-center justify-center relative z-10 transition-all group-hover/step:scale-110 ${m.color}`}>
                                    <m.icon className={`w-5 h-5 ${m.completed ? "text-white" : "text-white/20 group-hover/step:text-white/40"}`} />
                                </div>
                                <div className="space-y-1">
                                    <div className={`text-sm font-black uppercase tracking-widest transition-colors ${m.completed ? "text-white" : "text-white/20 group-hover/step:text-white/40"}`}>{m.step}</div>
                                    <div className={`text-[10px] font-medium leading-tight ${m.completed ? "text-violet-400" : "text-white/10"}`}>{m.desc}</div>
                                    {m.completed && (
                                        <div className="inline-flex mt-2 items-center gap-1.5 px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-[9px] font-black rounded uppercase tracking-tighter">
                                            <CheckCircle2 className="w-3 h-3" /> Verified
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                     </div>
                     
                     <div className="mt-12 p-6 bg-white/3 rounded-[2rem] border border-white/5">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-[10px] font-black text-white/30 uppercase tracking-widest">Next Milestone</span>
                            <span className="text-xs font-black text-violet-400 italic">24h Left</span>
                        </div>
                        <div className="text-[11px] font-bold text-white/60 mb-4 italic leading-relaxed">"Deep Architecture: Thấu hiểu Design Patterns trong Microservice"</div>
                        <button className="w-full py-3 bg-violet-600/10 hover:bg-violet-600 border border-violet-600/30 text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
                            Tiếp tục học
                        </button>
                     </div>
                </div>
             </div>
        </div>            </div>
        </div>
      </div>
    </AuthGuard>
  );
};

export default StudentDashboard;

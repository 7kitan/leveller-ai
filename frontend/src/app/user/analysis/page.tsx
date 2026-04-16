"use client";

import React, { useState, useEffect, Suspense } from "react";
import { motion } from "framer-motion";
import { useSearchParams } from "next/navigation";
import { 
  BrainCircuit, Zap, CheckCircle2, AlertCircle, 
  BookOpen, Clock, ChevronRight, 
  Info, Sparkles, History, ShieldCheck, RefreshCw, BarChart3, Target
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip, Legend
} from "recharts";

interface GapMatrixItem {
  jd_skill: string;
  cv_skill: string | null;
  status: "MET" | "PARTIAL" | "GAP";
  score: number;
  note: string;
}

interface SkillGap {
  skill: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  priority: number;
  reason: string;
  learning_path: string;
}

interface CourseRecommendation {
  skill_gap: string;
  severity?: "HIGH" | "MEDIUM" | "LOW";
  priority: number;
  reason: string;
  learning_path: string;
  courses: any[];
}

interface AnalysisResult {
  overall_match_pct: number;
  overall_assessment?: string;
  strengths?: string[];
  weaknesses?: string[];
  breakdown: {
    met: any[];
    gap: any[];
    partial: any[];
  };
  gap_matrix?: GapMatrixItem[];
  skill_gaps?: SkillGap[];
  course_recommendations?: CourseRecommendation[];
  recommendations: any[];
  seniority_report?: {
"use client";

import React, { useState, useEffect, Suspense } from "react";
import { motion } from "framer-motion";
import { useSearchParams } from "next/navigation";
import { 
  BrainCircuit, Zap, CheckCircle2, AlertCircle, 
  BookOpen, Clock, ChevronRight, 
  Info, Sparkles, History, ShieldCheck, RefreshCw, BarChart3, Target
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip, Legend
} from "recharts";

interface GapMatrixItem {
  jd_skill: string;
  cv_skill: string | null;
  status: "MET" | "PARTIAL" | "GAP";
  score: number;
  note: string;
}

interface SkillGap {
  skill: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  priority: number;
  reason: string;
  learning_path: string;
}

interface CourseRecommendation {
  skill_gap: string;
  severity?: "HIGH" | "MEDIUM" | "LOW";
  priority: number;
  reason: string;
  learning_path: string;
  courses: any[];
}

interface AnalysisResult {
  overall_match_pct: number;
  overall_assessment?: string;
  strengths?: string[];
  weaknesses?: string[];
  breakdown: {
    met: any[];
    gap: any[];
    partial: any[];
  };
  gap_matrix?: GapMatrixItem[];
  skill_gaps?: SkillGap[];
  course_recommendations?: CourseRecommendation[];
  recommendations: any[];
  seniority_report?: {
    skill: string;
    total_years: number;
    highlights: string[];
  }[];
}

import styles from "./user-analysis.module.css";

function AnalysisContent() {
  const { user, token } = useAuth();
  const searchParams = useSearchParams();
  const cvIdFromUrl = searchParams.get("cv_id");

  const [cvList, setCvList] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedCvId, setSelectedCvId] = useState(cvIdFromUrl || "");
  const [selectedJobId, setSelectedJobId] = useState("");
  const [jdText, setJdText] = useState("");
  const [useCustomJd, setUseCustomJd] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [pollingStage, setPollingStage] = useState("");
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [recommendedCourses, setRecommendedCourses] = useState<any[]>([]);
  const [selectedCourseIds, setSelectedCourseIds] = useState<string[]>([]);
  const [simulationResult, setSimulationResult] = useState<any>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");


  useEffect(() => {
    if (token) {
        fetchInitialData();
    }
  }, [token]);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      const [cvRes, jobRes] = await Promise.all([
        fetch("/api/cv/list", { headers: { "Authorization": `Bearer ${token}` } }),
        fetch("/api/jd/list", { headers: { "Authorization": `Bearer ${token}` } })
      ]);
      
      if (cvRes.ok) {
        const list = await cvRes.json();
        setCvList(list);
        if (!selectedCvId && list.length > 0) {
            setSelectedCvId(list[0].id);
            fetchAnalysis(list[0].id);
        } else if (selectedCvId) {
            fetchAnalysis(selectedCvId);
        }
      }
      if (jobRes.ok) setJobs(await jobRes.json());
    } catch (err) {
      console.error("Fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalysis = async (cvId: string) => {
    try {
        const response = await fetch(`/api/analysis/latest?cv_id=${cvId}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (response.ok) {
            const resData = await response.json();
            setData(resData);
        } else {
            setData(null);
        }
    } catch (err) {
        console.error("Fetch analysis error:", err);
    }
  };

  const handleStartAnalysis = async () => {
    if (!selectedCvId) return;
    setAnalyzing(true);
    setError("");
    setData(null);

    try {
      const res = await fetch("/api/analysis/gap", {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          cv_id: selectedCvId,
          ...(useCustomJd && jdText.trim() ? { jd_text: jdText } : selectedJobId ? { job_id: selectedJobId } : {})
        })
      });

      if (res.ok) {
        const { task_id } = await res.json();
        let attempts = 0;
        let errorCount = 0;
        const stages = [
            "Khởi tạo kén AI...",
            "Thẩm định thâm niên chuyên gia...",
            "Truy vấn Graph mạng lưới tri thức...",
            "Giải mã ngữ cảnh kinh nghiệm...",
            "Tổng hợp chỉ số phù hợp...",
            "Hoàn thiện báo cáo cao cấp..."
        ];

        const poll = async () => {
            if (attempts >= 60) {
                setAnalyzing(false);
                setError("Quá thời gian xử lý (90s). Vui lòng kiểm tra lại sau.");
                return;
            }
            if (errorCount > 3) {
                setAnalyzing(false);
                setError("Mất kết nối liên tục với Server. Vui lòng thử lại.");
                return;
            }

            setPollingStage(stages[Math.min(Math.floor(attempts / 4), stages.length - 1)]);
            attempts++;
            
            try {
                const statusRes = await fetch(`/api/analysis/status/${task_id}`, {
                    headers: { "Authorization": `Bearer ${token}` }
                });
                if (statusRes.ok) {
                    errorCount = 0; // Reset error count on success
                    const s = await statusRes.json();
                    if (s.status === "SUCCESS" || s.status === "completed") {
                        if (s.result && s.result.error) {
                            setError(s.result.error);
                            setAnalyzing(false);
                        } else {
                            setData(s.result);
                            setAnalyzing(false);
                        }
                        return;
                    } else if (s.status === "FAILURE") {
                        setAnalyzing(false);
                        setError("AI Engine không thể hoàn thành phân tích.");
                        return;
                    }
                } else {
                    errorCount++;
                }
            } catch (err) {
                errorCount++;
                console.error("Polling error:", err);
            }
            setTimeout(poll, 1500);
        };
        setTimeout(poll, 500);
      } else {
        setAnalyzing(false);
        setError("Lỗi khi gửi yêu cầu phân tích.");
      }
    } catch (err) {
      setAnalyzing(false);
      setError("Mất kết nối với AI Engine.");
    }
  };

  const handleSimulate = async () => {
      if (selectedCourseIds.length === 0) return;
      setIsSimulating(true);
      try {
          const res = await fetch("/api/analysis/simulate", {
              method: "POST",
              headers: { 
                  "Content-Type": "application/json",
                  "Authorization": `Bearer ${token}`
              },
              body: JSON.stringify({
                  cv_id: selectedCvId,
                  selected_course_ids: selectedCourseIds,
                  job_id: selectedJobId || null
              })
          });
          if (res.ok) {
              setSimulationResult(await res.json());
          }
      } catch (err) {
          console.error("Simulation error:", err);
      } finally {
          setIsSimulating(false);
      }
  };

  const submitFeedback = async () => {
      if (feedbackRating === 0 || !data) return;
      try {
          const res = await fetch("/api/analysis/feedback", {
              method: "POST",
              headers: { 
                  "Content-Type": "application/json",
                  "Authorization": `Bearer ${token}`
              },
              body: JSON.stringify({
                  analysis_id: selectedCvId, 
                  rating: feedbackRating,
                  is_accurate: feedbackRating >= 4,
                  comment: feedbackComment
              })
          });
          if (res.ok) setFeedbackSubmitted(true);
      } catch (err) {
          console.error("Feedback error:", err);
      }
  };


  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#020617] text-white">
        <div className="relative w-24 h-24 mb-6">
            <div className="absolute inset-0 border-4 border-indigo-500/20 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
        <p className="text-indigo-400 font-black tracking-widest animate-pulse italic uppercase">Initiating Data Stream...</p>
      </div>
    );
  }

  return (
    <div className={styles.pageRoot}>
      {/* Dynamic Background */}
      <div className={styles.dynamicBg}>
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-indigo-600/10 blur-[150px] rounded-full animate-pulse"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-violet-600/10 blur-[150px] rounded-full animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-[0.03]"></div>
      </div>

      <div className={styles.contentWrapper}>
        {/* Header Section */}
        <header className={styles.header}>
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-full">
              <Sparkles size={14} className="text-indigo-400" />
              <span className="text-indigo-400 text-[10px] font-black tracking-[0.2em] uppercase">Enterprise AI Analysis v2.0</span>
            </div>
            <h1 className={styles.headerTitle}>
              CAREER <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-violet-500 italic">GENOME.</span>
            </h1>
            <p className={styles.headerSubtitle}>
              Phân tích đa chiều về năng lực thực chiến, đo lường thâm niên qua ngữ cảnh và đề xuất lộ trình nâng cấp sự nghiệp cá nhân hóa.
            </p>
          </div>

          {!analyzing && data && (
            <button 
              onClick={() => setData(null)}
              className={styles.newAnalysisBtn}
            >
              <RefreshCw size={18} /> PHÂN TÍCH MỚI
            </button>
          )}
        </header>

        {analyzing ? (
          <div className={styles.analyzingPanel}>
            <div className="relative w-56 h-56 mb-16">
                <div className="absolute inset-0 border-[16px] border-white/5 rounded-full"></div>
                <div className={styles.spinRing}></div>
                <div className="absolute inset-0 flex items-center justify-center">
                    <BrainCircuit className="text-white animate-pulse" size={72} />
                </div>
                <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-indigo-600 text-white text-[10px] font-black rounded-lg uppercase tracking-widest shadow-lg">
                   Processing
                </div>
            </div>
            <h2 className={styles.analyzingTitle}>{pollingStage}</h2>
            <p className="text-slate-500 font-bold italic tracking-wide">Thuật toán đang bóc tách thâm niên thực tế của bạn...</p>
          </div>
        ) : !data ? (
          <div className={styles.configGrid}>
             <div className={styles.configPanel}>
                <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/5 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/2"></div>
                
                <div className="relative z-10 space-y-10">
                  <div className="flex items-center gap-3">
                    <div className="w-1.5 h-8 bg-indigo-500 rounded-full"></div>
                    <h3 className="text-slate-200 font-black italic tracking-widest uppercase text-lg">Cấu hình tham số</h3>
                  </div>

                  <div className="grid gap-10">
                    <div className={styles.inputWrapper}>
                      <label className="flex justify-between items-end px-2">
                        <span className="text-slate-400 text-[10px] font-black uppercase tracking-[0.3em]">1. Hồ sơ năng lực (CV)</span>
                        <span className="text-indigo-400/50 text-[10px] font-bold italic">Required</span>
                      </label>
                      <div className="relative">
                        <select 
                          value={selectedCvId}
                          onChange={(e) => setSelectedCvId(e.target.value)}
                          className={styles.inputField}
                        >
                          {cvList.length === 0 && <option value="" className="bg-slate-900">Chưa có hồ sơ nào</option>}
                          {cvList.map(cv => (
                            <option key={cv.id} value={cv.id} className="bg-slate-900">
                                {cv.full_name || 'Anonymous Profile'} ({new Date(cv.created_at).toLocaleDateString()})
                            </option>
                          ))}
                        </select>
                        <div className="absolute right-6 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500">
                          <ChevronRight className="rotate-90" size={20} />
                        </div>
                      </div>
                    </div>

                    <div className={styles.inputWrapper}>
                      <div className="flex justify-between items-center px-2">
                        <label className="text-slate-400 text-[10px] font-black uppercase tracking-[0.3em]">2. Mục tiêu sự nghiệp (JD)</label>
                        <div className="flex p-1 bg-white/5 rounded-xl border border-white/10">
                            <button 
                              onClick={() => setUseCustomJd(false)}
                              className={`px-4 py-1.5 rounded-lg text-[10px] font-black transition-all ${!useCustomJd ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                              >
                                SYSTEM
                            </button>
                            <button 
                              onClick={() => setUseCustomJd(true)}
                              className={`px-4 py-1.5 rounded-lg text-[10px] font-black transition-all ${useCustomJd ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                              >
                                CUSTOM
                            </button>
                        </div>
                      </div>
        ) : (
          <div className={styles.resultsRoot}>
            {/* Top Action / ID Bar */}
            <div className={styles.reportIdBar}>
               <div className="flex items-center gap-4">
                  <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Report ID:</span>
                  <span className="text-[10px] font-black text-indigo-400 italic">#{selectedCvId.substring(0,8).toUpperCase()}</span>
               </div>
               <button 
                 onClick={() => window.print()}
                 className="text-[10px] font-black text-slate-400 hover:text-white uppercase italic transition-colors"
               >
                 Export Report PDF
               </button>
            </div>

            {/* MASSIVE RADAR HERO SECTION */}
            <div className={styles.radarHero}>
               <div className="absolute top-0 right-0 w-[40rem] h-[40rem] bg-indigo-600/10 rounded-full blur-[120px] -translate-y-1/2 translate-x-1/2"></div>
               <div className="absolute bottom-0 left-0 w-[40rem] h-[40rem] bg-violet-600/5 rounded-full blur-[120px] translate-y-1/2 -translate-x-1/2"></div>
               
               <div className="relative z-10 text-center mb-16">
                  <h3 className="text-slate-500 font-black italic uppercase tracking-[0.6em] text-[12px] mb-4 uppercase tracking-[0.6em]">Competency Genome Map</h3>
                  <div className="h-1 w-24 bg-gradient-to-r from-transparent via-indigo-500 to-transparent mx-auto"></div>
               </div>

               <div className="relative h-[900px] w-full z-10">
                  {/* Overall Score Overlay */}
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center z-20 pointer-events-none">
                     <div className={styles.radarScoreBadge}>
                        <span className="text-6xl font-black text-white italic tracking-tighter leading-none">{Math.round(data?.overall_match_pct || 0)}%</span>
                        <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mt-2">Overall Fit</span>
                     </div>
                  </div>

                  <ResponsiveContainer width="100%" height="100%">
                      <RadarChart cx="50%" cy="50%" outerRadius="80%" data={[
                         ...(data?.breakdown?.met || []),
                         ...(data?.breakdown?.partial || []),
                         ...(data?.breakdown?.gap || [])
                       ].map(s => ({ 
                         subject: (s.skill || '').length > 20 ? s.skill.substring(0,18) + '..' : s.skill,
                         actual: s.score || 0,
                         target: 100,
                         full: 100 
                       }))}>
                        <PolarGrid stroke="#ffffff15" strokeDasharray="3 3" />
                        <PolarAngleAxis 
                          dataKey="subject" 
                          tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: '900', fontStyle: 'italic' }}
                          tickLine={false}
                        />
                        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                        <Radar 
                          name="Hồ sơ của bạn" 
                          dataKey="actual" 
                          stroke="#6366f1" 
                          fill="#6366f1" 
                          fillOpacity={0.5} 
                          dot={{ r: 4, fill: '#6366f1', stroke: '#fff', strokeWidth: 2 }} 
                        />
                        <Radar 
                          name="Yêu cầu JD (Target)" 
                          dataKey="target" 
                          stroke="#fb7185" 
                          fill="#fb7185" 
                          fillOpacity={0.1} 
                          strokeDasharray="10 10" 
                        />
                        <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '16px', fontSize: '11px', color: '#fff', boxShadow: '0 20px 50px rgba(0,0,0,0.5)' }} />
                        <Legend iconType="circle" wrapperStyle={{ paddingTop: '40px', fontSize: '12px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '1px' }} />
                      </RadarChart>
                  </ResponsiveContainer>
               </div>
            </div>

            <div className="space-y-12">
                   {/* Strengths & Weaknesses */}
                   <div className={styles.assessmentGrid}>
                      {/* Overall Assessment overlay if present */}
                      {data?.overall_assessment && (
                        <div className="lg:col-span-2 bg-indigo-600/10 border border-indigo-500/30 rounded-[2.5rem] p-8 mb-4">
                           <div className="flex items-start gap-4">
                              <BrainCircuit className="text-indigo-400 mt-1 shrink-0" size={24} />
                              <div>
                                 <h4 className="text-indigo-400 font-black italic text-sm uppercase tracking-widest mb-2">AI Expert Insights</h4>
                                 <p className="text-slate-300 font-medium italic leading-relaxed text-sm">"{data.overall_assessment}"</p>
                              </div>
                           </div>
                        </div>
                      )}

                      {/* Strengths */}
                      <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-[2.5rem] p-8 relative overflow-hidden group">
                         <div className="absolute top-0 right-0 p-8 opacity-5">
                            <ShieldCheck size={120} className="text-emerald-500" />
                         </div>
                         <h3 className="text-[10px] font-black text-emerald-400 italic mb-6 flex items-center gap-3 uppercase tracking-[0.4em]">
                           <ShieldCheck size={16} /> Key Strengths
                         </h3>
                         <ul className="space-y-4">
                            {data?.strengths?.map((s, i) => (
                               <li key={i} className="flex items-start gap-3">
                                  <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full mt-1.5 shrink-0 shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
                                  <span className="text-slate-200 font-bold italic text-sm leading-relaxed">{s}</span>
                               </li>
                            )) || <li className="text-slate-600 italic text-xs">Phân tích đang được xử lý...</li>}
                         </ul>
                      </div>

                      {/* Weaknesses */}
                      <div className="bg-rose-500/5 border border-rose-500/10 rounded-[2.5rem] p-8 relative overflow-hidden group">
                         <div className="absolute top-0 right-0 p-8 opacity-5">
                            <AlertCircle size={120} className="text-rose-500" />
                         </div>
                         <h3 className="text-[10px] font-black text-rose-400 italic mb-6 flex items-center gap-3 uppercase tracking-[0.4em]">
                           <AlertCircle size={16} /> Strategic Gaps
                         </h3>
                         <ul className="space-y-4">
                            {data?.weaknesses?.map((w, i) => (
                               <li key={i} className="flex items-start gap-3">
                                  <div className="w-1.5 h-1.5 bg-rose-500 rounded-full mt-1.5 shrink-0 shadow-[0_0_10px_rgba(244,63,94,0.5)]"></div>
                                  <span className="text-slate-200 font-bold italic text-sm leading-relaxed">{w}</span>
                               </li>
                            )) || <li className="text-slate-600 italic text-xs">Phân tích đang được xử lý...</li>}
                         </ul>
                      </div>
                   </div>

                   {/* GAP MATRIX SECTION */}
                   {data?.gap_matrix && (
                     <div className="bg-white/[0.03] backdrop-blur-2xl border border-white/10 rounded-[3rem] p-10">
                        <div className="flex justify-between items-end mb-10">
                           <div>
                              <h3 className="text-white font-black italic text-3xl tracking-tighter uppercase mb-2">Skill Gap Matrix</h3>
                              <p className="text-slate-500 font-bold text-xs uppercase tracking-widest italic">Bản đồ đối soát kỹ năng CV vs Yêu cầu JD</p>
                           </div>
                           <div className="flex gap-4">
                              {[
                                { label: 'MET', color: 'bg-emerald-500' },
                                { label: 'PARTIAL', color: 'bg-indigo-500' },
                                { label: 'GAP', color: 'bg-rose-500' }
                              ].map(l => (
                                <div key={l.label} className="flex items-center gap-2">
                                   <div className={`w-2 h-2 rounded-full ${l.color}`}></div>
                                   <span className="text-[8px] font-black text-slate-500 uppercase">{l.label}</span>
                                </div>
                              ))}
                           </div>
                        </div>

                        <div className={styles.matrixGrid}>
                           {(data?.gap_matrix ?? []).map((item, idx) => (
                             <div key={idx} className={`${styles.matrixCard} ${
                                item.status === 'MET' ? 'border-emerald-500/20' : 
                                item.status === 'PARTIAL' ? 'border-indigo-500/20' : 'border-rose-500/20'
                               }`}><div className="flex justify-between items-start mb-4">
                                    <div>
                                       <h4 className="text-white font-black italic text-md leading-none mb-1 uppercase tracking-tight">{item.jd_skill}</h4>
                                       <span className={`text-[10px] font-black italic px-2 py-0.5 rounded-full ${
                                         item.status === 'MET' ? 'bg-emerald-500/20 text-emerald-400' : 
                                         item.status === 'PARTIAL' ? 'bg-indigo-500/20 text-indigo-400' : 'bg-rose-500/20 text-rose-400'
                                        }`}>{item.status}
                                      </span>
                                   </div>
                                   <div className="text-right">
                                      <span className={`text-xl font-black italic ${
                                        item.status === 'MET' ? 'text-emerald-400' : 
                                        item.status === 'PARTIAL' ? 'text-indigo-400' : 'text-rose-400'
                                      }`}>{item.score}%</span>
                                   </div>
                                </div>
                                <div className="space-y-3">
                                   <div className="flex items-center gap-2 text-slate-500 text-[10px] font-bold">
                                      <span className="uppercase">Match from:</span>
                                      <span className="text-slate-300">{item.cv_skill || 'N/A (Missing)'}</span>
                                   </div>
                                   <p className="text-slate-400 text-[11px] font-medium italic leading-relaxed bg-white/5 p-3 rounded-xl border border-white/5">
                                      {item.note}
                                   </p>
                                </div>
                             </div>
                           ))}
                        </div>
                     </div>
                   )}

                   {/* Met Skills Card */}
                   <div className="bg-white/[0.03] backdrop-blur-2xl border border-white/10 rounded-[2.5rem] p-8 group overflow-hidden relative">
                      <div className="absolute -bottom-6 -right-6 text-emerald-500/5 group-hover:scale-110 transition-transform duration-700">
                         <CheckCircle2 size={100} />
                      </div>
                      <h3 className="text-[9px] font-black text-emerald-400 italic mb-6 flex items-center gap-3 uppercase tracking-[0.4em] relative z-10">
                        <CheckCircle2 size={14} /> Skills Owned
                      </h3>
                      <div className={styles.skillBadgeGrid}>
                        {(data?.breakdown?.met?.length || 0) > 0 ? (data?.breakdown?.met ?? []).map((s, i) => (
                           <div key={i} className={`${styles.skillItem} hover:bg-emerald-500/10`}>
                              <div>
                                 <span className="block text-white font-black italic text-xs tracking-tight leading-none mb-1">{s.skill}</span>
                                 <span className="text-[8px] font-bold text-slate-600 uppercase italic">Validated Match</span>
                              </div>
                              <span className="text-sm font-black italic text-emerald-400">+{s.score}%</span>
                           </div>
                        )) : (
                           <div className="py-10 text-center opacity-10 font-black italic text-[9px] uppercase">No Skills Matched</div>
                        )}
                      </div>
                   </div>

                   {/* Partial Gaps (Up-level) */}
                   <div className="bg-white/[0.03] backdrop-blur-2xl border border-white/10 rounded-[2.5rem] p-8 group overflow-hidden relative border-dashed border-indigo-500/30">
                      <div className="absolute -bottom-6 -right-6 text-indigo-500/5 group-hover:scale-110 transition-transform duration-700">
                         <Zap size={100} />
                      </div>
                      <h3 className="text-[9px] font-black text-indigo-400 italic mb-6 flex items-center gap-3 uppercase tracking-[0.4em] relative z-10">
                        <RefreshCw size={14} /> Growth Points
                      </h3>
                      <div className={styles.skillBadgeGrid}>
                        {(data?.breakdown?.partial?.length || 0) > 0 ? (data?.breakdown?.partial ?? []).map((s, i) => (
                           <div key={i} className={`${styles.skillItem} border-indigo-500/10 hover:bg-indigo-500/20`}>
                              <div>
                                 <span className="block text-white font-black italic text-xs tracking-tight leading-none mb-1">{s.skill}</span>
                                 <span className="text-[8px] font-bold text-indigo-400 uppercase italic">Needs Seniority</span>
                              </div>
                              <span className="text-sm font-black italic text-indigo-400">+{s.score}%</span>
                           </div>
                        )) : (
                           <div className="py-10 text-center opacity-10 font-black italic text-[9px] uppercase">No Level Gaps</div>
                        )}
                      </div>
                   </div>

                   {/* Critical Gaps Card */}
                   <div className="bg-white/[0.03] backdrop-blur-2xl border border-white/10 rounded-[2.5rem] p-8 group overflow-hidden relative">
                      <div className="absolute -bottom-6 -right-6 text-amber-500/5 group-hover:scale-110 transition-transform duration-700">
                         <AlertCircle size={100} />
                      </div>
                      <h3 className="text-[9px] font-black text-amber-400 italic mb-6 flex items-center gap-3 uppercase tracking-[0.4em] relative z-10">
                        <AlertCircle size={14} /> Critical Gaps
                      </h3>
                      <div className={styles.skillBadgeGrid}>
                        {(data?.breakdown?.gap?.length || 0) > 0 ? (data?.breakdown?.gap ?? []).map((s, i) => (
                           <div key={i} className={`${styles.skillItem} hover:bg-amber-500/10`}>
                              <div>
                                 <span className="block text-white font-black italic text-xs tracking-tight leading-none mb-1">{s.skill}</span>
                                 <span className="text-[8px] font-bold text-slate-600 uppercase italic">{s.is_mandatory ? 'Mandatory' : 'Optional'}</span>
                              </div>
                              <span className={`px-2 py-1 text-[8px] font-black rounded italic ${s.is_mandatory ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-slate-700/50 text-slate-400'} uppercase`}>Missing</span>
                           </div>
                        )) : (
                           <div className="py-10 text-center opacity-10 font-black italic text-[9px] uppercase">No Critical Gaps</div>
                        )}
                      </div>
                   </div>
                </div>

                {/* Recommendations & Simulation Section */}
                <section className={styles.bridgeSection}>
                   <div className="absolute bottom-0 right-0 w-96 h-96 bg-indigo-600/5 rounded-full blur-[100px] translate-y-1/2 translate-x-1/2"></div>
                   
                   <div className="flex flex-col md:flex-row md:items-center justify-between gap-8 mb-16 relative z-10">
                      <div className="flex items-center gap-6">
                        <div className="p-5 bg-indigo-600 rounded-3xl shadow-[0_15px_40px_rgba(79,70,229,0.3)]">
                           <BookOpen size={40} className="text-white" />
                        </div>
                        <div>
                           <h3 className="text-4xl font-black text-white italic tracking-tighter uppercase">Skill Bridge.</h3>
                           <p className="text-slate-500 font-bold italic text-lg mt-1">Lộ trình nâng cấp năng lực được hỗ trợ bởi AI</p>
                        </div>
                      </div>
                      {selectedCourseIds.length > 0 && (
                          <button 
                             onClick={handleSimulate}
                             disabled={isSimulating}
                             className="px-10 py-5 bg-emerald-600 hover:bg-emerald-500 text-white font-black text-sm italic rounded-2xl transition-all shadow-xl flex items-center gap-3"
                          >
                             {isSimulating ? <RefreshCw className="animate-spin" /> : <Zap fill="white" />} 
                             SIMULATE ROADMAP ({selectedCourseIds.length})
                          </button>
                      )}
                   </div>

                   {simulationResult && (
                        <div className={styles.simulationPanel}>
                            <div className="flex flex-col lg:flex-row gap-12 items-center">
                                <div className="text-center lg:text-left space-y-4">
                                    <h4 className="text-[10px] font-black uppercase tracking-widest text-indigo-400">Projected Growth</h4>
                                    <div className="text-7xl font-black text-white italic">
                                        {simulationResult.projected_market_fit_pct}% 
                                        <span className="text-xs text-emerald-400 ml-4 font-bold">+10% Growth</span>
                                    </div>
                                    <p className="text-slate-400 text-sm italic">Sau khi hoàn thành lộ trình, tỉ lệ khớp thị trường của bạn sẽ tăng mạnh.</p>
                                    <div className="flex gap-4 mt-6">
                                        <div className="px-4 py-2 bg-white/5 rounded-xl border border-white/10">
                                            <div className="text-white font-black">{simulationResult.estimated_duration_hours}h</div>
                                            <div className="text-[8px] text-slate-500 uppercase font-black">Total Hours</div>
                                        </div>
                                        <div className="px-4 py-2 bg-white/5 rounded-xl border border-white/10">
                                            <div className="text-white font-black">~{simulationResult.estimated_duration_weeks}w</div>
                                            <div className="text-[8px] text-slate-500 uppercase font-black">Timeline</div>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex-1 space-y-6">
                                    <h4 className="text-[10px] font-black uppercase tracking-widest text-indigo-400 mb-6">Learning Stages</h4>
                                    <div className="space-y-4">
                                        {simulationResult.roadmap_stages.map((stage: any) => (
                                            <div key={stage.stage} className="flex gap-6 items-start">
                                                <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-black shrink-0 shadow-lg shadow-indigo-500/30">{stage.stage}</div>
                                                <div>
                                                    <div className="text-white font-black text-sm uppercase italic tracking-tight">{stage.focus}</div>
                                                    <div className="flex flex-wrap gap-2 mt-2">
                                                        {stage.skills_acquired.map((s: string) => (
                                                            <span key={s} className="px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 text-[9px] text-indigo-300 rounded font-bold">{s}</span>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                   )}

                   <div className="space-y-16 relative z-10">
                      {(data?.course_recommendations || []).length > 0 ? (data?.course_recommendations ?? []).map((rec, groupIdx) => (
                        <div key={groupIdx} className="space-y-8 animate-in fade-in slide-in-from-bottom-10 duration-700" style={{ animationDelay: `${groupIdx * 200}ms` }}>
                          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-white/5">
                            <div className="space-y-3">
                              <div className="flex items-center gap-3">
                                <div className={`px-4 py-1 rounded-full text-[10px] font-black italic tracking-widest uppercase ${
                                  rec.severity === 'HIGH' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 
                                  rec.severity === 'MEDIUM' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 
                                  'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                                 }`}>{rec.severity || 'Gap Detected'}
                                 </div>
                                <h4 className="text-3xl font-black text-white italic tracking-tighter uppercase">{rec.skill_gap}</h4>
                              </div>
                              <p className="text-slate-400 font-bold italic text-sm max-w-2xl">{rec.reason}</p>
                              {rec.learning_path && (
                                <div className="flex items-center gap-2 text-[10px] font-black text-indigo-400 uppercase tracking-widest">
                                  <ChevronRight size={14} /> Path: {rec.learning_path}
                                </div>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-slate-500 font-black italic text-[10px] uppercase tracking-widest bg-white/5 px-4 py-2 rounded-xl border border-white/10">
                              Priority: {rec.priority || (groupIdx + 1)}
                            </div>
                          </div>

                          <div className={styles.courseGrid}>
                            {rec.courses.map((course, idx) => (
                              <div 
                                  key={idx} 
                                  onClick={() => setSelectedCourseIds(prev => prev.includes(course.id) ? prev.filter(id => id !== course.id) : [...prev, course.id])}
                                  className={`${styles.courseCard} ${
                                    selectedCourseIds.includes(course.id) ? "border-emerald-500/50 bg-emerald-500/5 ring-1 ring-emerald-500/50" : "border-white/5"
                                   }`}
                                >
                                {selectedCourseIds.includes(course.id) && (
                                  <div className="absolute top-0 right-0 p-4">
                                    <div className="bg-emerald-500 text-white rounded-full p-1 shadow-lg">
                                      <CheckCircle2 size={16} />
                                    </div>
                                  </div>
                                )}
                                
                                <div className="flex justify-between items-center mb-8">
                                   <span className="px-3 py-1 bg-white/5 border border-white/10 text-slate-400 text-[10px] font-black rounded-lg uppercase tracking-widest italic group-hover:text-indigo-400 transition-colors">
                                      {course.platform || 'Academy'}
                                   </span>
                                   <div className="text-[10px] font-black text-slate-600 italic uppercase">#{course.level || 'Expert'}</div>
                                </div>

                                <h4 className="text-xl font-black text-white italic mb-8 leading-tight group-hover:text-indigo-400 transition-colors line-clamp-2 h-14">{course.title}</h4>
                                
                                <div className="flex items-center justify-between pt-6 border-t border-white/5">
                                   <div className="flex items-center gap-2 text-slate-500 text-[10px] font-bold italic uppercase tracking-tighter">
                                      <Clock size={14} className="text-indigo-500" /> ~{course.duration_hours || '12'} Hrs
                                   </div>
                                   <a 
                                     href={course.url} 
                                     target="_blank" 
                                     rel="noreferrer"
                                     onClick={(e) => e.stopPropagation()}
                                     className="text-white font-black text-[9px] bg-indigo-600/20 border border-indigo-600/30 hover:bg-indigo-600 px-4 py-2 rounded-xl transition-all uppercase tracking-widest shadow-lg shadow-indigo-600/20"
                                   >
                                     Explore
                                   </a>
                                </div>
                              </div>
                            ))}
                            {rec.courses.length === 0 && (
                              <div className="lg:col-span-3 py-10 bg-white/5 border border-dashed border-white/10 rounded-[2rem] text-center">
                                 <p className="text-slate-600 font-black italic text-xs uppercase">No matching courses found in database for this gap</p>
                              </div>
                            )}
                          </div>
                        </div>
                      )) : (
                        <div className="text-center py-20 bg-white/[0.02] border border-dashed border-white/10 rounded-[3rem]">
                           <Info className="mx-auto text-slate-700 mb-4" size={48} />
                           <p className="text-slate-500 font-black italic text-sm uppercase tracking-widest">Không tìm thấy gợi ý lộ trình phù hợp.</p>
                        </div>
                      )}
                   </div>
                </section>

                {/* User Feedback Section */}
                {!feedbackSubmitted ? (
                    <section className={styles.feedbackSection}>
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-violet-500 to-indigo-500"></div>
                        <h3 className="text-xl font-black text-white italic mb-4">REPORT ACCURACY FEEDBACK</h3>
                        <p className="text-slate-500 text-sm font-bold italic mb-8">Đánh giá độ chính xác của AI trong bản báo cáo này</p>
                        
                        <div className="flex justify-center gap-4 mb-8">
                            {[1, 2, 3, 4, 5].map(star => (
                                <button 
                                    key={star}
                                    onClick={() => setFeedbackRating(star)}
                                    className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${feedbackRating >= star ? 'bg-amber-400 text-[#020617] scale-110 shadow-lg shadow-amber-500/20' : 'bg-white/5 text-slate-500 hover:bg-white/10'}`}
                                    >
      </div>
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#020617] text-white">
        <div className="w-12 h-12 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-indigo-400 font-black italic text-xs tracking-[0.3em] animate-pulse">BOOTING ANALYTICS...</p>
      </div>
    }>
      <AnalysisContent />
    </Suspense>
  );
}

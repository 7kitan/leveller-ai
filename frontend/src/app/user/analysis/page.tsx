"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { 
  BrainCircuit, Zap, CheckCircle2, AlertCircle, 
  BookOpen, Clock, ChevronRight, 
  Info, Sparkles, History, ShieldCheck, RefreshCw, BarChart3, Target
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, 
  ResponsiveContainer, Tooltip 
} from "recharts";

interface AnalysisResult {
  overall_match_pct: number;
  breakdown: {
    met: any[];
    gap: any[];
    partial: any[];
  };
  recommendations: any[];
  seniority_report: {
    skill: string;
    total_years: number;
    highlights: string[];
  }[];
}

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
        const response = await fetch(`/api/analysis/user/cv/${cvId}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (response.ok) {
            const resData = await response.json();
            setData(resData);
            if (resData.recommendations) {
                fetchRealCourses(resData.recommendations);
            }
        } else {
            setData(null);
        }
    } catch (err) {
        console.error("Fetch analysis error:", err);
    }
  };

  const fetchRealCourses = async (gaps: any[]) => {
      try {
          const res = await fetch("/api/recommend/courses", {
              method: "POST",
              headers: { 
                  "Content-Type": "application/json",
                  "Authorization": `Bearer ${token}`
              },
              body: JSON.stringify({ gap_skills: gaps.map(g => ({
                  skill_name: g.skill,
                  target_level: g.target_level || "Mid-level",
                  gap_type: g.type
              }))})
          });
          if (res.ok) {
              setRecommendedCourses(await res.json());
          }
      } catch (err) {
          console.error("Fetch real courses error:", err);
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
                            if (s.result.recommendations) {
                                fetchRealCourses(s.result.recommendations);
                            }
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
                  analysis_id: selectedCvId, // Hoặc ID của report nếu có
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
    <div className="min-h-screen bg-[#020617] text-slate-200 selection:bg-indigo-500/30">
      {/* Dynamic Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-indigo-600/10 blur-[150px] rounded-full animate-pulse"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-violet-600/10 blur-[150px] rounded-full animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-[0.03]"></div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-12 lg:py-20">
        {/* Header Section */}
        <header className="mb-20 text-center lg:text-left flex flex-col lg:flex-row lg:items-end lg:justify-between gap-10">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-full">
              <Sparkles size={14} className="text-indigo-400" />
              <span className="text-indigo-400 text-[10px] font-black tracking-[0.2em] uppercase">Enterprise AI Analysis v2.0</span>
            </div>
            <h1 className="text-6xl lg:text-8xl font-black text-white tracking-tighter italic leading-none">
              CAREER <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-violet-500 italic">GENOME.</span>
            </h1>
            <p className="text-slate-400 text-lg font-medium max-w-2xl italic leading-relaxed">
              Phân tích đa chiều về năng lực thực chiến, đo lường thâm niên qua ngữ cảnh và đề xuất lộ trình nâng cấp sự nghiệp cá nhân hóa.
            </p>
          </div>

          {!analyzing && data && (
            <button 
              onClick={() => setData(null)}
              className="px-8 py-4 bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl text-white font-black text-sm italic hover:bg-indigo-600 hover:border-indigo-500 transition-all flex items-center gap-2 shadow-xl"
            >
              <RefreshCw size={18} /> PHÂN TÍCH MỚI
            </button>
          )}
        </header>

        {analyzing ? (
          <div className="flex flex-col items-center justify-center min-h-[50vh] bg-white/[0.02] backdrop-blur-3xl border border-white/10 rounded-[4rem] p-16 text-center animate-in fade-in zoom-in duration-700 shadow-[0_40px_100px_rgba(0,0,0,0.5)]">
            <div className="relative w-56 h-56 mb-16">
                <div className="absolute inset-0 border-[16px] border-white/5 rounded-full"></div>
                <div className="absolute inset-0 border-[16px] border-indigo-50 rounded-full border-t-transparent animate-spin shadow-[0_0_50px_rgba(99,102,241,0.4)]"></div>
                <div className="absolute inset-0 flex items-center justify-center">
                    <BrainCircuit className="text-white animate-pulse" size={72} />
                </div>
                <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-indigo-600 text-white text-[10px] font-black rounded-lg uppercase tracking-widest shadow-lg">
                   Processing
                </div>
            </div>
            <h2 className="text-5xl font-black text-white italic tracking-tighter mb-4 uppercase animate-pulse">{pollingStage}</h2>
            <p className="text-slate-500 font-bold italic tracking-wide">Thuật toán đang bóc tách thâm niên thực tế của bạn...</p>
          </div>
        ) : !data ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
             <div className="lg:col-span-8 bg-white/[0.03] backdrop-blur-3xl border border-white/10 rounded-[3.5rem] p-10 lg:p-14 shadow-2xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/5 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/2"></div>
                
                <div className="relative z-10 space-y-10">
                  <div className="flex items-center gap-3">
                    <div className="w-1.5 h-8 bg-indigo-500 rounded-full"></div>
                    <h3 className="text-slate-200 font-black italic tracking-widest uppercase text-lg">Cấu hình tham số</h3>
                  </div>

                  <div className="grid gap-10">
                    <div className="space-y-4">
                      <label className="flex justify-between items-end px-2">
                        <span className="text-slate-400 text-[10px] font-black uppercase tracking-[0.3em]">1. Hồ sơ năng lực (CV)</span>
                        <span className="text-indigo-400/50 text-[10px] font-bold italic">Required</span>
                      </label>
                      <div className="relative">
                        <select 
                          value={selectedCvId}
                          onChange={(e) => setSelectedCvId(e.target.value)}
                          className="w-full p-6 bg-white/[0.03] border-2 border-white/10 rounded-[2rem] text-white focus:border-indigo-500/50 outline-none font-bold text-lg tracking-tight appearance-none transition-all hover:bg-white/[0.05]"
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

                    <div className="space-y-4">
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

                      {useCustomJd ? (
                        <textarea 
                          value={jdText}
                          onChange={(e) => setJdText(e.target.value)}
                          placeholder="Dán nội dung mô tả công việc (JD) vào đây để AI bóc tách yêu cầu..."
                          className="w-full h-56 p-7 bg-white/[0.03] border-2 border-white/10 rounded-[2.5rem] text-white focus:border-indigo-500/50 outline-none font-medium text-lg leading-relaxed transition-all placeholder:text-slate-700"
                        />
                      ) : (
                        <div className="relative">
                          <select 
                            value={selectedJobId}
                            onChange={(e) => setSelectedJobId(e.target.value)}
                            className="w-full p-6 bg-white/[0.03] border-2 border-white/10 rounded-[2rem] text-white focus:border-indigo-500/50 outline-none font-bold text-lg appearance-none transition-all hover:bg-white/[0.05]"
                          >
                            <option value="" className="bg-slate-900">-- Phân tích theo bộ kỹ năng thị trường --</option>
                            {jobs.map(j => (
                              <option key={j.id} value={j.id} className="bg-slate-900">{j.title_raw} @ {j.company_name || 'N/A'}</option>
                            ))}
                          </select>
                          <div className="absolute right-6 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500">
                             <ChevronRight className="rotate-90" size={20} />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="pt-6 relative">
                    <button 
                      onClick={handleStartAnalysis}
                      disabled={!selectedCvId || (useCustomJd && !jdText.trim())}
                      className="group relative w-full py-7 bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-[2rem] font-black text-2xl tracking-tighter overflow-hidden hover:scale-[1.02] active:scale-95 transition-all shadow-[0_25px_60px_-15px_rgba(79,70,229,0.5)] disabled:opacity-20 disabled:grayscale disabled:hover:scale-100"
                    >
                      <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-500"></div>
                      <div className="relative z-10 flex items-center justify-center gap-4">
                        <Zap size={28} fill="currentColor" className="text-white" />
                        RUN DEEP ANALYSIS
                      </div>
                    </button>
                    {error && <p className="mt-6 text-rose-500 font-bold text-center italic text-sm animate-bounce">⚠️ {error}</p>}
                  </div>
                </div>
             </div>

             <div className="lg:col-span-4 space-y-10">
                <div className="bg-indigo-600/10 border border-indigo-500/20 rounded-[3rem] p-10 relative overflow-hidden group">
                  <div className="absolute -bottom-8 -right-8 opacity-5 group-hover:opacity-10 transition-opacity">
                    <History size={200} />
                  </div>
                  <h4 className="text-white font-black italic text-2xl mb-4 tracking-tight uppercase">Thâm niên 2.0</h4>
                  <p className="text-indigo-200/60 font-medium italic text-sm leading-relaxed mb-6">
                    Chúng tôi không chỉ đếm năm. Thuật toán của AI bóc tách thâm niên thực chiến bằng cách đối soát các dự án và mô tả công việc cũ của bạn.
                  </p>
                  <ul className="space-y-3">
                    {['Xác thực qua ngữ cảnh', 'Đối soát Skill Graph', 'Định lượng số năm thực tế'].map((item, i) => (
                      <li key={i} className="flex items-center gap-3 text-indigo-300 font-black italic text-xs uppercase tracking-wider">
                         <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full"></div> {item}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-white/[0.03] border border-white/10 rounded-[3rem] p-10 flex flex-col justify-center items-center text-center">
                   <Target className="text-indigo-500 mb-6" size={48} />
                   <h4 className="text-white font-black italic text-xl mb-2">ĐỘ CHÍNH XÁC GRAPH.</h4>
                   <p className="text-slate-500 font-bold italic text-xs leading-relaxed">
                     Sử dụng mạng lưới tri thức 1.5M kết nối để so khớp kỹ năng đa ngôn ngữ và nền tảng.
                   </p>
                </div>
             </div>
          </div>
        ) : (
          <div className="animate-in fade-in slide-in-from-bottom-20 duration-1000 space-y-12">
            {/* Action Bar (Top) */}
            <div className="flex justify-between items-center bg-white/[0.03] backdrop-blur-xl border border-white/10 rounded-full px-8 py-3">
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

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
              {/* Score Card */}
              <div className="lg:col-span-4 space-y-10">
                <div className="bg-white/[0.03] backdrop-blur-3xl border border-white/10 rounded-[3.5rem] p-12 text-center shadow-2xl relative overflow-hidden group">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-[60px] -translate-y-1/2 translate-x-1/2"></div>
                  
                  <h3 className="text-slate-500 font-black italic uppercase tracking-[0.4em] text-[10px] mb-12">Overall Match Quality</h3>
                  
                  <div className="relative w-64 h-64 mx-auto mb-10">
                    <svg className="w-full h-full -rotate-90">
                       <circle cx="128" cy="128" r="110" className="stroke-white/[0.03] fill-none" strokeWidth="16" />
                       <circle 
                         cx="128" cy="128" r="110" 
                         className="stroke-indigo-500 fill-none transition-all duration-1000" 
                         strokeWidth="16" 
                         strokeDasharray={691}
                         strokeDashoffset={691 - (691 * (data?.overall_match_pct || 0) / 100)}
                         strokeLinecap="round"
                       />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                       <span className="text-8xl font-black text-white italic tracking-tighter leading-none">{Math.round(data?.overall_match_pct || 0)}<span className="text-2xl text-indigo-400">%</span></span>
                       <span className="text-[10px] font-black text-slate-500 uppercase tracking-[0.4em] mt-2">Score</span>
                    </div>
                  </div>

                  <p className="text-slate-300 font-bold italic leading-relaxed px-4">
                    {(data?.overall_match_pct || 0) >= 80 ? "Năng lực xuất sắc, hồ sơ thuộc nhóm 5% ứng viên hàng đầu." :
                     (data?.overall_match_pct || 0) >= 50 ? "Hồ sơ ổn định, cần bổ sung thâm niên ở các mảng trọng yếu." :
                     "Cần nâng cấp kỹ năng nền tảng và bổ sung thâm niên thực tế."}
                  </p>
                </div>

                <div className="bg-white/[0.03] backdrop-blur-2xl border border-white/10 rounded-[3.5rem] p-10 h-[450px]">
                   <h3 className="text-slate-500 font-black italic uppercase tracking-[0.4em] text-[10px] mb-8">Competency Spread</h3>
                   <div className="w-full h-full pb-10">
                     <ResponsiveContainer width="100%" height="100%">
                         <RadarChart cx="50%" cy="50%" outerRadius="80%" data={[
                            ...(data?.breakdown?.met || []).slice(0, 5),
                            ...(data?.breakdown?.partial || []).slice(0, 3)
                          ].map(s => ({ 
                            subject: (s.skill || '').length > 10 ? s.skill.substring(0,8) + '..' : s.skill,
                            A: s.score || 0,
                            full: 100 
                          }))}>
                           <PolarGrid stroke="#ffffff10" />
                           <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 10, fontWeight: 'bold', fontStyle: 'italic' }} />
                           <Radar name="Candidate" dataKey="A" stroke="#6366f1" fill="#6366f1" fillOpacity={0.4} />
                           <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px' }} />
                         </RadarChart>
                     </ResponsiveContainer>
                   </div>
                </div>
              </div>

              {/* Main Content (Seniority & Breakdown) */}
              <div className="lg:col-span-8 space-y-10">
                {/* SENIORITY EVIDENCE - THE "WOW" SECTION */}
                <section className="bg-gradient-to-br from-indigo-600/10 to-transparent backdrop-blur-3xl border border-indigo-500/20 rounded-[4rem] p-10 lg:p-14 relative overflow-hidden group">
                   <div className="absolute top-0 right-0 p-12 opacity-[0.03] group-hover:scale-110 transition-transform duration-1000">
                      <ShieldCheck size={200} />
                   </div>

                   <div className="flex items-center gap-5 mb-12 relative z-10">
                      <div className="p-4 bg-indigo-500 rounded-3xl shadow-[0_15px_35px_rgba(79,70,229,0.3)]">
                         <History className="text-white" size={32} />
                      </div>
                      <div>
                         <h3 className="text-4xl font-black text-white italic tracking-tighter">BẰNG CHỨNG THÂM NIÊN.</h3>
                         <p className="text-slate-500 font-bold italic text-sm tracking-wide mt-1">Dẫn chứng thực tế trích xuất từ lịch sử làm việc của bạn</p>
                      </div>
                   </div>

                   {data?.seniority_report?.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10">
                        {data.seniority_report.map((report, idx) => (
                          <div key={idx} className="bg-white/[0.04] border border-white/5 rounded-[2.5rem] p-8 hover:bg-white/[0.06] hover:border-indigo-500/20 transition-all group/item">
                             <div className="flex justify-between items-start mb-6">
                                <h4 className="text-xl font-black text-white italic tracking-tight group-hover/item:text-indigo-400 transition-colors uppercase">{report.skill}</h4>
                                <div className="px-4 py-1.5 bg-indigo-600 text-white text-[10px] font-black rounded-xl italic flex items-center gap-2">
                                   <Clock size={12} /> {report.total_years} NĂM
                                </div>
                             </div>
                             
                             <div className="space-y-4">
                                {(report.highlights || []).map((h, hIdx) => {
                                   const parts = h.split(':');
                                   return (
                                     <div key={hIdx} className="relative pl-6 py-1">
                                        <div className="absolute left-0 top-3 w-1.5 h-1.5 bg-indigo-500 rounded-full"></div>
                                        {parts.length > 1 ? (
                                           <div className="space-y-2">
                                              <p className="text-slate-100 font-black italic text-xs leading-none">{parts[0].replace(/\*\*/g, '')}</p>
                                              <p className="text-slate-500 font-medium italic text-[11px] leading-relaxed line-clamp-3">
                                                 {parts[1].replace(/\"/g, '').replace(/\.\.\./g, '')}
                                              </p>
                                           </div>
                                        ) : (
                                          <p className="text-slate-400 font-medium italic text-xs leading-relaxed">{h.replace(/\*\*/g, '')}</p>
                                        )}
                                     </div>
                                   );
                                })}
                             </div>
                          </div>
                        ))}
                      </div>
                   ) : (
                      <div className="py-20 flex flex-col items-center justify-center text-slate-700 bg-white/[0.02] border-2 border-dashed border-white/5 rounded-[3rem]">
                         <Info size={56} className="mb-6 opacity-20" />
                         <p className="font-extrabold italic text-lg opacity-40 uppercase tracking-widest">Không có dữ liệu thâm niên khớp</p>
                         <p className="text-sm font-bold opacity-30 mt-2 px-12 text-center">Chúng tôi không tìm thấy bằng chứng thâm niên rõ ràng cho các kỹ năng yêu cầu trong hồ sơ hiện tại của bạn.</p>
                      </div>
                   )}
                </section>

                <div className="grid grid-cols-1 gap-12">
                   {/* Met Skills Card */}
                   <div className="bg-white/[0.03] backdrop-blur-2xl border border-white/10 rounded-[2.5rem] p-8 group overflow-hidden relative">
                      <div className="absolute -bottom-6 -right-6 text-emerald-500/5 group-hover:scale-110 transition-transform duration-700">
                         <CheckCircle2 size={100} />
                      </div>
                      <h3 className="text-[9px] font-black text-emerald-400 italic mb-6 flex items-center gap-3 uppercase tracking-[0.4em] relative z-10">
                        <CheckCircle2 size={14} /> Skills Owned
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 relative z-10">
                        {(data?.breakdown?.met?.length || 0) > 0 ? data.breakdown.met.map((s, i) => (
                           <div key={i} className="flex justify-between items-center p-4 bg-white/[0.04] border border-white/5 rounded-2xl group/skill hover:bg-emerald-500/10 transition-colors">
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
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 relative z-10">
                        {(data?.breakdown?.partial?.length || 0) > 0 ? data.breakdown.partial.map((s, i) => (
                           <div key={i} className="flex justify-between items-center p-4 bg-white/[0.04] border border-indigo-500/10 rounded-2xl group/skill hover:bg-indigo-500/20 transition-colors">
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
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 relative z-10">
                        {(data?.breakdown?.gap?.length || 0) > 0 ? data.breakdown.gap.map((s, i) => (
                           <div key={i} className="flex justify-between items-center p-4 bg-white/[0.04] border border-white/5 rounded-2xl group/skill hover:bg-amber-500/10 transition-colors">
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
              </div>
            </div>

            {/* Recommendations & Simulation Section */}
            <section className="mt-10 bg-white/[0.03] backdrop-blur-3xl border border-white/10 rounded-[4rem] p-12 lg:p-16 relative overflow-hidden">
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
                    <div className="mb-16 p-10 bg-indigo-500/10 border border-indigo-500/30 rounded-[3rem] animate-in fade-in slide-in-from-top-10 duration-700 relative z-10">
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

               <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10 relative z-10">
                  {recommendedCourses.map((course, idx) => (
                    <div 
                        key={idx} 
                        onClick={() => setSelectedCourseIds(prev => prev.includes(course.id) ? prev.filter(id => id !== course.id) : [...prev, course.id])}
                        className={`bg-white/[0.02] border rounded-[3rem] p-9 group hover:bg-white/[0.05] transition-all cursor-pointer ${
                            selectedCourseIds.includes(course.id) ? "border-emerald-500/50 bg-emerald-500/5" : "border-white/5"
                        }`}
                    >
                       <div className="flex justify-between items-center mb-10">
                          <span className="px-4 py-1.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-black rounded-xl uppercase tracking-widest italic">
                             {course.platform || 'Academy'}
                          </span>
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${
                              selectedCourseIds.includes(course.id) ? "bg-emerald-500 text-white" : "bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-500 group-hover:text-white"
                          }`}>
                             {selectedCourseIds.includes(course.id) ? <CheckCircle2 size={20} /> : <ChevronRight size={20} />}
                          </div>
                       </div>
                       <h4 className="text-2xl font-black text-white italic mb-10 leading-tight group-hover:text-indigo-400 transition-colors line-clamp-2">{course.title}</h4>
                       <div className="flex items-center justify-between pt-8 border-t border-white/5 mt-auto">
                          <div className="flex items-center gap-2 text-slate-500 text-xs font-bold italic uppercase tracking-tighter">
                             <Clock size={16} /> ~{course.duration_hours || '12'} Giờ học
                          </div>
                          <a 
                            href={course.url} 
                            target="_blank" 
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-white font-black text-[10px] bg-indigo-600/10 border border-indigo-600/20 hover:bg-indigo-600 px-4 py-2 rounded-xl transition-all uppercase tracking-widest"
                          >
                            Explore
                          </a>
                       </div>
                    </div>
                  ))}
               </div>
            </section>

            {/* User Feedback Section */}
            {!feedbackSubmitted ? (
                <section className="mt-10 bg-white/[0.03] backdrop-blur-3xl border border-white/10 rounded-[3rem] p-12 text-center relative overflow-hidden group">
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
                                <Sparkles size={24} fill={feedbackRating >= star ? "currentColor" : "none"} />
                            </button>
                        ))}
                    </div>

                    <textarea 
                        value={feedbackComment}
                        onChange={(e) => setFeedbackComment(e.target.value)}
                        placeholder="Có kỹ năng nào AI bóc tách chưa chuẩn không? Hãy góp ý để chúng tôi cải thiện..."
                        className="w-full max-w-2xl mx-auto block p-4 bg-white/5 border border-white/10 rounded-2xl text-white text-sm outline-none focus:border-indigo-500 transition-all mb-6 h-28"
                    />

                    <button 
                        onClick={submitFeedback}
                        disabled={feedbackRating === 0}
                        className="px-12 py-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-20 text-white font-black text-sm italic rounded-full transition-all shadow-xl"
                    >
                        SUBMIT FEEDBACK
                    </button>
                </section>
            ) : (
                <section className="mt-10 bg-emerald-500/10 border border-emerald-500/20 rounded-[3rem] p-12 text-center animate-in zoom-in duration-500">
                    <CheckCircle2 size={48} className="text-emerald-400 mx-auto mb-4" />
                    <h3 className="text-xl font-black text-white italic">CẢM ƠN BẠN ĐÃ ĐÓNG GÓP!</h3>
                    <p className="text-emerald-400/60 text-sm font-bold italic">Ý kiến của bạn giúp hệ thống AI thông minh hơn mỗi ngày.</p>
                </section>
            )}

          </div>
        )}
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

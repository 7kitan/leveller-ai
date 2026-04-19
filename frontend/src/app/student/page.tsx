"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import { 
  Cpu, 
  Terminal, 
  Target, 
  ChevronRight, 
  Box, 
  Database,
  ArrowUpRight,
  TrendingUp,
  Workflow,
  Compass,
  Layers,
  Sparkles,
  Zap,
  AlertCircle,
  ShieldCheck,
  CheckCircle2
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import styles from "./student.module.css";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";

const DashboardSkeleton = () => (
  <div className={styles.pageRoot}>
    <section className={styles.welcomeSection}>
      <div className={styles.headerInfo}>
        <div className={cn(styles.skeleton)} style={{ width: '120px', height: '24px', borderRadius: '1.25rem' }} />
        <div className={cn(styles.skeleton)} style={{ width: '300px', height: '80px', margin: '1rem 0' }} />
        <div className={cn(styles.skeleton)} style={{ width: '400px', height: '40px' }} />
      </div>
      <div className={styles.quickStats}>
        <div className={styles.statItem}>
           <div className={cn(styles.skeleton)} style={{ width: '60px', height: '40px' }} />
           <div className={cn(styles.skeleton)} style={{ width: '80px', height: '12px' }} />
        </div>
        <div className={styles.statItem}>
           <div className={cn(styles.skeleton)} style={{ width: '60px', height: '40px' }} />
           <div className={cn(styles.skeleton)} style={{ width: '80px', height: '12px' }} />
        </div>
      </div>
    </section>

    <div className={styles.mainGrid}>
      <div className={styles.mainContentArea}>
        <div className={styles.sectionHeader}>
           <div className={cn(styles.skeleton)} style={{ width: '200px', height: '32px' }} />
        </div>
        <div className={styles.skillGrid}>
          {[1, 2, 3].map(i => (
            <div key={i} className={cn(styles.skillCard, styles.skeleton)} style={{ height: '240px' }} />
          ))}
        </div>
      </div>
      <div className={styles.sidebarStack}>
        <div className={cn(styles.sphereWidget, styles.skeleton)} style={{ height: '300px' }} />
        <div className={cn(styles.roadmapPanel, styles.skeleton)} style={{ height: '400px' }} />
      </div>
    </div>
  </div>
);

// Radar Chart Component (SVG based)
const RadarChart = ({ currentData, potentialData, labels }: { currentData: number[], potentialData?: number[], labels: string[] }) => {
  const size = 300;
  const center = size / 2;
  const radius = size * 0.35;
  const angleStep = (Math.PI * 2) / labels.length;

  const getPath = (data: number[]) => {
    return data.map((val, i) => {
      const x = center + radius * (val / 100) * Math.cos(angleStep * i - Math.PI / 2);
      const y = center + radius * (val / 100) * Math.sin(angleStep * i - Math.PI / 2);
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ') + ' Z';
  };

  return (
    <div className={styles.radarContainer}>
      <svg viewBox={`0 0 ${size} ${size}`} className={styles.radarSvg}>
        {/* Grid Circles */}
        {[0.2, 0.4, 0.6, 0.8, 1].map(r => (
          <circle key={r} cx={center} cy={center} r={radius * r} className={styles.radarGrid} />
        ))}
        {/* Axes */}
        {labels.map((label, i) => {
          const x = center + radius * Math.cos(angleStep * i - Math.PI / 2);
          const y = center + radius * Math.sin(angleStep * i - Math.PI / 2);
          const labelX = center + (radius + 20) * Math.cos(angleStep * i - Math.PI / 2);
          const labelY = center + (radius + 20) * Math.sin(angleStep * i - Math.PI / 2);
          return (
            <g key={i}>
              <line x1={center} y1={center} x2={x} y2={y} className={styles.radarAxis} />
              <text x={labelX} y={labelY} className={styles.radarLabel}>{label}</text>
            </g>
          );
        })}
        {/* Data Polygons */}
        {potentialData && <path d={getPath(potentialData)} className={styles.radarPolygonPotential} />}
        <path d={getPath(currentData)} className={styles.radarPolygonCurrent} />
      </svg>
    </div>
  );
};

const StudentDashboard = () => {
  const router = useRouter();
  const [activeSkill, setActiveSkill] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [simData, setSimData] = useState<any>(null);
  const [simulating, setSimulating] = useState(false);
  const { user, token } = useAuth();

  useEffect(() => {
    const fetchLatestAnalysis = async () => {
      if (!token || !user) return;
      
      try {
        const response = await axios.get("/api/analysis/user/latest", {
          headers: {
            "Authorization": `Bearer ${token}`,
            "X-User-ID": user.id
          }
        });
        if (response.data) {
          setAnalysis(response.data);
        } else {
          setAnalysis(null);
        }
      } catch (err: any) {
        console.error("Failed to fetch latest analysis:", err);
        setAnalysis(null);
      } finally {
        setTimeout(() => setLoading(false), 800);
      }
    };

    fetchLatestAnalysis();
  }, [token, user]);

  const handleSimulate = async (courseId: string) => {
    if (!analysis || !token || !user) return;
    setSimulating(true);
    try {
      const cv_id = analysis.cv_id || analysis.cv_parsed_json?.id;
      const resp = await axios.post("/api/analysis/simulate-boost", {
          cv_id: cv_id,
          selected_course_ids: [courseId],
          job_id: analysis.job_id
      }, {
          headers: {
              "Authorization": `Bearer ${token}`,
              "X-User-ID": user.id
          }
      });
      setSimData(resp.data);
    } catch (err) {
      console.error("Simulation failed:", err);
    } finally {
      setSimulating(false);
    }
  };

  const clearSimulation = () => setSimData(null);

  if (loading) {
    return (
      <AuthGuard>
        <DashboardSkeleton />
      </AuthGuard>
    );
  }

  // Zero State: No analysis found
  if (!analysis) {
    return (
      <AuthGuard>
        <div className={styles.pageRoot}>
          <div className={styles.emptyStateContainer}>
            <div className={styles.emptyStateContent}>
              <div className={styles.emptyStateDecoration} />
              <div className={styles.emptyStateIconBox}>
                 <Sparkles size={48} />
              </div>
              
              <div className={styles.emptyStateText}>
                <h1 className={styles.emptyStateTitle}>
                  THE<br />
                  <span className={styles.nexusText}>GENOME WAITS.</span>
                </h1>
                <p className={styles.emptyStateSub}>
                  Lộ trình nghề nghiệp của bạn đang được ẩn giấu. Hãy để AI của Lumix giải mã bộ kỹ năng và ánh xạ tương lai của bạn ngay bây giờ.
                </p>
              </div>

              <div className={styles.emptySteps}>
                <div className={styles.emptyStepItem}>
                  <div className={styles.emptyStepIcon}>01</div>
                  <span className={styles.emptyStepLabel}>Tải lên CV</span>
                </div>
                <div className={styles.emptyStepItem}>
                  <div className={styles.emptyStepIcon}>02</div>
                  <span className={styles.emptyStepLabel}>AI Đánh giá Gap</span>
                </div>
                <div className={styles.emptyStepItem}>
                   <div className={styles.emptyStepIcon}>03</div>
                   <span className={styles.emptyStepLabel}>Nhận lộ trình</span>
                </div>
              </div>

              <button 
                onClick={() => router.push("/user/cv")}
                className={styles.ctaButton}
              >
                BẮT ĐẦU PHÂN TÍCH CV <ArrowUpRight size={24} />
              </button>
            </div>
          </div>
        </div>
      </AuthGuard>
    );
  }

  // Data processing for normal state
  const roadmapStages = analysis?.career_roadmap?.stages || [];
  const growthPath = roadmapStages.map((stage: any, idx: number) => ({
    step: stage.focus || stage.stage_name || `Giai đoạn ${stage.stage}`,
    status: idx === 0 ? "In-Progress" : "Upcoming",
    icon: idx === 0 ? Workflow : (idx === 1 ? Cpu : Box),
    summary: stage.summary || ""
  }));

  const roles = analysis?.target_roles || ["AI Solutions Architect", "Full-Stack Tech Lead"];
  const cvParsed = analysis?.cv_parsed || analysis?.cv_parsed_json || {};
  const currentSkills = (cvParsed.skills || []).slice(0, 3).map((s: any) => ({
    name: s.name,
    level: s.level || "Beginner",
    progress: s.level === "Expert" ? 95 : (s.level === "Advanced" ? 80 : (s.level === "Intermediate" ? 60 : 30))
  }));
  const matchPct = analysis?.overall_match_pct || 0;
  const potentialMatchPct = simData?.potential_score || matchPct;
  
  const isCvVerified = cvParsed.is_verified || false;
  const skillCount = (cvParsed.skills || []).length;

  // Skills by Category (for Radar Chart and Progress Bars)
  const categories = ["Technology", "Soft Skills", "Business", "Design", "Management"];
  const catMatch = categories.map(cat => {
    // Current match in this category (using CV skills)
    const catSkills = (cvParsed.skills || []).filter((s: any) => s.category?.toLowerCase() === cat.toLowerCase());
    // Basic logic: base 30% if any skill exists, plus 10% per skill, capped at 100%
    if (catSkills.length === 0) return 20; 
    return Math.min(100, 30 + catSkills.length * 15);
  });
  
  // Potential match (if simulation data exists)
  const potentialCatMatch = categories.map((cat, i) => {
    if (!simData) return catMatch[i];
    
    // Check if any filled skill belongs to this category
    const filledInCat = (simData.filled_skills || []).filter((s: any) => 
       (s.category || "Technology").toLowerCase() === cat.toLowerCase()
    );
    
    if (filledInCat.length === 0) return catMatch[i];
    // Boost based on number of filled skills in this category
    return Math.min(98, catMatch[i] + filledInCat.length * 12);
  });

  return (
    <AuthGuard>
      <div className={styles.pageRoot}>
        <section className={styles.welcomeSection}>
          <div className={styles.headerInfo}>
            <div className={styles.careerBadge}>
                <Target size={14} />
                <span>Career Logic v3.0</span>
            </div>
            <h1 className={styles.headerTitle}>
              THE<br />
              <span className={styles.nexusText}>NEXUS.</span>
            </h1>
            <p className={styles.headerSubtitle}>
               Chào mừng trở lại. AI đã phân tích sự phù hợp của bạn với thị trường.
               Hệ thống phát hiện <b>{analysis.skill_gaps?.length || 0}</b> khoảng trống tri thức trong lộ trình lên <b>{roles[0]}</b>.
            </p>
          </div>

          <div className={styles.quickStats}>
             <div className={styles.statItem}>
                <div className={styles.statValue}>
                   {simData ? simData.potential_score : Math.round(matchPct)}
                   {simData && <span className={styles.statBoost}> (+{simData.boost_amount})</span>}
                </div>
                <div className={styles.statLabel}>{simData ? "POTENTIAL MATCH %" : "MARKET FIT %"}</div>
             </div>
             <div className={styles.statItem}>
                <div className={styles.statValueAmber}>{analysis?.skill_gaps?.length || 0}</div>
                <div className={styles.statLabel}>GAPS FOUND</div>
             </div>
          </div>
        </section>

        <div className={styles.mainGrid}>
            <div className={styles.mainContentArea}>
                <div>
                   <div className={styles.sectionHeader}>
                      <h2 className={styles.sectionTitle}>
                        <Terminal size={24} className={styles.titleIconMuted} /> Core Matrix
                      </h2>
                      <div className={styles.sectionSubtitle}>
                         <Database size={12} /> Semantic Map Sync: Live
                      </div>
                   </div>

                   <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '3rem', alignItems: 'center', marginBottom: '3rem' }}>
                      <RadarChart 
                        labels={categories} 
                        currentData={catMatch} 
                        potentialData={simData ? potentialCatMatch : undefined} 
                      />
                      
                      <div className={styles.categorySection}>
                         {categories.map((cat, i) => (
                            <div key={cat} className={styles.categoryGroup}>
                               <div className={styles.categoryHeader}>
                                  <span className={styles.categoryTitle}>{cat}</span>
                                  <span className={styles.categoryTitle}>{catMatch[i]}%</span>
                               </div>
                               <div className={styles.progressBarTrack} style={{ height: '0.25rem' }}>
                                  <motion.div 
                                    className={styles.progressBarFill}
                                    style={{ background: i % 2 === 0 ? 'linear-gradient(to right, #fbbf24, #f59e0b)' : 'linear-gradient(to right, #06b6d4, #0891b2)' }}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${catMatch[i]}%` }}
                                  />
                               </div>
                            </div>
                         ))}
                      </div>
                   </div>

                   <div className={styles.skillGrid}>
                      {currentSkills.length > 0 ? currentSkills.map((skill: any) => (
                         <div 
                            key={skill.name} 
                            onClick={() => setActiveSkill(activeSkill === skill.name ? null : skill.name)}
                            className={cn(styles.skillCard, activeSkill === skill.name && styles.skillCardActive)}
                         >
                             <div className={styles.cardIconWrapper}>
                                <div className={cn(styles.iconBox, styles.iconAmber)}>
                                   <Cpu size={24} />
                                 </div>
                                 <span className={styles.levelBadge}>{skill.level}</span>
                             </div>
                            
                            <h3 className={styles.skillTitle}>{skill.name}</h3>

                            <div className={styles.progressContainer}>
                               <div className={styles.progressLabel}>
                                  <span>Expertise Level</span>
                                  <span>{skill.progress}%</span>
                               </div>
                               <div className={styles.progressBarTrack}>
                                  <motion.div 
                                    className={styles.progressBarFill}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${skill.progress}%` }}
                                  />
                               </div>
                            </div>

                            <AnimatePresence>
                               {activeSkill === skill.name && (
                                  <motion.div 
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: "auto", opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className={styles.drillDownPanel}
                                  >
                                     <div className={styles.drillDownTitle}>Target Roles requiring this</div>
                                     <div className={styles.roleBadgeGroup}>
                                        {roles.map((r: any) => (
                                           <span key={r} className={styles.roleBadge}>
                                              <TrendingUp size={10} /> {r}
                                           </span>
                                        ))}
                                     </div>

                                       {/* AI CV Suggester */}
                                      {analysis.skill_gaps?.find((g: any) => g.skill.toLowerCase() === skill.name.toLowerCase()) && (
                                        <div className={styles.aiSuggesterBox}>
                                          <div className={styles.aiSuggesterTitle}>
                                            <Sparkles size={12} />
                                            <span>AI CV Suggester</span>
                                          </div>
                                          <p className={styles.aiSuggesterText}>
                                            {analysis.skill_gaps.find((g: any) => g.skill.toLowerCase() === skill.name.toLowerCase()).learning_path || 
                                             `Tối ưu hóa kinh nghiệm với ${skill.name} để lấp đầy khoảng cách kỹ năng trong lộ trình nghề nghiệp.`}
                                          </p>
                                          <button 
                                            onClick={() => {
                                              const text = analysis.skill_gaps.find((g: any) => g.skill.toLowerCase() === skill.name.toLowerCase()).learning_path;
                                              navigator.clipboard.writeText(text);
                                            }}
                                            className={styles.copySuggesterBtn}
                                          >
                                            Copy to Clipboard
                                          </button>
                                        </div>
                                      )}

                                      {/* AI Explainability / Reasoning */}

                                      {analysis.skill_gaps?.find((g: any) => g.skill.toLowerCase() === skill.name.toLowerCase())?.reasoning && (
                                        <div className={styles.aiReasoningBox}>
                                          <div className={styles.aiReasoningHeader}>
                                            <Sparkles size={12} className={styles.sparkleIcon} />
                                            <span>AI INSIGHT</span>
                                          </div>
                                          <p className={styles.aiReasoningText}>
                                            {analysis.skill_gaps.find((g: any) => g.skill.toLowerCase() === skill.name.toLowerCase()).reasoning}
                                          </p>
                                        </div>
                                      )}

                                      <Link href="/student/courses" className={styles.courseItem}>
                                         <span className={styles.nodeOptimizeLink}>Optimize this node</span>
                                         <ChevronRight size={14} className={styles.iconAmberSmall} />
                                      </Link>
                                  </motion.div>
                               )}
                            </AnimatePresence>
                         </div>
                      )) : (
                        <div className={styles.emptyCard}>
                           <p>Chưa có dữ liệu kỹ năng. Hãy bắt đầu phân tích Gap để thấy Core Matrix của bạn.</p>
                        </div>
                      )}
                   </div>
                </div>

                <div>
                    <div className={styles.sectionHeader}>
                        <h2 className={styles.sectionTitle}>
                          <Sparkles size={24} className={styles.titleIconCyan} /> Knowledge Booster
                        </h2>
                       <Link href="/student/courses" className={styles.sectionSubtitle}>
                          VIEW ALL <ArrowUpRight size={12} />
                       </Link>
                    </div>

                     <div className={styles.coursesWrapper}>
                        {analysis?.course_recommendations?.slice(0, 2).map((course: any, idx: number) => (
                           <div 
                              key={idx} 
                              className={styles.courseCardSmall}
                              onMouseEnter={() => handleSimulate(course.course_id || course.id)}
                              onMouseLeave={clearSimulation}
                           >
                               <div className={styles.courseHeaderSmall}>
                                  <span className={styles.complexityBadge}>{course.level}</span>
                                  <span className={styles.coursePlatform}>{course.platform}</span>
                               </div>
                              <h3 className={styles.courseTitleSmall}>{course.title}</h3>
                               <div className={styles.courseFooter}>
                                  <div className={styles.badge}>
                                     <div className={cn(styles.badgeDot, styles.badgeDotCyan)} />
                                     <span className={styles.badgeLabel}>Boost Fit +{Math.round(course.similarity * 20)}%</span>
                                  </div>
                                 <button onClick={() => window.open(course.url, '_blank')} className={styles.enrollBtn}>Enroll Now <ArrowUpRight size={14} /></button>
                              </div>
                           </div>
                        )) || (
                          <div className={styles.emptyCourses}>
                             <p>Tải CV lên để nhận gợi ý khóa học tối ưu lộ trình.</p>
                          </div>
                        )}
                    </div>
                </div>
            </div>

              <div className={styles.sidebarStack}>
                {/* Readiness Score removed per user request */}

               <div className={styles.roadmapPanel}>
                   <h3 className={cn(styles.sectionTitle, styles.roadmapTitle)}>
                     <Compass size={20} className={styles.compassIcon} /> Learning Path
                   </h3>
                  
                  <div className={styles.roadmapLine} />

                   <div className={styles.roadmapSteps}>
                     {growthPath.length > 0 ? growthPath.map((item: any, idx: number) => (
                         <div key={idx} className={styles.stepItem}>
                            <div className={cn(
                                styles.stepIconBox, 
                                item.status === 'In-Progress' ? styles.stepIconProgress : styles.stepIconUpcoming
                            )}>
                               <item.icon size={20} />
                            </div>
                            <div className={styles.stepTextWrapper}>
                               <div className={cn(
                                   styles.stepStatus,
                                   item.status === 'In-Progress' ? styles.stepStatusProgress : styles.stepStatusUpcoming
                               )}>{item.status}</div>
                               <h4 className={styles.stepTitle}>{item.step}</h4>
                            </div>
                         </div>
                     )) : (
                       <p className={styles.emptyRoadmap}>Chưa có lộ trình học tập.</p>
                     )}
                  </div>

                   {analysis?.career_roadmap?.stages?.[0] && (
                     <div className={styles.milestoneCard}>
                        <div className={styles.milestoneHeader}>
                           <Layers size={16} className={styles.layersIcon} />
                           <span className={styles.milestoneLabel}>Current Focus</span>
                        </div>
                        <p className={styles.milestoneText}>{analysis.career_roadmap.stages[0].summary || analysis.career_roadmap.summary}</p>
                     </div>
                   )}
               </div>
            </div>
        </div>
      </div>
    </AuthGuard>
  );
};

export default StudentDashboard;

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
import { useLanguage } from "@/context/LanguageContext";

/* ========================================
 * CONSTANTS
 * Magic numbers and configuration values
 * ======================================== */

const SKILL_LEVELS = {
  Expert: { progress: 95, label: "Expert" },
  Advanced: { progress: 80, label: "Advanced" },
  Intermediate: { progress: 60, label: "Intermediate" },
  Beginner: { progress: 30, label: "Beginner" },
} as const;

const SKILL_MATCH_CONFIG = {
  basePercentage: 30,
  perSkillBonus: 15,
  maxPercentage: 100,
  emptySkillsDefault: 20,
} as const;

const SIMULATION_CONFIG = {
  boostPerSkill: 12,
  maxBoostCap: 98,
} as const;

const RADAR_CHART = {
  size: 300,
  radiusMultiplier: 0.35,
  labelOffset: 20,
} as const;

const CATEGORIES = ["Technology", "Soft Skills", "Business", "Design", "Management"] as const;

const LOADING_DELAY_MS = 800;

/* ========================================
 * TYPE DEFINITIONS
 * For better type safety
 * ======================================== */

interface SkillData {
  name: string;
  level: string;
  progress: number;
}

interface CategoryMatch {
  category: string;
  current: number;
  potential: number;
}

interface CareerStage {
  step: string;
  status: "In-Progress" | "Upcoming";
  icon: React.ElementType;
  summary: string;
}

interface AnalysisData {
  cv_id?: string;
  cv_parsed?: SkillSourceData;
  cv_parsed_json?: SkillSourceData;
  job_id?: string;
  career_roadmap?: CareerRoadmap;
  skill_gaps?: SkillGap[];
  target_roles?: string[];
  overall_match_pct?: number;
  course_recommendations?: CourseRecommendation[];
}

interface SkillSourceData {
  id?: string;
  skills?: SkillSource[];
  is_verified?: boolean;
}

interface SkillSource {
  name: string;
  level?: string;
  category?: string;
}

interface CareerRoadmap {
  stages?: CareerStageData[];
  summary?: string;
}

interface CareerStageData {
  focus?: string;
  stage_name?: string;
  stage?: number;
  summary?: string;
}

interface SkillGap {
  skill: string;
  reasoning?: string;
  learning_path?: string;
}

interface CareerRoadmapData {
  stages?: CareerStage[];
}

interface CourseRecommendation {
  course_id?: string;
  id?: string;
  title: string;
  level: string;
  platform: string;
  url: string;
  similarity: number;
}

interface SimulationResult {
  potential_score?: number;
  boost_amount?: number;
  filled_skills?: { category?: string }[];
}

/* ========================================
 * HELPER FUNCTIONS
 * Data transformations and utilities
 * ======================================== */

function getSkillProgressLevel(level: string | undefined): number {
  const levelConfig = SKILL_LEVELS[level as keyof typeof SKILL_LEVELS];
  return levelConfig?.progress ?? SKILL_LEVELS.Beginner.progress;
}

function calculateCategoryMatch(skills: SkillSource[], category: string): number {
  const normalizedCategory = category.toLowerCase();
  
  const categorySkills = skills.filter(s => {
    const skillCategory = s.category?.toLowerCase();
    // Only match skills that explicitly have this category
    // Skills without category are excluded (not auto-assigned to Technology)
    return skillCategory === normalizedCategory;
  });
  
  if (categorySkills.length === 0) return SKILL_MATCH_CONFIG.emptySkillsDefault;
  
  return Math.min(
    SKILL_MATCH_CONFIG.maxPercentage,
    SKILL_MATCH_CONFIG.basePercentage + categorySkills.length * SKILL_MATCH_CONFIG.perSkillBonus
  );
}

function calculatePotentialCategoryMatch(
  currentMatch: number, 
  filledSkills: { category?: string }[], 
  category: string
): number {
  const normalizedCategory = category.toLowerCase();
  
  const filledInCategory = filledSkills.filter(s => {
    const skillCategory = s.category?.toLowerCase();
    return skillCategory === normalizedCategory;
  });
  
  if (filledInCategory.length === 0) return currentMatch;
  
  return Math.min(
    SIMULATION_CONFIG.maxBoostCap,
    currentMatch + filledInCategory.length * SIMULATION_CONFIG.boostPerSkill
  );
}

function transformRoadmapStages(stages: CareerStageData[]): CareerStage[] {
  return stages.map((stage, idx) => ({
    step: stage.focus ?? stage.stage_name ?? `Giai đoạn ${stage.stage}`,
    status: idx === 0 ? "In-Progress" : "Upcoming",
    icon: idx === 0 ? Workflow : (idx === 1 ? Cpu : Box),
    summary: stage.summary ?? ""
  }));
}

function transformSkills(skills: SkillSource[]): SkillData[] {
  return skills.slice(0, 3).map(s => ({
    name: s.name,
    level: s.level ?? "Beginner",
    progress: getSkillProgressLevel(s.level)
  }));
}

function extractCvData(analysis: AnalysisData): SkillSourceData {
  return analysis.cv_parsed ?? analysis.cv_parsed_json ?? {};
}

/* ========================================
 * SKELETON COMPONENT
 * Loading state placeholder
 * ======================================== */

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

/* ========================================
 * RADAR CHART COMPONENT
 * Extracted for reusability and clarity
 * ======================================== */

function RadarChart({ 
  currentData, 
  potentialData, 
  labels 
}: { 
  currentData: number[]; 
  potentialData?: number[]; 
  labels: readonly string[]; 
}) {
  const { size, radiusMultiplier, labelOffset } = RADAR_CHART;
  const center = size / 2;
  const radius = size * radiusMultiplier;
  const angleStep = (Math.PI * 2) / labels.length;

  const getPath = (data: number[]): string => {
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
          const labelX = center + (radius + labelOffset) * Math.cos(angleStep * i - Math.PI / 2);
          const labelY = center + (radius + labelOffset) * Math.sin(angleStep * i - Math.PI / 2);
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
}

/* ========================================
 * MAIN DASHBOARD COMPONENT
 * ======================================== */

const StudentDashboard = () => {
  const router = useRouter();
  const [activeSkill, setActiveSkill] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [simData, setSimData] = useState<any>(null);
  const [simulating, setSimulating] = useState(false);
  const { user, token } = useAuth();
  const { t, language } = useLanguage();

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
        setTimeout(() => setLoading(false), LOADING_DELAY_MS);
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
                  <span className={styles.nexusText}>{t("student_empty_title").split('.')[0]}</span>
                </h1>
                <p className={styles.emptyStateSub}>
                  {t("student_empty_sub")}
                </p>
              </div>

              <div className={styles.emptySteps}>
                <div className={styles.emptyStepItem}>
                   <div className={styles.emptyStepIcon}>01</div>
                   <span className={styles.emptyStepLabel}>{t("student_step_upload")}</span>
                </div>
                <div className={styles.emptyStepItem}>
                   <div className={styles.emptyStepIcon}>02</div>
                   <span className={styles.emptyStepLabel}>{t("student_step_gap")}</span>
                </div>
                <div className={styles.emptyStepItem}>
                    <div className={styles.emptyStepIcon}>03</div>
                    <span className={styles.emptyStepLabel}>{t("student_step_roadmap")}</span>
                </div>
              </div>

              <button 
                onClick={() => router.push("/user/cv")}
                 className={styles.ctaButton}
               >
                 {t("student_btn_start")} <ArrowUpRight size={24} />
               </button>
            </div>
          </div>
        </div>
      </AuthGuard>
    );
  }

  // ----- DATA TRANSFORMATIONS USING HELPER FUNCTIONS -----
  
  // Transform career roadmap into display-friendly format
  const roadmapStages = analysis?.career_roadmap?.stages || [];
  const growthPath = transformRoadmapStages(roadmapStages);

  // Get target roles with defaults
  const roles = analysis?.target_roles || ["AI Solutions Architect", "Full-Stack Tech Lead"];
  
  // Extract CV data from analysis response
  const cvParsed = extractCvData(analysis);
  
  // Transform skills for display
  const currentSkills = transformSkills(cvParsed.skills || []);
  
  // Match percentages
  const matchPct = analysis?.overall_match_pct ?? 0;
  const potentialMatchPct = simData?.potential_score ?? matchPct;
  
  const isCvVerified = cvParsed.is_verified ?? false;
  const skillCount = (cvParsed.skills || []).length;

  // Calculate category match percentages for Radar Chart
  const cvSkills = cvParsed.skills || [];
  const catMatch = CATEGORIES.map(cat => calculateCategoryMatch(cvSkills, cat));
  
  // Calculate potential category match (with simulation boost)
  const potentialCatMatch = CATEGORIES.map((cat, i) => {
    if (!simData) return catMatch[i];
    return calculatePotentialCategoryMatch(catMatch[i], simData.filled_skills || [], cat);
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
               <span className={styles.nexusText}>NEXUS</span>
             </h1>
             <p className={styles.headerSubtitle}>
                {t("student_welcome_back")}
                <br/>
                {t("student_detected_gaps").replace('các khoảng trống', (analysis.skill_gaps?.length || 0).toString() + ' khoảng trống')} <b>{roles[0]}</b>.
             </p>
          </div>

          <div className={styles.quickStats}>
             <div className={styles.statItem}>
                <div className={styles.statValue}>
                   {simData ? simData.potential_score : Math.round(matchPct)}
                   {simData && <span className={styles.statBoost}> (+{simData.boost_amount})</span>}
                </div>
                 <div className={styles.statLabel}>{simData ? t("student_potential_match") : t("student_fit_market")}</div>
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
                         <Terminal size={24} className={styles.titleIconMuted} /> {t("student_core_matrix")}
                       </h2>
                       <div className={styles.sectionSubtitle}>
                          <Database size={12} /> {t("student_semantic_map")}
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
                                   <span>{t("student_expertise_level")}</span>
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
                                      <div className={styles.drillDownTitle}>{t("student_target_roles_req")}</div>
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
                                             <span>{t("student_ai_suggester")}</span>
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
                                           {t("copy_to_clipboard") || "Copy to Clipboard"}
                                          </button>
                                        </div>
                                      )}

                                      {/* AI Explainability / Reasoning */}

                                      {analysis.skill_gaps?.find((g: any) => g.skill.toLowerCase() === skill.name.toLowerCase())?.reasoning && (
                                        <div className={styles.aiReasoningBox}>
                                           <div className={styles.aiReasoningHeader}>
                                             <Sparkles size={12} className={styles.sparkleIcon} />
                                             <span>{t("student_ai_insight")}</span>
                                           </div>
                                          <p className={styles.aiReasoningText}>
                                            {analysis.skill_gaps.find((g: any) => g.skill.toLowerCase() === skill.name.toLowerCase()).reasoning}
                                          </p>
                                        </div>
                                      )}

                                       <Link href="/student/courses" className={styles.courseItem}>
                                          <span className={styles.nodeOptimizeLink}>{t("student_optimize_node")}</span>
                                          <ChevronRight size={14} className={styles.iconAmberSmall} />
                                       </Link>
                                  </motion.div>
                               )}
                            </AnimatePresence>
                         </div>
                      )) : (
                         <div className={styles.emptyCard}>
                            <p>{t("cv_no_skills")}</p>
                         </div>
                      )}
                   </div>
                </div>

                <div>
                    <div className={styles.sectionHeader}>
                         <h2 className={styles.sectionTitle}>
                           <Sparkles size={24} className={styles.titleIconCyan} /> {t("student_knowledge_booster")}
                         </h2>
                        <Link href="/student/courses" className={styles.sectionSubtitle}>
                           {t("student_view_all_courses")} <ArrowUpRight size={12} />
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
                                      <span className={styles.badgeLabel}>{t("student_boost_fit")} +{Math.round(course.similarity * 20)}%</span>
                                   </div>
                                  <button onClick={() => window.open(course.url, '_blank')} className={styles.enrollBtn}>{t("student_enroll_now")} <ArrowUpRight size={14} /></button>
                               </div>
                           </div>
                        )) || (
                           <div className={styles.emptyCourses}>
                              <p>{t("dash_no_gaps")}</p>
                           </div>
                        )}
                    </div>
                </div>
            </div>

              <div className={styles.sidebarStack}>
                {/* Readiness Score removed per user request */}

               <div className={styles.roadmapPanel}>
                    <h3 className={cn(styles.sectionTitle, styles.roadmapTitle)}>
                      <Compass size={20} className={styles.compassIcon} /> {t("student_learning_path")}
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
                        <p className={styles.emptyRoadmap}>{t("roadmap_empty")}</p>
                     )}
                  </div>

                   {analysis?.career_roadmap?.stages?.[0] && (
                     <div className={styles.milestoneCard}>
                        <div className={styles.milestoneHeader}>
                            <Layers size={16} className={styles.layersIcon} />
                            <span className={styles.milestoneLabel}>{t("student_current_focus")}</span>
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

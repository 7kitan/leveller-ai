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
  Zap
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import styles from "./student.module.css";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";

const StudentDashboard = () => {
  const router = useRouter();
  const [activeSkill, setActiveSkill] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
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
        setLoading(false);
      }
    };

    fetchLatestAnalysis();
  }, [token, user]);

  if (loading) {
    return (
      <AuthGuard>
        <div className={styles.pageRoot}>
          <div className={styles.loadingContainer}>
            <div className={styles.spinner}></div>
            <p>Đang tải ma trận tri thức...</p>
          </div>
        </div>
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
                onClick={() => router.push("/user/analysis")}
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
                <div className={styles.statValue}>{Math.round(matchPct)}</div>
                <div className={styles.statLabel}>MARKET FIT %</div>
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
                           <div key={idx} className={styles.courseCardSmall}>
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
               <div className={styles.sphereWidget}>
                  <div className={styles.sphereContainer}>
                     <div className={styles.outerRing}></div>
                     <div className={styles.innerRing}></div>
                      <div className={styles.sphereCore}>
                         <Zap size={32} className={styles.zapIconCore} />
                      </div>
                      <div className={cn(styles.graphPoint, styles.graphPointFrontend)}>
                         <span className={cn(styles.contextLabel, styles.contextLabelTop)}>Foundations</span>
                      </div>
                      <div className={cn(styles.graphPoint, styles.graphPointAI)}>
                         <span className={cn(styles.contextLabel, styles.contextLabelBottom)}>Expertise</span>
                      </div>
                  </div>
                   <div>
                     <h3 className={styles.graphSyncTitle}>Graph Sync</h3>
                     <p className={styles.graphSyncDesc}>Hồ sơ của bạn đang đồng bộ với <b>8,421</b> node tri thức thực tế của ngành AI.</p>
                   </div>
               </div>

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

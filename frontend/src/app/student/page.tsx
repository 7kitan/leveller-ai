"use client";

import React, { useState } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import { 
  Cpu, 
  Terminal, 
  Globe, 
  Zap, 
  Target, 
  ChevronRight, 
  Box, 
  Database,
  Search,
  BookOpen,
  ArrowUpRight,
  TrendingUp,
  Layout,
  Workflow,
  Compass,
  Layers,
  Sparkles
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import styles from "./student.module.css";
import { motion, AnimatePresence } from "framer-motion";

const StudentDashboard = () => {
  const [activeSkill, setActiveSkill] = useState<string | null>(null);

  const personaContext = {
    roles: ["AI Solutions Architect", "Full-Stack Tech Lead"],
    currentSkills: [
      { name: "Next.js 15 (Turbopack)", level: "Architect", progress: 95 },
      { name: "PostgreSQL Optimizer", level: "Expert", progress: 85 },
      { name: "Semantic Search / RAG", level: "Advanced", progress: 78 }
    ],
    growthPath: [
      { step: "Graph Database Orchestration", status: "In-Progress", icon: Workflow },
      { step: "Agentic AI Reasoning", status: "Upcoming", icon: Cpu },
      { step: "Enterprise DevOps Mesh", status: "Locked", icon: Box }
    ]
  };

  return (
    <AuthGuard>
      <div className={styles.pageRoot}>
        {/* ── Welcome Section ────────────────────────────────────────── */}
        <section className={styles.welcomeSection}>
          <div className={styles.headerInfo}>
            <div className={styles.careerBadge}>
                <Target size={14} />
                <span>Career Logic v2.5</span>
            </div>
            <h1 className={styles.headerTitle}>
              THE<br />
              <span className={styles.nexusText}>NEXUS.</span>
            </h1>
            <p className={styles.headerSubtitle}>
               Chào mừng trở lại. AI đã ánh xạ 42 kỹ năng mới vào đồ thị nghề nghiệp của bạn.
               Hệ thống phát hiện 3 khoảng trống tri thức trong lộ trình lên <b>{personaContext.roles[0]}</b>.
            </p>
          </div>

          <div className={styles.quickStats}>
             <div className={styles.statItem}>
                <div className={styles.statValue}>89</div>
                <div className={styles.statLabel}>MARKET FIT %</div>
             </div>
             <div className={styles.statItem}>
                <div className={styles.statValueAmber}>12</div>
                <div className={styles.statLabel}>NEW NODES</div>
             </div>
          </div>
        </section>

        <div className={styles.mainGrid}>
            {/* ── Skills & Learning Focus ────────────────────────────────── */}
            <div className={styles.mainContentArea}>
                <div>
                   <div className={styles.sectionHeader}>
                      <h2 className={styles.sectionTitle}>
                        <Terminal size={24} style={{ color: "rgba(255,255,255,0.4)" }} /> Core Matrix
                      </h2>
                      <div className={styles.sectionSubtitle}>
                         <Database size={12} /> Semantic Map Sync: Live
                      </div>
                   </div>

                   <div className={styles.skillGrid}>
                      {personaContext.currentSkills.map((skill) => (
                         <div 
                            key={skill.name} 
                            onClick={() => setActiveSkill(activeSkill === skill.name ? null : skill.name)}
                            className={cn(styles.skillCard, activeSkill === skill.name && styles.skillCardActive)}
                         >
                            <div className={styles.cardIconWrapper}>
                               <div className={styles.iconBox} style={{ color: "#fbbf24" }}>
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
                                        {personaContext.roles.map(r => (
                                           <span key={r} className={styles.roleBadge}>
                                              <TrendingUp size={10} /> {r}
                                           </span>
                                        ))}
                                     </div>
                                     <Link href="/student/courses" className={styles.courseItem}>
                                        <span style={{ fontSize: "11px", fontWeight: 900, color: "white" }}>Optimize this node</span>
                                        <ChevronRight size={14} style={{ color: "#fbbf24" }} />
                                     </Link>
                                  </motion.div>
                               )}
                            </AnimatePresence>
                         </div>
                      ))}
                   </div>
                </div>

                {/* Recommendations Widget */}
                <div>
                    <div className={styles.sectionHeader}>
                       <h2 className={styles.sectionTitle}>
                         <Sparkles size={24} style={{ color: "#22d3ee" }} /> Knowledge Booster
                       </h2>
                       <Link href="/student/courses" className={styles.sectionSubtitle}>
                          VIEW ALL <ArrowUpRight size={12} />
                       </Link>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "2rem" }}>
                        {[
                          { title: "Neo4j Graph Orchestration", platform: "Coursera", level: "Expert" },
                          { title: "Agentic Workflows with LangGraph", platform: "Udemy", level: "Advanced" }
                        ].map((course, idx) => (
                           <div key={idx} className={styles.courseCardSmall}>
                              <div className={styles.courseHeaderSmall}>
                                 <span className={styles.complexityBadge}>{course.level}</span>
                                 <span style={{ fontSize: "9px", color: "rgba(255,255,255,0.2)", fontWeight: 900 }}>{course.platform}</span>
                              </div>
                              <h3 className={styles.courseTitleSmall}>{course.title}</h3>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                 <div className={styles.badge}>
                                    <div className={styles.badgeDot} style={{ backgroundColor: "#22d3ee" }} />
                                    <span className={styles.badgeLabel}>Boost Fit +12%</span>
                                 </div>
                                 <button className={styles.enrollBtn}>Enroll Now <ArrowUpRight size={14} /></button>
                              </div>
                           </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* ── Sidebar: AI Roadmap & Career Insights ─────────────────── */}
            <div style={{ display: "flex", flexDirection: "column", gap: "3rem" }}>
               {/* Career Sphere Visualization Placeholder */}
               <div className={styles.sphereWidget}>
                  <div className={styles.sphereContainer}>
                     <div className={styles.outerRing}></div>
                     <div className={styles.innerRing}></div>
                     <div className={styles.sphereCore}>
                        <Zap size={32} style={{ color: "#8b5cf6" }} />
                     </div>
                     {/* Floating nodes */}
                     <div className={styles.point} style={{ top: "10%", left: "20%", background: "#fbbf24", boxShadow: "0 0 10px #fbbf24" }}>
                        <span className={styles.contextLabel} style={{ top: "-1.5rem" }}>Frontend</span>
                     </div>
                     <div className={styles.point} style={{ bottom: "20%", right: "15%", background: "#8b5cf6", boxShadow: "0 0 10px #8b5cf6" }}>
                        <span className={styles.contextLabel} style={{ bottom: "-1.5rem" }}>AI</span>
                     </div>
                  </div>
                  <div>
                    <h3 style={{ fontSize: "1.25rem", fontWeight: 900, color: "white", fontStyle: "italic", marginBottom: "1rem" }}>Graph Sync</h3>
                    <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.3)", lineHeight: 1.6 }}>Hồ sơ của bạn đang đồng bộ với <b>8,421</b> node tri thức thực tế của ngành AI.</p>
                  </div>
               </div>

               {/* Step-by-Step Roadmap */}
               <div className={styles.roadmapPanel}>
                  <h3 className={styles.sectionTitle} style={{ fontSize: "1.25rem", marginBottom: "3rem" }}>
                    <Compass size={20} style={{ color: "#8b5cf6" }} /> Learning Path
                  </h3>
                  
                  <div className={styles.roadmapLine} />

                  <div style={{ display: "flex", flexDirection: "column", gap: "4rem" }}>
                     {personaContext.growthPath.map((item, idx) => (
                        <div key={idx} className={styles.stepItem}>
                           <div className={styles.stepIconBox} style={{ background: item.status === 'In-Progress' ? '#8b5cf6' : 'rgba(255,255,255,0.03)', color: item.status === 'In-Progress' ? 'white' : 'rgba(255,255,255,0.2)' }}>
                              <item.icon size={20} />
                           </div>
                           <div style={{ paddingTop: "0.5rem" }}>
                              <div style={{ fontSize: "10px", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.15em", color: item.status === 'In-Progress' ? '#a78bfa' : 'rgba(255,255,255,0.2)', marginBottom: "0.5rem" }}>{item.status}</div>
                              <h4 style={{ fontSize: "1rem", fontWeight: 900, color: "white" }}>{item.step}</h4>
                           </div>
                        </div>
                     ))}
                  </div>

                  <div className={styles.milestoneCard}>
                     <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
                        <Layers size={16} style={{ color: "#8b5cf6" }} />
                        <span style={{ fontSize: "10px", fontWeight: 900, textTransform: "uppercase", color: "white" }}>Next Milestone</span>
                     </div>
                     <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", fontWeight: 500, fontStyle: "italic" }}>Hoàn thành "Graph Databases" để unlock vai trò Tech Lead tại 12 tập đoàn công nghệ.</p>
                  </div>
               </div>
            </div>
        </div>
      </div>
    </AuthGuard>
  );
};

export default StudentDashboard;

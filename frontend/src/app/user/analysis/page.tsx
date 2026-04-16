"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { 
  Cpu, 
  Sparkles,
  Zap,
  Layers,
  Search,
  Network
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./user-analysis.module.css";
import { motion, AnimatePresence } from "framer-motion";

const AnalysisPage = () => {
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState(0);
  const router = useRouter();

  const steps = [
    { title: "Bóc tách ngôn ngữ (NLP)", icon: Search },
    { title: "Ánh xạ Knowledge Graph", icon: Network },
    { title: "Phân tích khoảng cách (Gap Analysis)", icon: Layers },
    { title: "Đề xuất lộ trình tối ưu", icon: Zap },
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(timer);
          setTimeout(() => router.push("/user/recommend"), 800);
          return 100;
        }
        return prev + 1;
      });
    }, 40);

    return () => clearInterval(timer);
  }, [router]);

  useEffect(() => {
    if (progress < 25) setStep(0);
    else if (progress < 50) setStep(1);
    else if (progress < 75) setStep(2);
    else setStep(3);
  }, [progress]);

  return (
    <div className={styles.pageRoot}>
      <div className={styles.glowTop}></div>
      <div className={styles.glowBottom}></div>
      <div className={styles.textureOverlay}></div>

      {/* Main Content Area */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={styles.card}
      >
        <div className={styles.innerContent}>
            <div className={styles.badge}>
                <Sparkles size={12} />
                <span className={styles.badgeLabel}>Enterprise AI Analysis v2.0</span>
            </div>
            
            <h1 className={styles.title}>
                CAREER <span className={styles.gradientText}>GENOME.</span>
            </h1>

            {/* Spinner */}
            <div className={styles.spinnerContainer}>
                <div className={styles.spinnerOuter}></div>
                <div className={styles.spinnerInner}></div>
                <div className={styles.spinnerOverlay}>
                    <Cpu size={24} className={styles.cpuIcon} />
                </div>
            </div>

            {/* Status */}
            <div className={styles.statusGroup}>
                <p className={styles.statusText}>AI đang phân tích hồ sơ của bạn</p>
                <p className={styles.statusSubtext}>Quá trình này có thể mất vài giây để ánh xạ toàn bộ kỹ năng vào Graph...</p>
            </div>

            {/* Progress Bar */}
            <div className={styles.fullWidth}>
                <div className={styles.progressBar}>
                    <div 
                        className={styles.progressFill}
                        style={{ width: `${progress}%` }}
                    ></div>
                </div>
                
                <div className={styles.progressInfo}>
                    <div className={styles.flexCenterGap3}>
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={step}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 10 }}
                                className={styles.flexCenterGap3}
                                style={{ gap: "0.5rem" }}
                            >
                                {React.createElement(steps[step].icon, { size: 14, style: { color: "#818cf8" } })}
                                <span className={styles.stepTitle}>{steps[step].title}</span>
                            </motion.div>
                        </AnimatePresence>
                    </div>
                    <span className={styles.progressPercent}>{progress}%</span>
                </div>
            </div>
        </div>
      </motion.div>

      {/* Footer Decoration */}
      <div className={styles.footerDots}>
         {[1, 2, 3].map(i => (
            <div key={i} className={styles.dot} />
         ))}
      </div>
    </div>
  );
};

export default AnalysisPage;

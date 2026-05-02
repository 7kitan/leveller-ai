"use client";

import React, { useEffect, useState } from "react";
import styles from "./ScanningOverlay.module.css";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Cpu, Search, Database, CheckCircle } from "lucide-react";

interface ScanningOverlayProps {
  status: "idle" | "uploading" | "processing" | "viewing";
}

export const ScanningOverlay: React.FC<ScanningOverlayProps> = ({ status }) => {
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    { icon: <FileText className="w-5 h-5" />, label: "Đang nạp dữ liệu ứng viên..." },
    { icon: <Cpu className="w-5 h-5" />, label: "Khởi tạo AI Core: Chandra v3.0..." },
    { icon: <Search className="w-5 h-5" />, label: "Đang bóc tách thực thể (NER)..." },
    { icon: <Database className="w-5 h-5" />, label: "Đang truy vấn Market Skills Index..." },
    { icon: <CheckCircle className="w-5 h-5" />, label: "Đang đồng bộ hóa kết quả..." },
  ];

  useEffect(() => {
    if (status === "processing") {
      const interval = setInterval(() => {
        setActiveStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
      }, 3000);
      return () => clearInterval(interval);
    } else {
      setActiveStep(0);
    }
  }, [status]);

  if (status !== "processing" && status !== "uploading") return null;

  return (
    <div className={styles.overlay}>
      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className={styles.scannerContainer}
      >
        <div className={styles.scannerGrid} />
        <div className={styles.scannerLine} />
        <div className={styles.scannerGlow} />
        
        {/* Particles */}
        {[...Array(25)].map((_, i) => (
          <motion.div 
            key={i} 
            className={styles.particle} 
            initial={{ 
              x: Math.random() * 320, 
              y: 440, 
              opacity: 0 
            }}
            animate={{ 
              y: -20, 
              opacity: [0, 1, 0] 
            }}
            transition={{ 
              duration: Math.random() * 3 + 2, 
              repeat: Infinity, 
              delay: Math.random() * 5 
            }}
            style={{ 
              width: `${Math.random() * 4 + 1}px`,
              height: `${Math.random() * 4 + 1}px`
            }} 
          />
        ))}

        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <motion.div
            animate={{ 
              rotate: [0, 360],
              opacity: [0.1, 0.3, 0.1]
            }}
            transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
            className="w-64 h-64 border border-cyan-500/20 rounded-full"
          />
          <motion.div
            animate={{ 
              rotate: [360, 0],
              opacity: [0.2, 0.4, 0.2]
            }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            className="w-48 h-48 border border-dashed border-cyan-400/30 rounded-full"
          />
        </div>
      </motion.div>

      <div className="text-center max-w-md px-6">
        <h2 className={styles.statusText}>
          {status === "uploading" ? "Đang tải lên hệ thống..." : "Hệ thống AI đang phân tích..."}
        </h2>
        
        <div className="mt-8 space-y-4">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeStep}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex items-center gap-4 bg-white/5 border border-white/10 rounded-xl px-6 py-4 backdrop-blur-md"
            >
              <div className="p-2 bg-cyan-500/20 rounded-lg text-cyan-400">
                {steps[activeStep].icon}
              </div>
              <div className="text-left">
                <p className="text-sm font-medium text-white/90">{steps[activeStep].label}</p>
                <div className="mt-1 w-48 h-1 bg-white/10 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 3 }}
                    className="h-full bg-cyan-500"
                  />
                </div>
              </div>
            </motion.div>
          </AnimatePresence>

          <div className="flex justify-center gap-2 mt-4">
            {steps.map((_, i) => (
              <div 
                key={i}
                className={`w-2 h-2 rounded-full transition-colors duration-300 ${
                  i === activeStep ? 'bg-cyan-500' : i < activeStep ? 'bg-cyan-500/40' : 'bg-white/10'
                }`}
              />
            ))}
          </div>
        </div>
        
        <p className={styles.subText}>
          AI Engine: GPT-4o-mini | Strategy: Chandra v3.0
        </p>
      </div>
    </div>
  );
};

"use client";

import React from "react";
import styles from "./ScanningOverlay.module.css";
import { motion } from "framer-motion";

interface ScanningOverlayProps {
  status: "idle" | "uploading" | "processing" | "viewing";
}

export const ScanningOverlay: React.FC<ScanningOverlayProps> = ({ status }) => {
  if (status !== "processing" && status !== "uploading") return null;

  return (
    <div className={styles.overlay}>
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className={styles.scannerContainer}
      >
        <div className={styles.scannerGrid} />
        <div className={styles.scannerLine} />
        <div className={styles.scannerGlow} />
        
        {/* Particles */}
        {[...Array(15)].map((_, i) => (
          <motion.div 
            key={i} 
            className={styles.particle} 
            initial={{ 
              x: Math.random() * 500, 
              y: 700, 
              opacity: 0 
            }}
            animate={{ 
              y: -20, 
              opacity: [0, 1, 0] 
            }}
            transition={{ 
              duration: Math.random() * 2 + 1.5, 
              repeat: Infinity, 
              delay: Math.random() * 3 
            }}
            style={{ 
              width: `${Math.random() * 3 + 1}px`,
              height: `${Math.random() * 3 + 1}px`
            }} 
          />
        ))}
      </motion.div>
    </div>
  );
};

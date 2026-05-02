"use client";

import { motion } from 'framer-motion';
import styles from './ScanningOverlay.module.css';
import { useLanguage } from '@/context/LanguageContext';

interface ScanningOverlayProps {
  isScanning: boolean;
  progress?: number; // 0-100
}

export function ScanningOverlay({ isScanning, progress }: ScanningOverlayProps) {
  const { t } = useLanguage();
  
  if (!isScanning) return null;

  return (
    <div className={styles.scanningOverlay}>
      {/* Corner Brackets (QR Scanner Style) */}
      <div className={styles.cornerBrackets}>
        <motion.div 
          className={styles.cornerTL}
          animate={{ 
            opacity: [1, 0.4, 1],
            scale: [1, 1.05, 1]
          }}
          transition={{ 
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div 
          className={styles.cornerTR}
          animate={{ 
            opacity: [1, 0.4, 1],
            scale: [1, 1.05, 1]
          }}
          transition={{ 
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 0.5
          }}
        />
        <motion.div 
          className={styles.cornerBL}
          animate={{ 
            opacity: [1, 0.4, 1],
            scale: [1, 1.05, 1]
          }}
          transition={{ 
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1
          }}
        />
        <motion.div 
          className={styles.cornerBR}
          animate={{ 
            opacity: [1, 0.4, 1],
            scale: [1, 1.05, 1]
          }}
          transition={{ 
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1.5
          }}
        />
      </div>

      {/* Primary Scanning Line */}
      <motion.div
        className={styles.scanLine}
        animate={{
          y: ['0%', '100%'],
        }}
        transition={{
          duration: 2.5,
          repeat: Infinity,
          ease: [0.45, 0.05, 0.55, 0.95],
          repeatDelay: 0.3
        }}
      />

      {/* Secondary Scanning Line (Offset) */}
      <motion.div
        className={styles.scanLineSecondary}
        animate={{
          y: ['0%', '100%'],
        }}
        transition={{
          duration: 2.5,
          repeat: Infinity,
          ease: [0.45, 0.05, 0.55, 0.95],
          repeatDelay: 0.3,
          delay: 1.25
        }}
      />

      {/* Glow Effect Following Scan Line */}
      <motion.div
        className={styles.scanGlow}
        animate={{
          y: ['0%', '100%'],
        }}
        transition={{
          duration: 2.5,
          repeat: Infinity,
          ease: [0.45, 0.05, 0.55, 0.95],
          repeatDelay: 0.3
        }}
      />

      {/* Grid Overlay Effect */}
      <motion.div 
        className={styles.gridOverlay}
        animate={{
          opacity: [0.1, 0.3, 0.1]
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />

      {/* Data Extraction Particles */}
      <div className={styles.particles}>
        {[...Array(12)].map((_, i) => (
          <motion.div
            key={i}
            className={styles.particle}
            animate={{
              y: ['0%', '100%'],
              opacity: [0, 1, 0.8, 0],
              scale: [0.5, 1, 1, 0.5]
            }}
            transition={{
              duration: 2.5,
              repeat: Infinity,
              delay: i * 0.15,
              ease: 'linear',
            }}
            style={{
              left: `${8 + i * 7.5}%`,
            }}
          />
        ))}
      </div>

      {/* Horizontal Scan Lines (Multi-stage effect) */}
      {[...Array(5)].map((_, i) => (
        <motion.div
          key={`h-${i}`}
          className={styles.horizontalScanLine}
          style={{ top: `${20 + i * 15}%` }}
          animate={{
            scaleX: [0, 1, 0],
            opacity: [0, 0.6, 0]
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            delay: i * 0.3,
            ease: "easeInOut"
          }}
        />
      ))}

      {/* Status Text */}
      <div className={styles.scanStatus}>
        <motion.div
          className={styles.statusText}
          animate={{ 
            opacity: [0.7, 1, 0.7],
            y: [0, -2, 0]
          }}
          transition={{ 
            duration: 2, 
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          {t('cv_analyzing')}
        </motion.div>
        {progress !== undefined && (
          <motion.div 
            className={styles.progress}
            initial={{ scale: 0.8 }}
            animate={{ 
              scale: [0.9, 1.1, 0.9],
              textShadow: [
                '0 0 10px var(--color-primary)',
                '0 0 20px var(--color-primary)',
                '0 0 10px var(--color-primary)'
              ]
            }}
            transition={{ 
              duration: 2, 
              repeat: Infinity,
              ease: "easeInOut"
            }}
          >
            {progress}%
          </motion.div>
        )}
        
        {/* Scanning Dots Animation */}
        <motion.div className={styles.scanningDots}>
          {[...Array(3)].map((_, i) => (
            <motion.span
              key={i}
              animate={{
                opacity: [0.3, 1, 0.3],
                scale: [0.8, 1.2, 0.8]
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                delay: i * 0.2,
                ease: "easeInOut"
              }}
            >
              •
            </motion.span>
          ))}
        </motion.div>
      </div>

      {/* Pulse Ring Effect */}
      <motion.div
        className={styles.pulseRing}
        animate={{
          scale: [1, 1.5],
          opacity: [0.5, 0]
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: "easeOut"
        }}
      />
    </div>
  );
}

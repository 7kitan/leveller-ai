"use client";

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Clock, ShieldCheck, Mail } from 'lucide-react';
import styles from './maintenance-overlay.module.css';
import { useAuth } from '@/context/AuthContext';
import { useLanguage } from '@/context/LanguageContext';
import { UserRole } from '@/types/roles';

export default function MaintenanceOverlay() {
  const { maintenanceMode, maintenanceDuration, user } = useAuth();
  const { t } = useLanguage();
  
  // If not in maintenance mode, or if user is admin, don't show overlay
  if (!maintenanceMode || user?.role === UserRole.ADMIN) {
    return null;
  }

  return (
    <AnimatePresence>
      <div className={styles.overlayContainer}>
        <div className={styles.glassBackground} />
        
        {/* Decorative ambient elements */}
        <div className={styles.glow1} />
        <div className={styles.glow2} />

        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className={styles.card}
        >
          <div className={styles.header}>
            <div className={styles.iconWrapper}>
              <Sparkles className={styles.mainIcon} size={48} />
              <motion.div 
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ repeat: Infinity, duration: 2 }}
                className={styles.statusBadge}
              >
                {t("maintenance_system_update")}
              </motion.div>
            </div>
            
            <h1 className={styles.title}>{t("maintenance_title")}</h1>
            <p className={styles.subtitle}>
              {t("maintenance_subtitle")}
            </p>
          </div>

          <div className={styles.infoGrid}>
            <div className={styles.infoItem}>
              <Clock className={styles.infoIcon} size={20} />
              <div>
                <span className={styles.infoLabel}>{t("maintenance_duration_label")}</span>
                <p className={styles.infoValue}>{maintenanceDuration || "..."}</p>
              </div>
            </div>
            
            <div className={styles.infoItem}>
              <ShieldCheck className={styles.infoIcon} size={20} />
              <div>
                <span className={styles.infoLabel}>{t("maintenance_data_safe_label")}</span>
                <p className={styles.infoValue}>{t("maintenance_data_safe_value")}</p>
              </div>
            </div>
          </div>

          <div className={styles.footer}>
            <div className={styles.contact}>
              <Mail size={16} />
              <span>support@leveller.ai</span>
            </div>
            <button 
              className={styles.refreshBtn}
              onClick={() => window.location.reload()}
            >
              {t("maintenance_refresh_btn")}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

import React from 'react';
import { motion } from 'framer-motion';
import { Hammer, Clock, ShieldCheck, Mail } from 'lucide-react';
import styles from './maintenance-overlay.module.css';
import { cn } from '@/lib/utils';

interface MaintenanceOverlayProps {
  isAdmin?: boolean;
  duration?: string;
}

export default function MaintenanceOverlay({ isAdmin, duration }: MaintenanceOverlayProps) {
  return (
    <div className={styles.overlayContainer}>
      <div className={styles.glassBackground} />
      
      {/* Decorative ambient elements */}
      <div className={styles.glow1} />
      <div className={styles.glow2} />

      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className={styles.card}
      >
        <div className={styles.header}>
          <div className={styles.iconWrapper}>
            <Hammer className={styles.mainIcon} size={48} />
            <motion.div 
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ repeat: Infinity, duration: 2 }}
              className={styles.statusBadge}
            >
              System Update
            </motion.div>
          </div>
          
          <h1 className={styles.title}>Chúng tôi đang bảo trì hệ thống</h1>
          <p className={styles.subtitle}>
            Lumix AI đang được nâng cấp để mang lại trải nghiệm tốt nhất cho định hướng sự nghiệp của bạn.
          </p>
        </div>

        <div className={styles.infoGrid}>
          <div className={styles.infoItem}>
            <Clock className={styles.infoIcon} size={20} />
            <div>
              <span className={styles.infoLabel}>Thời gian dự kiến</span>
              <p className={styles.infoValue}>{duration || "Đang cập nhật..."}</p>
            </div>
          </div>
          
          <div className={styles.infoItem}>
            <ShieldCheck className={styles.infoIcon} size={20} />
            <div>
              <span className={styles.infoLabel}>Dữ liệu an toàn</span>
              <p className={styles.infoValue}>Toàn bộ CV & phân tích được bảo mật</p>
            </div>
          </div>
        </div>

        <div className={styles.footer}>
          <div className={styles.contact}>
            <Mail size={16} />
            <span>support@lumix.ai</span>
          </div>
          <button 
            className={styles.refreshBtn}
            onClick={() => window.location.reload()}
          >
            Thử tải lại trang
          </button>
        </div>

        {isAdmin && (
          <div className={styles.adminTip}>
            <p>💡 <b>Bạn là Admin:</b> Nếu bạn thấy trang này, vui lòng đảm bảo bạn đã đăng nhập để bypass chế độ bảo trì.</p>
          </div>
        )}
      </motion.div>
    </div>
  );
}

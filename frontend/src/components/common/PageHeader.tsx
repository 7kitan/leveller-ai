"use client";

import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import styles from "./PageHeader.module.css";

interface PageHeaderProps {
  title: React.ReactNode;
  subtitle?: string;
  showAccent?: boolean;
  compact?: boolean;
  className?: string;
  children?: React.ReactNode; // For actions like buttons on the right
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  showAccent = true,
  compact = false,
  className,
  children,
}) => {
  return (
    <div className={cn(styles.headerSection, compact && styles.compact, className)}>
      <div className={styles.headerContent}>
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className={styles.headerTitle}>{title}</h1>
          {subtitle && <p className={styles.headerSubtitle}>{subtitle}</p>}
        </motion.div>
      </div>
      {children && (
        <motion.div 
          className={styles.headerActions}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          {children}
        </motion.div>
      )}
    </div>
  );
};

export default PageHeader;

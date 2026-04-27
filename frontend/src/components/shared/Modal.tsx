"use client";

import React, { useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import Portal from "./Portal";
import styles from "./modal.module.css";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/context/LanguageContext";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  maxWidth?: string;
  showCloseButton?: boolean;
  className?: string;
}

export default function Modal({
  isOpen,
  onClose,
  title,
  children,
  maxWidth = "36rem",
  showCloseButton = true,
  className
}: ModalProps) {
  const { t } = useLanguage();
  
  // Close on Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    } else {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "unset";
    }
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, handleKeyDown]);

  return (
    <Portal>
      <AnimatePresence>
        {isOpen && (
          <div 
            className={styles.modalOverlay}
            onClick={(e) => {
              if (e.target === e.currentTarget) onClose();
            }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className={cn(styles.modalContent, className)}
              style={{ maxWidth }}
              onClick={(e) => e.stopPropagation()}
            >
              {title && (
                <div className={styles.modalHeader}>
                  <div className={styles.modalTitle}>{title}</div>
                  {showCloseButton && (
                    <button 
                      onClick={onClose} 
                      className={styles.closeBtn}
                      aria-label={t("aria_close_modal")}
                    >
                      <X size={20} />
                    </button>
                  )}
                </div>
              )}
              {!title && showCloseButton && (
                <button 
                  onClick={onClose} 
                  className={cn(styles.closeBtn, styles.closeBtnStandalone)}
                  aria-label={t("aria_close_modal")}
                >
                  <X size={20} />
                </button>
              )}
              <div className={styles.modalBody}>
                {children}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </Portal>
  );
}

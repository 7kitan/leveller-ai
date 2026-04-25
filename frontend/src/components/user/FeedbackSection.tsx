"use client";

import React, { useState } from "react";
import { Star, CheckCircle2, AlertCircle, Send, Plus, X, RefreshCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/context/LanguageContext";
import api from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import Portal from "@/components/shared/Portal";
import styles from "./feedback-section.module.css";
import { useEffect } from "react";

interface FeedbackSectionProps {
  analysisId: string;
  hasFeedback?: boolean;
  isCached?: boolean;
}

const FeedbackSection: React.FC<FeedbackSectionProps> = ({ analysisId, hasFeedback, isCached }) => {
  const { t } = useLanguage();
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [isAccurate, setIsAccurate] = useState<boolean | null>(null);
  const [comment, setComment] = useState("");
  const [missingSkills, setMissingSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (isSubmitted) {
      const timer = setTimeout(() => {
        setIsSubmitted(false);
        setIsExpanded(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isSubmitted]);

  const handleAddSkill = () => {
    if (skillInput.trim() && !missingSkills.includes(skillInput.trim())) {
      setMissingSkills([...missingSkills, skillInput.trim()]);
      setSkillInput("");
    }
  };

  const removeSkill = (skill: string) => {
    setMissingSkills(missingSkills.filter((s) => s !== skill));
  };

  const handleSubmit = async () => {
    if (rating === 0) {
      setError(t("error_rating"));
      return;
    }
    setIsSubmitting(true);
    setError("");
    try {
      await api.post("analysis/feedback", {
        analysis_id: analysisId,
        rating,
        is_accurate: isAccurate,
        missing_skills: missingSkills,
        comment,
      });
      setIsSubmitted(true);
    } catch (err) {
      setError(t("error_submit_feedback"));
    } finally {
      setIsSubmitting(false);
    }
  };

  // If already had feedback from DB, don't show the widget at all
  if (hasFeedback && !isSubmitted) {
    return null;
  }

  return (
    <Portal>
      <div className={cn(styles.floatingWrapper, isExpanded && styles.isExpanded)}>
        <motion.button 
          layout
          onClick={() => setIsExpanded(!isExpanded)}
          className={styles.triggerBtn}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Send size={20} className={cn(styles.triggerIcon, isExpanded && styles.iconActive)} />
          <span>{isExpanded ? t("close") : t("feedback_title")}</span>
        </motion.button>

        <AnimatePresence>
          {isSubmitted && (
            <motion.div 
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className={styles.successContainer}
            >
              <CheckCircle2 size={32} className={styles.successIcon} />
              <h3 className={styles.successTitle}>{t("feedback_success")}</h3>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {isExpanded && !isSubmitted && (
            <motion.section 
              initial={{ opacity: 0, y: 50, scale: 0.9, x: 20 }}
              animate={{ opacity: 1, y: 0, scale: 1, x: 0 }}
              exit={{ opacity: 0, y: 50, scale: 0.9, x: 20 }}
              className={styles.section}
            >
              <div className={styles.header}>
                <h2 className={styles.title}>{t("feedback_title")}</h2>
                <p className={styles.subtitle}>{t("feedback_subtitle")}</p>
              </div>

              <div className={styles.card}>
                {/* Rating */}
                <div className={styles.group}>
                  <label className={styles.label}>{t("feedback_rating")}</label>
                  <div className={styles.stars}>
                    {[1, 2, 3, 4, 5].map((i) => (
                      <button
                        key={i}
                        onMouseEnter={() => setHoverRating(i)}
                        onMouseLeave={() => setHoverRating(0)}
                        onClick={() => setRating(i)}
                        className={cn(
                          styles.starBtn,
                          (hoverRating || rating) >= i && styles.starActive
                        )}
                        type="button"
                      >
                        <Star 
                          size={28} 
                          fill={(hoverRating || rating) >= i ? "currentColor" : "none"} 
                          strokeWidth={1.5}
                        />
                      </button>
                    ))}
                  </div>
                </div>

                {/* Accuracy */}
                <div className={styles.group}>
                  <label className={styles.label}>{t("feedback_accurate")}</label>
                  <div className={styles.toggleRow}>
                    <button
                      onClick={() => setIsAccurate(true)}
                      className={cn(styles.toggleBtn, styles.btnYes, isAccurate === true && styles.toggleActiveYes)}
                      type="button"
                    >
                      <CheckCircle2 size={16} />
                      {t("feedback_accurate_yes")}
                    </button>
                    <button
                      onClick={() => setIsAccurate(false)}
                      className={cn(styles.toggleBtn, styles.btnNo, isAccurate === false && styles.toggleActiveNo)}
                      type="button"
                    >
                      <AlertCircle size={16} />
                      {t("feedback_accurate_no")}
                    </button>
                  </div>
                </div>

                {/* Missing Skills */}
                <div className={styles.group}>
                  <label className={styles.label}>{t("feedback_missing_skills")}</label>
                  <div className={styles.skillInputRow}>
                    <input
                      type="text"
                      value={skillInput}
                      onChange={(e) => setSkillInput(e.target.value)}
                      onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddSkill();
                      }
                    }}
                      className={styles.input}
                      placeholder={t("feedback_missing_skills_placeholder")}
                      maxLength={50}
                      id="skill-input"
                    />
                    <button 
                      onClick={(e) => {
                        e.preventDefault();
                        handleAddSkill();
                        document.getElementById("skill-input")?.focus();
                      }} 
                      className={styles.addBtn} 
                      type="button"
                      disabled={!skillInput.trim()}
                    >
                      <Plus size={18} />
                    </button>
                  </div>
                  <div className={styles.pillContainer}>
                    {missingSkills.map((skill) => (
                      <span key={skill} className={styles.pill}>
                        {skill}
                        <button onClick={() => removeSkill(skill)} className={styles.pillX} type="button">
                          <X size={12} />
                        </button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Comment */}
                <div className={styles.group}>
                  <label className={styles.label}>{t("feedback_comment")}</label>
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    className={styles.textarea}
                    rows={3}
                    placeholder={t("feedback_comment_placeholder")}
                    maxLength={1000}
                  />
                </div>

                {error && <p className={styles.error}>{error}</p>}

                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting || rating === 0}
                  className={styles.submitBtn}
                  type="button"
                >
                  {isSubmitting ? <RefreshCcw className="animate-spin" size={18} /> : <Send size={18} />}
                  {t("feedback_submit")}
                </button>
              </div>
            </motion.section>
          )}
        </AnimatePresence>
      </div>
    </Portal>
  );
};

export default FeedbackSection;


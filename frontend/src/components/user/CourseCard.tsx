"use client";

import React from "react";
import { Award, ArrowRight, ExternalLink } from "lucide-react";
import { useLanguage } from "@/context/LanguageContext";
import styles from "./CourseCard.module.css";
import { motion } from "framer-motion";

interface CourseCardProps {
  course: {
    id: string | number;
    title: string;
    platform: string;
    level?: string;
    match: string;
    skills: string[];
    url: string;
    is_certification?: boolean;
    selection_reason?: string;
  };
  index?: number;
}

const CourseCard: React.FC<CourseCardProps> = ({ course, index = 0 }) => {
  const { t } = useLanguage();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className={styles.courseCard}
    >
      <div className={styles.courseCardTop}>
        <div className={styles.courseTitle}>{course.title}</div>
        {course.is_certification && (
          <span className={styles.certBadge}>
            <Award size={12} />
            {t("cert_label")}
          </span>
        )}
      </div>

      <div className={styles.courseMeta}>
        <span className={styles.platformName}>{course.platform}</span>
        <span>·</span>
        <span>{course.level || "Beginner"}</span>
      </div>

      {course.skills && course.skills.length > 0 && (
        <div className={styles.skillList}>
          {course.skills.map((s, i) => (
            <span key={`${s}-${i}`} className={styles.skillBadge}>{s}</span>
          ))}
        </div>
      )}

      {course.selection_reason && (
        <p className={styles.courseReason}>
          &ldquo;{course.selection_reason}&rdquo;
        </p>
      )}

      <div className={styles.courseFooterActions}>
        <div className={styles.matchScoreLabel}>
          <span className="font-micro">{t("dash_match_score")}</span>
          <span className={styles.matchScoreValue}>{course.match}</span>
        </div>
        {course.url && (
          <a
            href={course.url}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.viewCourseLink}
          >
            {t("dash_learn_now")} <ArrowRight size={14} />
          </a>
        )}
      </div>
    </motion.div>
  );
};

export default CourseCard;

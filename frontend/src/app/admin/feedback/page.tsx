"use client";

import React, { useState, useEffect } from "react";
import { 
  Star, 
  CheckCircle2, 
  AlertCircle, 
  User, 
  Calendar,
  Filter
} from "lucide-react";
import { useLanguage } from "@/context/LanguageContext";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import styles from "./admin-feedback.module.css";
import Pagination from "@/components/shared/Pagination";
import AuthGuard from "@/components/auth/AuthGuard";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";

interface FeedbackItem {
  id: string;
  user_email: string;
  analysis_id: string;
  rating: number;
  is_accurate: boolean | null;
  missing_skills: string[];
  comment: string;
  created_at: string;
}

export default function AdminFeedbackPage() {
  const { t } = useLanguage();
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  
  const [ratingFilter, setRatingFilter] = useState<number | null>(null);
  const [accurateFilter, setAccurateFilter] = useState<boolean | null>(null);

  const fetchFeedback = async () => {
    setLoading(true);
    try {
      const resp = await api.get("/api/analysis/admin/feedback", {
        params: {
          limit,
          offset: (page - 1) * limit,
          rating: ratingFilter,
          is_accurate: accurateFilter
        }
      });
      setFeedback(resp.data.items);
      setTotal(resp.data.total);
    } catch (err) {
      console.error("Failed to fetch feedback", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeedback();
  }, [page, ratingFilter, accurateFilter]);

  const renderStars = (rating: number) => {
    return (
      <div className={styles.stars}>
        {[1, 2, 3, 4, 5].map((i) => (
          <Star 
            key={i} 
            size={14} 
            className={cn(i <= rating ? styles.starActive : styles.starInactive)}
            fill={i <= rating ? "currentColor" : "none"}
          />
        ))}
      </div>
    );
  };

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <PageHeader 
          title={t("admin_feedback_title")}
          subtitle={t("admin_feedback_sub")}
        >
        <div className={styles.filters}>
          <div className={styles.filterGroup}>
            <Filter size={16} />
            <select 
              value={ratingFilter ?? ""} 
              onChange={(e) => {
                setRatingFilter(e.target.value ? parseInt(e.target.value) : null);
                setPage(1);
              }}
              className={styles.select}
            >
              <option value="">{t("table_rating")}: {t("admin_feedback_all")}</option>
              {[5, 4, 3, 2, 1].map(r => <option key={r} value={r}>{r} {t("admin_feedback_stars")}</option>)}
            </select>
          </div>
          <div className={styles.filterGroup}>
            <select 
              value={accurateFilter === null ? "" : accurateFilter.toString()} 
              onChange={(e) => {
                setAccurateFilter(e.target.value === "" ? null : e.target.value === "true");
                setPage(1);
              }}
              className={styles.select}
            >
              <option value="">{t("table_accurate")}: {t("admin_feedback_all")}</option>
              <option value="true">{t("feedback_accurate_yes")}</option>
              <option value="false">{t("feedback_accurate_no")}</option>
            </select>
          </div>
          </div>
        </PageHeader>

      <div className={styles.tableCard}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>{t("table_user")}</th>
              <th>{t("table_rating")}</th>
              <th>{t("table_accurate")}</th>
              <th>{t("table_comment")}</th>
              <th>{t("cv_history_title")}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className={styles.loading}>{t("loading")}</td></tr>
            ) : feedback.length === 0 ? (
              <tr><td colSpan={5} className={styles.empty}>No feedback found</td></tr>
            ) : (
              feedback.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div className={styles.userInfo}>
                      <User size={14} />
                      <span>{item.user_email}</span>
                    </div>
                  </td>
                  <td>{renderStars(item.rating)}</td>
                  <td>
                    {item.is_accurate === null ? (
                      <span className={styles.statusN}>-</span>
                    ) : item.is_accurate ? (
                      <span className={styles.statusY}><CheckCircle2 size={14} /> {t("feedback_accurate_yes")}</span>
                    ) : (
                      <span className={styles.statusX}><AlertCircle size={14} /> {t("feedback_accurate_no")}</span>
                    )}
                  </td>
                  <td className={styles.commentCell}>
                    <div className={styles.commentText}>{item.comment || <span className={styles.noComment}>{t("admin_feedback_no_comment")}</span>}</div>
                    {item.missing_skills?.length > 0 && (
                      <div className={styles.missingSkills}>
                        {item.missing_skills.map(s => <span key={s} className={styles.skillPill}>{s}</span>)}
                      </div>
                    )}
                  </td>
                  <td className={styles.dateCell}>
                    <div className={styles.dateInfo}>
                      <Calendar size={12} />
                      {new Date(item.created_at).toLocaleString()}
                    </div>
                    <div className={styles.taskId}>ID: {item.analysis_id.slice(0, 8)}</div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {total > limit && (
          <div className={styles.pagination}>
            <Pagination 
              currentPage={page} 
              totalPages={Math.ceil(total / limit)} 
              onPageChange={setPage} 
            />
          </div>
        )}
      </div>
    </PageContainer>
    </AuthGuard>
  );
}

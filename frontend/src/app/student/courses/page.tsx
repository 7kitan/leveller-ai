"use client";

import React, { useState, useEffect } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookOpen,
  Clock,
  Award,
  ExternalLink,
  Search,
  Globe,
  Tag,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/context/LanguageContext";
import styles from "./courses.module.css";

// ─── Types ────────────────────────────────────────────────────────────────────
interface Course {
  id: string;
  title: string;
  description: string;
  platform: string;
  url: string;
  level: string;
  cost_usd: number;
  duration_hours: number;
  is_certification: boolean;
  language: string;
  tags: string[];
}

interface FilterState {
  query: string;
  level: string;
  platform: string;
  hasCertificate: boolean;
  maxCost: number;
  sortBy: "relevance" | "level_asc" | "level_desc" | "cost_asc" | "cost_desc";
}

// ─── Level Badge ─────────────────────────────────────────────────────────────
function LevelBadge({ level }: { level: string }) {
  const { t } = useLanguage();
  const cls =
    level === "Beginner"     ? styles.levelBeginner     :
    level === "Intermediate" ? styles.levelIntermediate :
    level === "Advanced"    ? styles.levelAdvanced     :
    styles.levelBeginner;
  return <span className={cls}>{t(`level_${level?.toLowerCase()}` as any)}</span>;
}

// ─── Course Card ───────────────────────────────────────────────────────────────
function CourseCard({ course, index }: { course: Course; index: number }) {
  const { t } = useLanguage();
  const isFree = (course.cost_usd ?? 0) === 0;
  const platformStrip =
    course.platform === "Coursera" ? styles.stripCoursera :
    course.platform === "Udemy"    ? styles.stripUdemy   :
    styles.stripDefault;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.35 }}
      className={styles.courseCard}
    >
      <div className={cn(styles.platformStrip, platformStrip)} />

      <div className={styles.courseBody}>
        <div className={styles.courseHeader}>
          <span className={styles.platformLabel}>{course.platform}</span>
          {course.level && <LevelBadge level={course.level} />}
        </div>

        <h3 className={styles.courseTitle}>{course.title}</h3>

        {course.description && (
          <p className={styles.courseDescription}>{course.description}</p>
        )}

        {course.tags?.length > 0 && (
          <div className={styles.tagGroup}>
            {course.tags.slice(0, 5).map((tag) => (
              <span key={tag} className={styles.skillTag}>
                <Tag size={10} />
                {tag}
              </span>
            ))}
            {course.tags.length > 5 && (
              <span className={cn(styles.skillTag, styles.statLabel)}>
                +{course.tags.length - 5}
              </span>
            )}
          </div>
        )}

        <div className={styles.courseMeta}>
          {course.duration_hours && (
            <span className={styles.metaItem}>
              <Clock size={14} />
              {course.duration_hours}h
            </span>
          )}
          <span className={styles.metaItem}>
            <Globe size={14} />
            {course.language?.toUpperCase() ?? "EN"}
          </span>
          {course.is_certification && (
            <span className={cn(styles.metaItem, styles.badgeSuccess)}>
              <Award size={14} />
              {t('cert_short')}
            </span>
          )}
          <span className={cn(styles.costBadge, isFree ? styles.costFree : styles.costPaid)}>
            {isFree ? t('free') : `$${course.cost_usd}`}
          </span>
        </div>

        {course.url && (
          <a
            href={course.url}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.courseCta}
          >
            <BookOpen size={16} />
            {t('view_course')}
            <ExternalLink size={14} />
          </a>
        )}
      </div>
    </motion.div>
  );
}

// ─── Filter Bar ────────────────────────────────────────────────────────────────
function FilterBar({
  filters,
  onChange,
  platforms,
  levels,
}: {
  filters: FilterState;
  onChange: (f: Partial<FilterState>) => void;
  platforms: string[];
  levels: string[];
}) {
  const { t } = useLanguage();
  return (
    <div className={styles.filterBar}>
      <div className={styles.filterRow}>
        <div className={styles.searchBox}>
          <Search size={18} />
          <input
            type="text"
            placeholder={t('search_courses_placeholder')}
            value={filters.query}
            onChange={(e) => onChange({ query: e.target.value })}
            className={styles.searchInput}
          />
          {filters.query && (
            <button
              onClick={() => onChange({ query: "" })}
            >
              <X size={14} />
            </button>
          )}
        </div>

        <div className={styles.filterControls}>
          <select
            value={filters.level}
            onChange={(e) => onChange({ level: e.target.value })}
            className={styles.selectInput}
          >
            <option value="">{t('level')}</option>
            {levels.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>

          <select
            value={filters.platform}
            onChange={(e) => onChange({ platform: e.target.value })}
            className={styles.selectInput}
          >
            <option value="">{t('platform')}</option>
            {platforms.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>

          <select
            value={filters.sortBy}
            onChange={(e) => onChange({ sortBy: e.target.value as FilterState["sortBy"] })}
            className={styles.selectInput}
          >
            <option value="relevance">{t('relevance')}</option>
            <option value="level_asc">{t('level_asc')}</option>
            <option value="level_desc">{t('level_desc')}</option>
            <option value="cost_asc">{t('price_asc')}</option>
            <option value="cost_desc">{t('price_desc')}</option>
          </select>

          <button
            onClick={() => onChange({ hasCertificate: !filters.hasCertificate })}
            className={cn(styles.filterChip, filters.hasCertificate && styles.filterChipActive)}
          >
            <Award size={14} />
            {t('cert_short')}
          </button>
        </div>
      </div>

      {(filters.query || filters.level || filters.platform || filters.hasCertificate) && (
        <div className={styles.activeFilters}>
          <span className={styles.statLabel}>
            {t('filter_by')}
          </span>

          {filters.query && (
            <button onClick={() => onChange({ query: "" })} className={cn(styles.activeFilterBadge, styles.badgePrimary)}>
              &ldquo;{filters.query}&rdquo; <X size={12} />
            </button>
          )}
          {filters.level && (
            <button onClick={() => onChange({ level: "" })} className={cn(styles.activeFilterBadge, styles.badgePrimary)}>
              {filters.level} <X size={12} />
            </button>
          )}
          {filters.platform && (
            <button onClick={() => onChange({ platform: "" })} className={cn(styles.activeFilterBadge, styles.badgePrimary)}>
              {filters.platform} <X size={12} />
            </button>
          )}
          {filters.hasCertificate && (
            <button onClick={() => onChange({ hasCertificate: false })} className={cn(styles.activeFilterBadge, styles.badgeSuccess)}>
              {t('has_cert')} <X size={12} />
            </button>
          )}
          <button
            onClick={() => onChange({ query: "", level: "", platform: "", hasCertificate: false })}
            className={styles.resetBtn}
          >
            {t('reset_filters')}
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function StudentCoursesPage() {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState<FilterState>({
    query: "",
    level: "",
    platform: "",
    hasCertificate: false,
    maxCost: 0,
    sortBy: "relevance",
  });

  useEffect(() => {
    if (!user) return;
    const fetchCourses = async () => {
      setLoading(true);
      try {
        const res = await api.get("recommend/courses", {
          params: { limit: 100 },
        });
        setCourses(Array.isArray(res.data) ? res.data : res.data.courses ?? []);
      } catch {
        setError(t('load_courses_error'));
      } finally {
        setLoading(false);
      }
    };
    fetchCourses();
  }, [user]);

  // Filter + sort
  const filtered = courses
    .filter((c) => {
      const q = filters.query.toLowerCase();
      if (q && !(
        c.title?.toLowerCase().includes(q) ||
        c.tags?.some((t) => t.toLowerCase().includes(q)) ||
        c.description?.toLowerCase().includes(q) ||
        c.platform?.toLowerCase().includes(q)
      )) return false;
      if (filters.level && c.level !== filters.level) return false;
      if (filters.platform && c.platform !== filters.platform) return false;
      if (filters.hasCertificate && !c.is_certification) return false;
      return true;
    })
    .sort((a, b) => {
      switch (filters.sortBy) {
        case "level_asc":  return (a.level ?? "").localeCompare(b.level ?? "");
        case "level_desc": return (b.level ?? "").localeCompare(a.level ?? "");
        case "cost_asc":   return (a.cost_usd ?? 0) - (b.cost_usd ?? 0);
        case "cost_desc":  return (b.cost_usd ?? 0) - (a.cost_usd ?? 0);
        default:           return 0;
      }
    });

  const platforms = [...new Set(courses.map((c) => c.platform).filter(Boolean))] as string[];
  const levels    = [...new Set(courses.map((c) => c.level).filter(Boolean))] as string[];

  const updateFilters = (patch: Partial<FilterState>) =>
    setFilters((prev) => ({ ...prev, ...patch }));

  return (
    <div className={styles.pageRoot}>

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className={styles.headerSection}>
        <div className={styles.titleArea}>
          <div className={styles.sectionLabel}>
            <BookOpen size={14} />
            {t('course_library')}
          </div>
          <h1 className={styles.sectionTitle}>
            {t('explore_title_1')}<br />
            <span className={styles.gradientText}>{t('explore_title_2')}.</span>
          </h1>
          <p className={styles.sectionSubtitle}>
            {t('explore_subtitle')}
          </p>
        </div>

        {/* Stats pill */}
        <div className={styles.statsHeader}>
          {[
            { label: t('courses_text'),   value: courses.length },
            { label: t('platform'),   value: platforms.length },
            { label: t('cert_short'), value: courses.filter((c) => c.is_certification).length },
          ].map(({ label, value }) => (
            <div key={label} className={styles.statItem}>
              <div className={styles.statValue}>{value}</div>
              <div className={styles.statLabel}>{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Filter ─────────────────────────────────────────────────────────── */}
      <FilterBar
        filters={filters}
        onChange={updateFilters}
        platforms={platforms}
        levels={levels}
      />

      {/* ── Loading ────────────────────────────────────────────────────────── */}
      {loading && (
        <div className={styles.courseGrid}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className={styles.courseCard}>
              <div className={styles.platformStrip} />
              <div className={styles.courseBody}>
                <div className={cn(styles.skeleton, styles.skeletonLabel)} />
                <div className={cn(styles.skeleton, styles.skeletonTitle)} />
                <div className={cn(styles.skeleton, styles.skeletonText)} />
                <div className={cn(styles.skeleton, styles.skeletonTextSub)} />
                <div className={styles.skeletonTagContainer}>
                  {[1, 2, 3].map((j) => <div key={j} className={cn(styles.skeleton, styles.skeletonTag)} />)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Error ──────────────────────────────────────────────────────────── */}
      {!loading && error && (
        <div className={cn(styles.headerSection, styles.centeredError)}>
          <span className={styles.levelAdvanced}>{error}</span>
        </div>
      )}

      {/* ── Results count ───────────────────────────────────────────────────── */}
      {!loading && !error && (
        <p className={styles.resultsCount}>
          {t('displaying')}{" "}
          <span className={styles.resultsCountHighlight}>{filtered.length}</span>
          {" "}{t('of_text')} {courses.length} {t('courses_text')}
        </p>
      )}

      {/* ── Grid ────────────────────────────────────────────────────────────── */}
      {!loading && !error && (
        <AnimatePresence mode="wait">
          {filtered.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className={styles.emptyStateContainer}
            >
              <div className={styles.emptyIconBox}>
                <BookOpen size={32} />
              </div>
              <div className={styles.summaryArea}>
                <h3 className={styles.summaryTitle}>{t('no_courses_found')}</h3>
                <p className={styles.summaryDesc}>{t('adjust_filters_desc')}</p>
              </div>
              <button
                onClick={() =>
                  setFilters({ query: "", level: "", platform: "", hasCertificate: false, maxCost: 0, sortBy: "relevance" })
                }
                className={cn(styles.courseCta, styles.mt0)}
              >
                {t('clear_all_filters')}
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="grid"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className={styles.courseGrid}
            >
              {filtered.map((course, i) => (
                <CourseCard key={course.id ?? i} course={course} index={i} />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      )}

    </div>
  );
}



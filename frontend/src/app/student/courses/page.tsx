"use client";

import React, { useState, useEffect } from "react";
import axios from "axios";
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

// ─── Types ─────────────────────────────────────────────────────────────────────
interface Course {
  id: string;
  title: string;
  description?: string;
  platform: string;
  provider?: string;
  url?: string;
  language?: string;
  level?: string;
  is_certification: boolean;
  duration_hours?: number;
  cost_usd?: number;
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

// ─── Level Badge (CSS handles theme) ─────────────────────────────────────────
function LevelBadge({ level }: { level: string }) {
  const cls =
    level === "Beginner"     ? "level-beginner"     :
    level === "Intermediate" ? "level-intermediate" :
    level === "Advanced"    ? "level-advanced"     :
    "level-beginner";
  return <span className={cls}>{level}</span>;
}

// ─── Course Card ───────────────────────────────────────────────────────────────
function CourseCard({ course, index }: { course: Course; index: number }) {
  const isFree = (course.cost_usd ?? 0) === 0;
  const platformStrip =
    course.platform === "Coursera" ? "course-platform-coursera" :
    course.platform === "Udemy"    ? "course-platform-udemy"   :
    "course-platform-default";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.35 }}
      className="course-card"
    >
      {/* Platform color strip */}
      <div className={`course-platform-strip ${platformStrip}`} />

      <div className="course-body">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <span className="course-platform-label">{course.platform}</span>
          {course.level && <LevelBadge level={course.level} />}
        </div>

        {/* Title */}
        <h3 className="course-title">{course.title}</h3>

        {/* Description */}
        {course.description && (
          <p className="course-description">{course.description}</p>
        )}

        {/* Tags */}
        {course.tags?.length > 0 && (
          <div className="course-tags">
            {course.tags.slice(0, 5).map((tag) => (
              <span key={tag} className="skill-tag">
                <Tag className="w-2.5 h-2.5" />
                {tag}
              </span>
            ))}
            {course.tags.length > 5 && (
              <span className="skill-tag" style={{ color: "hsl(var(--text-muted))" }}>
                +{course.tags.length - 5}
              </span>
            )}
          </div>
        )}

        {/* Meta */}
        <div className="course-meta">
          {course.duration_hours && (
            <span className="course-meta-item">
              <Clock className="w-3.5 h-3.5" />
              {course.duration_hours}h
            </span>
          )}
          <span className="course-meta-item">
            <Globe className="w-3.5 h-3.5" />
            {course.language?.toUpperCase() ?? "EN"}
          </span>
          {course.is_certification && (
            <span className="course-meta-item" style={{ color: "hsl(var(--success))" }}>
              <Award className="w-3.5 h-3.5" />
              Certificate
            </span>
          )}
          <span className={`course-cost ${isFree ? "course-cost-free" : "course-cost-paid"}`}>
            {isFree ? "Free (audit)" : `$${course.cost_usd}`}
          </span>
        </div>

        {/* CTA */}
        {course.url && (
          <a
            href={course.url}
            target="_blank"
            rel="noopener noreferrer"
            className="course-cta"
          >
            <BookOpen className="w-4 h-4" />
            Xem khóa học
            <ExternalLink className="w-3.5 h-3.5" />
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
  return (
    <div className="filter-bar">
      {/* Search + controls row */}
      <div className="filter-row">
        {/* Search input */}
        <div className="filter-search">
          <Search className="w-4 h-4 flex-shrink-0" style={{ color: "hsl(var(--text-muted))" }} />
          <input
            type="text"
            placeholder="Tìm kiếm khóa học, kỹ năng..."
            value={filters.query}
            onChange={(e) => onChange({ query: e.target.value })}
          />
          {filters.query && (
            <button
              onClick={() => onChange({ query: "" })}
              style={{ color: "hsl(var(--text-muted))" }}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Controls: level + platform + sort + cert */}
        <div className="filter-controls">
          <select
            value={filters.level}
            onChange={(e) => onChange({ level: e.target.value })}
            className="select"
          >
            <option value="">Mọi cấp độ</option>
            {levels.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>

          <select
            value={filters.platform}
            onChange={(e) => onChange({ platform: e.target.value })}
            className="select"
          >
            <option value="">Mọi nền tảng</option>
            {platforms.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>

          <select
            value={filters.sortBy}
            onChange={(e) => onChange({ sortBy: e.target.value as FilterState["sortBy"] })}
            className="select"
          >
            <option value="relevance">Độ phù hợp</option>
            <option value="level_asc">Cấp độ ↑</option>
            <option value="level_desc">Cấp độ ↓</option>
            <option value="cost_asc">Giá ↑</option>
            <option value="cost_desc">Giá ↓</option>
          </select>

          <button
            onClick={() => onChange({ hasCertificate: !filters.hasCertificate })}
            className={`filter-chip${filters.hasCertificate ? " active" : ""}`}
          >
            <Award className="w-3.5 h-3.5 inline mr-1" />
            Chứng chỉ
          </button>
        </div>
      </div>

      {/* Active filter chips */}
      {(filters.query || filters.level || filters.platform || filters.hasCertificate) && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[11px] font-bold uppercase tracking-widest" style={{ color: "hsl(var(--text-muted))" }}>
            Lọc:
          </span>

          {filters.query && (
            <button onClick={() => onChange({ query: "" })} className="badge badge-primary">
              &ldquo;{filters.query}&rdquo; <X className="w-3 h-3" />
            </button>
          )}
          {filters.level && (
            <button onClick={() => onChange({ level: "" })} className="badge badge-primary">
              {filters.level} <X className="w-3 h-3" />
            </button>
          )}
          {filters.platform && (
            <button onClick={() => onChange({ platform: "" })} className="badge badge-primary">
              {filters.platform} <X className="w-3 h-3" />
            </button>
          )}
          {filters.hasCertificate && (
            <button onClick={() => onChange({ hasCertificate: false })} className="badge badge-success">
              Có chứng chỉ <X className="w-3 h-3" />
            </button>
          )}
          <button
            onClick={() => onChange({ query: "", level: "", platform: "", hasCertificate: false })}
            className="filter-chip-clear"
          >
            Xóa tất cả
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function StudentCoursesPage() {
  const { token } = useAuth();
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
    if (!token) return;
    const fetchCourses = async () => {
      setLoading(true);
      try {
        const res = await axios.get("/api/recommend/courses", {
          headers: { Authorization: `Bearer ${token}` },
          params: { limit: 100 },
        });
        setCourses(Array.isArray(res.data) ? res.data : res.data.courses ?? []);
      } catch {
        setError("Không thể tải danh sách khóa học.");
      } finally {
        setLoading(false);
      }
    };
    fetchCourses();
  }, [token]);

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
    <div className="space-y-10 pb-20">

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
        <div className="space-y-4">
          <div className="section-label section-label-accent">
            <BookOpen className="w-3.5 h-3.5" />
            Course Library
          </div>
          <h1 className="section-title">
            KHÁM PHÁ<br />
            <span className="gradient-text">KHÓA HỌC.</span>
          </h1>
          <p className="section-subtitle">
            Trang bị kỹ năng cần thiết từ các nền tảng hàng đầu.
            Học theo lộ trình cá nhân hóa dựa trên Gap Analysis của bạn.
          </p>
        </div>

        {/* Stats pill */}
        <div className="card px-6 py-4 flex items-center gap-8">
          {[
            { label: "Khóa học",   value: courses.length },
            { label: "Nền tảng",   value: platforms.length },
            { label: "Có chứng chỉ", value: courses.filter((c) => c.is_certification).length },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <div className="text-2xl font-black">{value}</div>
              <div className="stat-label">{label}</div>
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="course-card">
              <div className="h-1" />
              <div className="course-body space-y-3">
                <div className="skeleton h-3 w-16" />
                <div className="skeleton h-5 w-3/4" />
                <div className="skeleton h-3 w-full" />
                <div className="skeleton h-3 w-2/3" />
                <div className="flex gap-2 mt-2">
                  {[1, 2, 3].map((j) => <div key={j} className="skeleton h-6 w-16 rounded-full" />)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Error ──────────────────────────────────────────────────────────── */}
      {!loading && error && (
        <div className="toast toast-error">
          <span className="text-sm font-bold">{error}</span>
        </div>
      )}

      {/* ── Results count ───────────────────────────────────────────────────── */}
      {!loading && !error && (
        <p className="text-sm font-bold" style={{ color: "hsl(var(--text-muted))" }}>
          Hiển thị{" "}
          <span style={{ color: "hsl(var(--accent))" }}>{filtered.length}</span>
          {" "}/ {courses.length} khóa học
        </p>
      )}

      {/* ── Grid ────────────────────────────────────────────────────────────── */}
      {!loading && !error && (
        <AnimatePresence mode="wait">
          {filtered.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="card flex flex-col items-center justify-center py-24 space-y-4 text-center"
            >
              <BookOpen className="w-12 h-12" style={{ color: "hsl(var(--text-muted))" }} />
              <h3 className="text-lg font-bold">Không tìm thấy khóa học phù hợp</h3>
              <p className="text-sm" style={{ color: "hsl(var(--text-muted))" }}>
                Thử điều chỉnh bộ lọc hoặc từ khóa tìm kiếm
              </p>
              <button
                onClick={() =>
                  setFilters({ query: "", level: "", platform: "", hasCertificate: false, maxCost: 0, sortBy: "relevance" })
                }
                className="btn btn-secondary"
              >
                Xóa bộ lọc
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="grid"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
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

"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import Pagination from "@/components/shared/Pagination";
import { 
  Plus, 
  Trash2, 
  Search, 
  RefreshCcw,
  Edit2,
  BookOpen,
  ExternalLink,
  Clock,
  DollarSign,
  AlertCircle,
  Tag,
  Globe,
  CheckCircle2,
  List,
  Target,
  Award,
  BadgeDollarSign,
  X
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-courses.module.css";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";
import Portal from "@/components/shared/Portal";
import Modal from "@/components/shared/Modal";

interface Course {
  id: string;
  title: string;
  description?: string;
  platform: string;
  source_platform?: string | null;
  source_id?: string | null;
  external_uuid?: string | null;
  url: string;
  level: string;
  provider: string | null;
  duration_hours: number | null;
  duration_raw?: string | null;
  cost_usd: number;
  languages?: string[];
  tags: string[];
  skills_raw?: string[];
  outcomes?: string[];
  modules?: string[];
  is_certification?: boolean;
  is_active: boolean;
}

const TagInput = ({ tags, setTags, placeholder = t("admin_courses_tag_placeholder") }: { tags: string[], setTags: (tags: string[]) => void, placeholder?: string }) => {
  const [input, setInput] = useState("");

  const addTag = (val: string) => {
    const trimmed = val.trim();
    if (trimmed && !tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
    }
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(input);
    } else if (e.key === "Backspace" && !input && tags.length > 0) {
      setTags(tags.slice(0, -1));
    }
  };

  return (
    <div className={styles.tagInputWrapper}>
      {tags.map((tag, idx) => (
        <span key={idx} className={styles.tagPill}>
          {tag}
          <button 
            type="button" 
            onClick={() => setTags(tags.filter((_, i) => i !== idx))}
            className={styles.tagDelete}
          >
            <X size={10} />
          </button>
        </span>
      ))}
      <input
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => addTag(input)}
        placeholder={tags.length === 0 ? placeholder : ""}
        className={styles.tagInnerInput}
      />
    </div>
  );
};

const AdminCoursesPage = () => {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [courses, setCourses] = useState<Course[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [pageSize] = useState(10); // Trang Admin hiển thị ít hơn chút cho thoáng

  const [formData, setFormData] = useState({
    title: "",
    description: "",
    platform: "",
    source_platform: "",
    source_id: "",
    external_uuid: "",
    url: "",
    level: "Beginner",
    provider: "",
    duration_hours: "",
    duration_raw: "",
    cost_usd: "0",
    languages: [] as string[],
    tags: [] as string[],
    skills: [] as string[],
    outcomes: [] as string[],
    modules: "",
    is_certification: false,
    is_active: true
  });

  const fetchCourses = async (page = 1) => {
    setIsLoading(true);
    try {
      const offset = (page - 1) * pageSize;
      const resp = await axios.get("/api/recommend/admin/courses", {
        params: {
          limit: pageSize,
          offset: offset,
          q: searchTerm || undefined
        },
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-Is-Admin": "true"
        }
      });
      setCourses(resp.data.items);
      setTotalPages(resp.data.pages);
      setCurrentPage(page);
    } catch (err) {
      showNotification("Không thể tải danh sách khóa học", "error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchCourses(1);
  }, [token]);

  // Handle search with debounce ideally, but for now reset page
  useEffect(() => {
    const timer = setTimeout(() => {
      if (token) fetchCourses(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleSave = async () => {
    try {
      const payload = {
        ...formData,
        duration_hours: formData.duration_hours ? parseFloat(formData.duration_hours) : null,
        cost_usd: formData.cost_usd ? parseFloat(formData.cost_usd) : 0,
        tags: formData.tags,
        skills_raw: formData.skills,
        outcomes: formData.outcomes,
        languages: formData.languages,
        modules: formData.modules.split('\n').map(s => s.trim()).filter(Boolean),
        source_platform: formData.source_platform || null,
        source_id: formData.source_id || null,
        external_uuid: formData.external_uuid || null
      };

      if (editingCourse) {
        await axios.patch(`/api/recommend/admin/courses/${editingCourse.id}`, payload, {
          headers: { 
            Authorization: `Bearer ${token}`,
            "X-Is-Admin": "true"
          }
        });
        showNotification("Đã cập nhật khóa học");
      } else {
        await axios.post("/api/recommend/admin/courses", payload, {
          headers: { 
            Authorization: `Bearer ${token}`,
            "X-Is-Admin": "true"
          }
        });
        showNotification("Đã tạo khóa học mới");
      }
      setIsModalOpen(false);
      fetchCourses();
    } catch (err) {
      showNotification("Lỗi khi lưu khóa học", "error");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Xóa khóa học này?")) return;
    try {
      await axios.delete(`/api/recommend/admin/courses/${id}`, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-Is-Admin": "true"
        }
      });
      showNotification("Đã xóa khóa học");
      fetchCourses();
    } catch (err) {
      showNotification("Lỗi khi xóa", "error");
    }
  };

  const openEdit = (course: Course) => {
    setEditingCourse(course);
    setFormData({
      title: course.title,
      description: course.description || "",
      platform: course.platform,
      source_platform: course.source_platform || "",
      source_id: course.source_id || "",
      external_uuid: course.external_uuid || "",
      url: course.url,
      level: course.level,
      provider: course.provider || "",
      duration_hours: course.duration_hours?.toString() || "",
      duration_raw: course.duration_raw || "",
      cost_usd: course.cost_usd.toString(),
      languages: course.languages || [],
      tags: course.tags,
      skills: course.skills_raw || [],
      outcomes: course.outcomes || [],
      modules: (course.modules || []).join("\n"),
      is_certification: course.is_certification || false,
      is_active: course.is_active ?? true
    });
    setIsModalOpen(true);
  };

  const filtered = courses.filter(c => 
    c.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.platform.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <PageHeader 
          title={t("admin_courses_title")}
          subtitle={t("admin_courses_sub")}
        >
          <div className="flex gap-3">
            <Link href="/admin/courses/import">
              <button className={cn(styles.addBtn, "bg-blue-600 hover:bg-blue-700")}>
                <Globe size={18} /> 
                {t("import_url")}
              </button>
            </Link>
            <button 
              onClick={() => {
                setEditingCourse(null);
                setFormData({ 
                  title: "", 
                  description: "",
                  platform: "", 
                  source_platform: "",
                  source_id: "",
                  external_uuid: "",
                  url: "", 
                  level: "Beginner", 
                  provider: "", 
                  duration_hours: "",
                  duration_raw: "",
                  cost_usd: "0",
                  languages: [],
                  tags: [], 
                  skills: [],
                  outcomes: [],
                  modules: "",
                  is_certification: false,
                  is_active: true
                });
                setIsModalOpen(true);
              }} 
              className={styles.addBtn}
            >
              <Plus size={18} /> 
              {t("add_course")}
            </button>
          </div>
        </PageHeader>
        <div className={styles.contentStack}>
          <div className={styles.controlBar}>
            <div className={styles.searchContainer}>
              <Search className={styles.searchIcon} />
              <input 
                type="text" 
                placeholder={t("search_course_placeholder")}
                className={styles.searchInput}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                maxLength={200}
              />
            </div>
            <button onClick={() => fetchCourses(currentPage)} className={styles.refreshBtn}>
              <RefreshCcw size={18} className={cn(isLoading && "animate-spin")} />
            </button>
          </div>

          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr className={styles.tableHeader}>
                  <th className={styles.th}>{t("table_course_platform")}</th>
                  <th className={styles.th}>{t("table_provider")}</th>
                  <th className={styles.th}>{t("table_duration_price")}</th>
                  <th className={styles.th}>{t("table_level")}</th>
                  <th className={styles.th}>{t("table_tags")}</th>
                  <th className={styles.th}>Active</th>
                  <th className={cn(styles.th, styles.thRight)}>{t("table_actions")}</th>
                </tr>
              </thead>
              <tbody>
                {courses.map((course) => (
                  <tr key={course.id} className={styles.tr}>
                    <td className={styles.td}>
                      <div className={styles.courseMainInfo}>
                         <div className={styles.courseIconBox}>
                            <BookOpen size={14} />
                         </div>
                         <div>
                            <div className={styles.courseTitleText}>{course.title}</div>
                            <div className={styles.platformName}>
                               {course.platform} 
                               <a href={course.url} target="_blank" className="ml-2 hover:text-blue-500">
                                  <ExternalLink size={12} />
                               </a>
                            </div>
                         </div>
                      </div>
                    </td>
                    <td className={styles.td}>
                       <span className={styles.levelBadge}>{course.provider || "N/A"}</span>
                    </td>
                    <td className={styles.td}>
                       <div className={styles.courseMetaInfo}>
                          <div className={styles.metaRow}>
                             <Clock size={12} /> {course.duration_raw || course.duration_hours + 'h'}
                          </div>
                          <div className={styles.metaRow}>
                             <BadgeDollarSign size={12} /> {course.cost_usd > 0 ? `$${course.cost_usd}` : 'Free'}
                          </div>
                       </div>
                    </td>
                    <td className={styles.td}>
                       <span className={styles.levelBadge}>{course.level}</span>
                    </td>
                    <td className={styles.td}>
                       <div className={styles.tagGroup}>
                          {course.tags.slice(0, 3).map(t => (
                            <span key={t} className={styles.tagBadge}>#{t}</span>
                          ))}
                          {course.tags.length > 3 && <span className={styles.tagBadge}>+{course.tags.length - 3}</span>}
                       </div>
                    </td>
                    <td className={styles.td}>
                      <div className={styles.actionGroup}>
                        <button onClick={() => openEdit(course)} className={styles.actionBtn}>
                          <Edit2 size={16} />
                        </button>
                        <button onClick={() => handleDelete(course.id)} className={cn(styles.actionBtn, styles.actionBtnDelete)}>
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Pagination 
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={(page) => fetchCourses(page)}
          />
        </div>

        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title={
            <h2 className={styles.modalTitle}>{editingCourse ? t("edit_course") : t("create_course")}</h2>
          }
          maxWidth="42rem"
        >
          <div className={styles.modalBodyContent}>
            <div className={styles.formGrid}>
                <div className={styles.sectionTitle}>{t("modal_main_info")}</div>
                <div className={cn(styles.formField, styles.formFieldFull)}>
                  <label>{t("modal_course_name")}</label>
                  <input 
                    value={formData.title}
                    onChange={e => setFormData({...formData, title: e.target.value})}
                    placeholder={t("admin_courses_eg_title")}
                  />
                </div>
                <div className={cn(styles.formField, styles.formFieldFull)}>
                  <label>{t("modal_short_desc")}</label>
                  <textarea 
                    value={formData.description}
                    onChange={e => setFormData({...formData, description: e.target.value})}
                    placeholder={t("admin_courses_desc_placeholder")}
                    maxLength={5000}
                  />
                </div>
                <div className={styles.formField}>
                  <label>{t("modal_platform")}</label>
                  <input 
                    value={formData.platform}
                    onChange={e => setFormData({...formData, platform: e.target.value})}
                    placeholder="e.g. Coursera, Udemy"
                  />
                </div>
                <div className={styles.formField}>
                  <label>{t("modal_provider")}</label>
                  <input 
                    value={formData.provider}
                    onChange={e => setFormData({...formData, provider: e.target.value})}
                    placeholder="e.g. Google, IBM"
                  />
                </div>
                <div className={styles.formField}>
                  <label>{t("modal_source")}</label>
                  <input 
                    value={formData.source_platform}
                    onChange={e => setFormData({...formData, source_platform: e.target.value})}
                    placeholder="e.g. coursera"
                  />
                </div>
                <div className={styles.formField}>
                  <label>{t("modal_source_id")}</label>
                  <input 
                    value={formData.source_id}
                    onChange={e => setFormData({...formData, source_id: e.target.value})}
                    placeholder="e.g. advanced-patterns"
                  />
                </div>
                <div className={styles.formField}>
                  <label>{t("modal_external_uuid")}</label>
                  <input 
                    value={formData.external_uuid}
                    onChange={e => setFormData({...formData, external_uuid: e.target.value})}
                    placeholder="e.g. 22-char ID"
                  />
                </div>
                <div className={cn(styles.formField, styles.formFieldFull)}>
                  <label>{t("modal_url")}</label>
                  <input 
                    value={formData.url}
                    onChange={e => setFormData({...formData, url: e.target.value})}
                    placeholder="https://..."
                  />
                </div>
                
                <div className={styles.sectionTitle}>{t("modal_details_price")}</div>
                <div className={styles.formField}>
                  <label>{t("modal_level")}</label>
                  <select 
                    value={formData.level}
                    onChange={e => setFormData({...formData, level: e.target.value})}
                  >
                      <option value="Beginner">{t("level_beginner")}</option>
                      <option value="Intermediate">{t("level_intermediate")}</option>
                      <option value="Advanced">{t("level_advanced")}</option>
                  </select>
                </div>
                <div className={styles.formField}>
                  <label>{t("modal_price")}</label>
                  <input 
                    type="number"
                    value={formData.cost_usd}
                    onChange={e => setFormData({...formData, cost_usd: e.target.value})}
                    min={0}
                    max={999999}
                  />
                </div>
                <div className={styles.formField}>
                  <label>{t("modal_duration_hr")}</label>
                  <input 
                    type="number"
                    value={formData.duration_hours}
                    onChange={e => setFormData({...formData, duration_hours: e.target.value})}
                    min={0}
                    max={10000}
                  />
                </div>
                <div className={styles.formField}>
                  <label>{t("modal_duration_text")}</label>
                  <input 
                    value={formData.duration_raw}
                    onChange={e => setFormData({...formData, duration_raw: e.target.value})}
                    placeholder="e.g. 4 weeks"
                  />
                </div>
                <div className={cn(styles.formField, styles.formFieldFull)}>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input 
                      type="checkbox"
                      className="w-4 h-4"
                      checked={formData.is_certification}
                      onChange={e => setFormData({...formData, is_certification: e.target.checked})}
                    />
                    <span>{t("modal_is_cert")}</span>
                  </label>
                </div>
                <div className={cn(styles.formField, styles.formFieldFull)}>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input 
                      type="checkbox"
                      className="w-4 h-4"
                      checked={formData.is_active}
                      onChange={e => setFormData({...formData, is_active: e.target.checked})}
                    />
                    <span className="font-bold text-indigo-500">{t("admin_courses_prod_enable")}</span>
                  </label>
                </div>

                <div className={styles.sectionTitle}>{t("modal_learning_content")}</div>
                <div className={cn(styles.formField, styles.formFieldFull)}>
                  <label>{t("modal_skills")}</label>
                  <TagInput 
                      tags={formData.skills}
                      setTags={(skills) => setFormData({...formData, skills})}
                      placeholder={t("admin_courses_skill_placeholder")}
                  />
                </div>
                <div className={cn(styles.formField, styles.formFieldFull)}>
                  <label>{t("modal_outcomes")}</label>
                  <TagInput 
                      tags={formData.outcomes}
                      setTags={(outcomes) => setFormData({...formData, outcomes})}
                      placeholder={t("admin_courses_outcome_placeholder")}
                  />
                </div>
                <div className={cn(styles.formField, styles.formFieldFull)}>
                  <label>{t("modal_languages")}</label>
                  <TagInput 
                      tags={formData.languages}
                      setTags={(languages) => setFormData({...formData, languages})}
                      placeholder={t("admin_courses_lang_placeholder")}
                  />
                </div>
                <div className={cn(styles.formField, styles.formFieldFull)}>
                  <label>{t("modal_modules")}</label>
                  <textarea 
                    className="h-32"
                    value={formData.modules}
                    onChange={e => setFormData({...formData, modules: e.target.value})}
                    placeholder="Introduction&#10;Basic Syntax&#10;Advanced Patterns..."
                    maxLength={5000}
                  />
                </div>
                <div className={cn(styles.formField, styles.formFieldFull)}>
                  <label>{t("modal_tags_input")}</label>
                  <TagInput 
                      tags={formData.tags}
                      setTags={(tags) => setFormData({...formData, tags})}
                      placeholder={t("admin_courses_tag_input_placeholder")}
                  />
                </div>
            </div>
          </div>
            <div className={styles.modalFooter}>
              <button onClick={() => setIsModalOpen(false)}>{t("cancel")}</button>
              <button onClick={handleSave} className={styles.submitBtn}>
                {editingCourse ? t("save") : t("save")}
              </button>
            </div>
        </Modal>

        <AnimatePresence>
          {notification && (
            <motion.div 
               initial={{ opacity: 0, y: 20 }}
               animate={{ opacity: 1, y: 0 }}
               exit={{ opacity: 0, y: 20 }}
               className={cn(
                 styles.notification,
                 notification.type === 'success' ? styles.notifSuccess : styles.notifError
               )}
            >
               {notification.type === 'success' ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
               <span>{notification.message}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </PageContainer>
    </AuthGuard>
  );
};

export default AdminCoursesPage;

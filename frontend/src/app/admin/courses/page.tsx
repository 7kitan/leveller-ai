"use client";

import React, { useState, useEffect } from "react";
import AuthGuard from "@/components/auth/AuthGuard";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
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
  CheckCircle2,
  AlertCircle,
  Tag
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-courses.module.css";
import { motion, AnimatePresence } from "framer-motion";

interface Course {
  id: string;
  title: string;
  platform: string;
  url: string;
  level: string;
  provider: string | null;
  duration_hours: number | null;
  cost_usd: number;
  tags: string[];
}

const AdminCoursesPage = () => {
  const { token } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null);

  const [formData, setFormData] = useState({
    title: "",
    platform: "",
    url: "",
    level: "Beginner",
    provider: "",
    tags: ""
  });

  const fetchCourses = async () => {
    setIsLoading(true);
    try {
      const resp = await axios.get("/api/recommend/admin/courses", {
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-Is-Admin": "true"
        }
      });
      setCourses(resp.data);
    } catch (err) {
      showNotification("Không thể tải danh sách khóa học", "error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchCourses();
  }, [token]);

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleSave = async () => {
    try {
      const payload = {
        ...formData,
        tags: formData.tags.split(',').map(s => s.trim()).filter(Boolean)
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
      platform: course.platform,
      url: course.url,
      level: course.level,
      provider: course.provider || "",
      tags: course.tags.join(", ")
    });
    setIsModalOpen(true);
  };

  const filtered = courses.filter(c => 
    c.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.platform.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <AuthGuard requireAdmin>
      <div className={styles.pageRoot}>
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>
              <BookOpen size={40} className={styles.headerIcon} /> 
              <span>Course Catalog Catalog</span>
            </h1>
            <p className={styles.subtitle}>Quản lý thư viện khóa học và cấu hình Knowledge Embedding.</p>
          </div>
          <button 
            onClick={() => {
              setEditingCourse(null);
              setFormData({ title: "", platform: "", url: "", level: "Beginner", provider: "", tags: "" });
              setIsModalOpen(true);
            }} 
            className={styles.addBtn}
          >
            <Plus size={18} /> 
            Thêm khóa học
          </button>
        </div>

        <div className={styles.contentStack}>
          <div className={styles.controlBar}>
            <div className={styles.searchContainer}>
              <Search className={styles.searchIcon} />
              <input 
                type="text" 
                placeholder="Tìm tên khóa học, nền tảng..." 
                className={styles.searchInput}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <button onClick={fetchCourses} className={styles.refreshBtn}>
              <RefreshCcw size={18} className={cn(isLoading && "animate-spin")} />
            </button>
          </div>

          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr className={styles.tableHeader}>
                  <th className={styles.th}>Khóa học / Nền tảng</th>
                  <th className={styles.th}>Cấp độ</th>
                  <th className={styles.th}>Tags</th>
                  <th className={cn(styles.th, styles.thRight)}>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((course) => (
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
        </div>

        <AnimatePresence>
          {isModalOpen && (
            <div className={styles.modalOverlay}>
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className={styles.modalContent}
              >
                <div className={styles.modalHeader}>
                    <h2 className={styles.modalTitle}>{editingCourse ? "Cập nhật khóa học" : "Thêm khóa học mới"}</h2>
                </div>
                <div className={styles.modalBody}>
                   <div className={styles.formGrid}>
                      <div className={styles.formField}>
                         <label>Tên khóa học</label>
                         <input 
                           value={formData.title}
                           onChange={e => setFormData({...formData, title: e.target.value})}
                           placeholder="e.g. Advanced Python Patterns"
                         />
                      </div>
                      <div className={styles.formField}>
                         <label>Nền tảng</label>
                         <input 
                           value={formData.platform}
                           onChange={e => setFormData({...formData, platform: e.target.value})}
                           placeholder="e.g. Coursera, Udemy"
                         />
                      </div>
                      <div className={styles.formField}>
                         <label>URL</label>
                         <input 
                           value={formData.url}
                           onChange={e => setFormData({...formData, url: e.target.value})}
                           placeholder="https://..."
                         />
                      </div>
                      <div className={styles.formField}>
                         <label>Cấp độ</label>
                         <select 
                           value={formData.level}
                           onChange={e => setFormData({...formData, level: e.target.value})}
                         >
                            <option value="Beginner">Beginner</option>
                            <option value="Intermediate">Intermediate</option>
                            <option value="Advanced">Advanced</option>
                         </select>
                      </div>
                      <div className={styles.formField}>
                         <label>Tags (cách nhau bởi dấu phẩy)</label>
                         <input 
                           value={formData.tags}
                           onChange={e => setFormData({...formData, tags: e.target.value})}
                           placeholder="python, backend, patterns"
                         />
                      </div>
                   </div>
                </div>
                <div className={styles.modalFooter}>
                   <button onClick={() => setIsModalOpen(false)}>Hủy</button>
                   <button onClick={handleSave} className={styles.submitBtn}>
                      {editingCourse ? "Cập nhật" : "Tạo khóa học"}
                   </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>

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
      </div>
    </AuthGuard>
  );
};

export default AdminCoursesPage;

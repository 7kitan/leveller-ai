"use client";

import React, { useEffect, useState } from "react";
import { 
  Video, 
  Search,
  Trash2,
  AlertTriangle,
  RefreshCcw,
  ExternalLink,
  CheckCircle2,
  Calendar,
  Clock,
  Video as YoutubeIcon
} from "lucide-react";
import { format } from "date-fns";
import toast from "react-hot-toast";
import Pagination from "@/components/shared/Pagination";
import Modal from "@/components/shared/Modal";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import AuthGuard from "@/components/auth/AuthGuard";
import styles from "./youtube-admin.module.css";
import { useLanguage } from "@/context/LanguageContext";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";

interface YouTubeCourse {
  id: string;
  video_id: string;
  title: string;
  description: string | null;
  channel_name: string | null;
  thumbnail: string | null;
  url: string;
  embedding_context: string | null;
  duration_raw: string | null;
  published_at: string | null;
  expires_at: string | null;
  last_verified_at: string | null;
  created_at: string;
}

const AdminYouTubePage = () => {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [courses, setCourses] = useState<YouTubeCourse[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Modals
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState<YouTubeCourse | null>(null);
  const [videoToDelete, setVideoToDelete] = useState<YouTubeCourse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0); // Optional: if backend provides total pages
  const [pageSize] = useState(10);

  const fetchYouTubeCache = async (page = 1) => {
    if (!token) return;
    try {
      setLoading(true);
      const offset = (page - 1) * pageSize;
      const url = `/admin/youtube?limit=${pageSize}&offset=${offset}${searchTerm ? `&search=${encodeURIComponent(searchTerm)}` : ""}`;
      
      const res = await api.get(url, {
        headers: { "X-Is-Admin": "true" }
      });
      
      setCourses(res.data || []);
      // Logic for total pages might need total count from backend, 
      // for now let's assume we can calculate it if backend returns total_count
      // setTotalPages(Math.ceil((res.data.total_count || 0) / pageSize));
      setCurrentPage(page);
    } catch (err) {
      console.error(err);
      toast.error(t("error"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchYouTubeCache(1);
  }, [token]);

  // Handle search resets pagination
  useEffect(() => {
    const timer = setTimeout(() => {
      if (token) fetchYouTubeCache(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const handleOpenDetails = (course: YouTubeCourse) => {
    setSelectedCourse(course);
    setShowDetailsModal(true);
  };

  const handleOpenDelete = (course: YouTubeCourse) => {
    setVideoToDelete(course);
    setShowDeleteConfirm(true);
  };

  const handleDelete = async () => {
    if (!videoToDelete || !token) return;
    setSubmitting(true);

    try {
      const res = await api.delete(`/admin/youtube/${videoToDelete.video_id}`, {
        headers: { "X-Is-Admin": "true" }
      });

      if (res.status === 200) {
        toast.success(t("admin_users_delete_success"));
        setShowDeleteConfirm(false);
        fetchYouTubeCache(currentPage);
      }
    } catch (err) {
      toast.error(t("error"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyAll = async () => {
    if (!token) return;
    try {
      setSubmitting(true);
      const res = await api.post("/admin/youtube/verify-all", {}, {
        headers: { "X-Is-Admin": "true" }
      });
      toast.success(t("admin_youtube_verify_success"));
    } catch (err) {
      toast.error(t("admin_youtube_verify_error"));
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (course: YouTubeCourse) => {
    const now = new Date();
    const expiresAt = course.expires_at ? new Date(course.expires_at) : null;
    const lastVerified = course.last_verified_at ? new Date(course.last_verified_at) : null;
    
    if (expiresAt && expiresAt < now) {
      return <span className={cn(styles.statusBadge, styles.statusExpired)}>Expired Cache</span>;
    }
    
    // If not verified for more than 7 days
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    
    if (!lastVerified || lastVerified < sevenDaysAgo) {
      return <span className={cn(styles.statusBadge, styles.statusStale)}>Verification Needed</span>;
    }
    
    return <span className={cn(styles.statusBadge, styles.statusActive)}>Active</span>;
  };

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <PageHeader 
          title={t("admin_youtube_title")}
          subtitle={t("admin_youtube_sub")}
        >
          <button 
            onClick={handleVerifyAll}
            disabled={submitting}
            className={styles.addBtn}
          >
            <RefreshCcw size={18} className={cn(submitting && "animate-spin")} /> 
            <span>{t("admin_youtube_verify_all")}</span>
          </button>
        </PageHeader>

        {/* Control Bar */}
        <div className={styles.controlBar}>
          <div className={styles.searchContainer}>
            <Search className={styles.searchIcon} />
            <input
              type="text"
              placeholder={t("admin_youtube_search_placeholder")}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={styles.searchInput}
              maxLength={200}
            />
          </div>
          <button onClick={() => fetchYouTubeCache(currentPage)} className={styles.refreshBtn}>
            <RefreshCcw size={20} className={cn(loading && "animate-spin")} />
          </button>
        </div>

        {/* YouTube Table */}
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr className={styles.tableHeader}>
                <th className={styles.th}>{t("admin_youtube_table_video")}</th>
                <th className={styles.th}>{t("admin_youtube_table_published")}</th>
                <th className={styles.th}>{t("admin_youtube_table_expires")}</th>
                <th className={styles.th}>{t("admin_youtube_table_verified")}</th>
                <th className={styles.th}>Status</th>
                <th className={cn(styles.th, styles.thRight)}>{t("admin_users_table_actions")}</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6}>
                    <div className={styles.skeletonRow}>
                      <div className={styles.spinner}></div>
                      <span className={styles.skeletonText}>{t("syncing_dots")}</span>
                    </div>
                  </td>
                </tr>
              ) : courses.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                     <div className={styles.emptyState}>
                        <YoutubeIcon size={48} className={styles.emptyStateIcon} />
                        <p className={styles.emptyStateText}>{t("jobs_no_results")}</p>
                     </div>
                  </td>
                </tr>
              ) : (
                courses.map((course) => (
                  <tr key={course.id} className={styles.tr}>
                    <td className={styles.td}>
                      <div className={styles.videoCell}>
                        <a href={course.url} target="_blank" rel="noopener noreferrer" className={styles.thumbnailWrapper}>
                          {course.thumbnail ? (
                            <img src={course.thumbnail} alt={course.title} className={styles.thumbnail} />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center bg-gray-200">
                               <Video size={24} className="text-gray-400" />
                            </div>
                          )}
                        </a>
                        <div className={styles.videoInfo}>
                          <a 
                            href={course.url} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className={styles.videoTitle} 
                            title={course.title}
                          >
                            {course.title}
                            <ExternalLink size={12} className="inline ml-1 opacity-50" />
                          </a>
                          <div className={styles.videoMeta}>
                             <span className={styles.videoId}>ID: {course.video_id}</span>
                             {course.duration_raw && <span className={styles.duration}> • {course.duration_raw}</span>}
                          </div>
                          <div className={styles.channelName}>
                             <Video size={12} /> {course.channel_name || "Unknown"}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className={styles.td}>
                      <div className={styles.dateCell}>
                        <div className="flex items-center gap-1">
                           <Calendar size={12} />
                           {course.published_at ? format(new Date(course.published_at), "dd/MM/yyyy") : t("not_available")}
                        </div>
                      </div>
                    </td>
                    <td className={styles.td}>
                      <div className={styles.dateCell}>
                        <div className="flex items-center gap-1">
                           <Clock size={12} />
                           {course.expires_at ? format(new Date(course.expires_at), "dd/MM HH:mm") : t("not_available")}
                        </div>
                      </div>
                    </td>
                    <td className={styles.td}>
                      <div className={styles.dateCell}>
                        <div className="flex items-center gap-1">
                           <RefreshCcw size={12} />
                           {course.last_verified_at ? format(new Date(course.last_verified_at), "dd/MM HH:mm") : t("not_available")}
                        </div>
                      </div>
                    </td>
                    <td className={styles.td}>
                      {getStatusBadge(course)}
                    </td>
                    <td className={styles.td}>
                       <div className={styles.actionBtnGroup}>
                          <button 
                            onClick={() => handleOpenDetails(course)}
                            className={styles.actionBtn}
                            title="View All Details"
                          >
                             <Search size={16} />
                          </button>
                          <a 
                            href={course.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className={styles.actionBtn}
                            title="View on YouTube"
                          >
                            <ExternalLink size={16} />
                          </a>
                          <button 
                            onClick={() => handleOpenDelete(course)}
                            className={cn(styles.actionBtn, styles.actionBtnDelete)}
                            title={t("delete")}
                          >
                            <Trash2 size={16} />
                          </button>
                       </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <Pagination 
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={(page) => fetchYouTubeCache(page)}
          />
        )}

        <Modal
          isOpen={showDeleteConfirm}
          onClose={() => setShowDeleteConfirm(false)}
          maxWidth="28rem"
        >
          <div className={styles.deleteModalContent}>
              <div className={styles.deleteIconBox}>
                  <AlertTriangle size={32} className={styles.deleteIcon} />
              </div>
              <div>
                <h3 className={styles.deleteConfirmTitle}>{t("admin_youtube_delete_confirm")}</h3>
                <p className={styles.deleteConfirmDesc}>
                  <span className={styles.deleteConfirmTarget}>{videoToDelete?.title}</span>
                </p>
              </div>
              <div className={styles.deleteActions}>
                  <button onClick={() => setShowDeleteConfirm(false)} className={styles.cancelDeleteBtn}>
                    {t("cancel")}
                  </button>
                  <button onClick={handleDelete} disabled={submitting} className={styles.confirmDeleteBtn}>
                    {submitting ? t("processing") : t("delete")}
                  </button>
              </div>
          </div>
        </Modal>

        {/* Details Modal */}
        <Modal
          isOpen={showDetailsModal}
          onClose={() => setShowDetailsModal(false)}
          title={
            <div className="flex items-center gap-2">
              <YoutubeIcon size={20} className="text-red-500" />
              <span>YouTube Course Details</span>
            </div>
          }
          maxWidth="50rem"
        >
          {selectedCourse && (
            <div className={styles.detailsContent}>
              <div className={styles.detailsGrid}>
                <div className={styles.detailItem}>
                   <label>ID</label>
                   <div className={styles.detailValue}>{selectedCourse.id}</div>
                </div>
                <div className={styles.detailItem}>
                   <label>Video ID</label>
                   <div className={styles.detailValue}>{selectedCourse.video_id}</div>
                </div>
                <div className={styles.detailItemFull}>
                   <label>Title</label>
                   <div className={styles.detailValue}>{selectedCourse.title}</div>
                </div>
                <div className={styles.detailItemFull}>
                   <label>Description</label>
                   <div className={styles.detailValueLong}>{selectedCourse.description || "No description"}</div>
                </div>
                <div className={styles.detailItem}>
                   <label>Channel</label>
                   <div className={styles.detailValue}>{selectedCourse.channel_name}</div>
                </div>
                <div className={styles.detailItem}>
                   <label>Duration</label>
                   <div className={styles.detailValue}>{selectedCourse.duration_raw}</div>
                </div>
                <div className={styles.detailItem}>
                   <label>Published At</label>
                   <div className={styles.detailValue}>{selectedCourse.published_at}</div>
                </div>
                <div className={styles.detailItem}>
                   <label>Created At</label>
                   <div className={styles.detailValue}>{selectedCourse.created_at}</div>
                </div>
                <div className={styles.detailItem}>
                   <label>Expires At</label>
                   <div className={styles.detailValue}>{selectedCourse.expires_at}</div>
                </div>
                <div className={styles.detailItem}>
                   <label>Last Verified</label>
                   <div className={styles.detailValue}>{selectedCourse.last_verified_at}</div>
                </div>
                <div className={styles.detailItemFull}>
                   <label>Thumbnail URL</label>
                   <div className={styles.detailValue}>{selectedCourse.thumbnail}</div>
                </div>
                <div className={styles.detailItemFull}>
                   <label>Video URL</label>
                   <div className={styles.detailValue}>{selectedCourse.url}</div>
                </div>
                <div className={styles.detailItemFull}>
                   <label>Embedding Context (Vector Input)</label>
                   <div className={styles.detailValueLong}>{selectedCourse.embedding_context}</div>
                </div>
              </div>
              <div className={styles.detailsActions}>
                 <button onClick={() => setShowDetailsModal(false)} className={styles.closeBtn}>
                   Close
                 </button>
                 <button 
                  onClick={() => {
                    setShowDetailsModal(false);
                    handleOpenDelete(selectedCourse);
                  }} 
                  className={styles.deleteDetailsBtn}
                 >
                   <Trash2 size={16} /> Delete from DB
                 </button>
              </div>
            </div>
          )}
        </Modal>
      </PageContainer>
    </AuthGuard>
  );
};

export default AdminYouTubePage;



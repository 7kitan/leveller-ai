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
  Edit,
  Video as YoutubeIcon
} from "lucide-react";
import { format } from "date-fns";
import toast from "react-hot-toast";
import Pagination from "@/components/shared/Pagination";
import Modal from "@/components/shared/Modal";
import TagInput from "@/components/shared/TagInput";
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
  // New fields
  language?: string;
  skill_level?: string;
  is_curated?: boolean;
  quality_score?: number;
  skills?: string[];
}

interface VideoPreview {
  video_id: string;
  title: string;
  description: string;
  channel_name: string;
  thumbnail: string;
  published_at: string;
  duration_raw: string;
}

const AdminYouTubePage = () => {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [courses, setCourses] = useState<YouTubeCourse[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Filters
  const [filterLanguage, setFilterLanguage] = useState<string>("all");
  const [filterLevel, setFilterLevel] = useState<string>("all");
  const [filterSkill, setFilterSkill] = useState<string>("all");
  const [availableSkills, setAvailableSkills] = useState<string[]>([]);
  
  // Modals
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showAddVideoModal, setShowAddVideoModal] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState<YouTubeCourse | null>(null);
  const [videoToDelete, setVideoToDelete] = useState<YouTubeCourse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  
  // Add Video Form
  const [videoInput, setVideoInput] = useState("");
  const [fetchingMetadata, setFetchingMetadata] = useState(false);
  const [videoPreview, setVideoPreview] = useState<VideoPreview | null>(null);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedLevel, setSelectedLevel] = useState<string>("");
  const [selectedLanguage, setSelectedLanguage] = useState<string>("");
  const [editingVideo, setEditingVideo] = useState<YouTubeCourse | null>(null);
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [pageSize] = useState(10);

  const fetchYouTubeCache = async (page = 1) => {
    if (!token) return;
    try {
      setLoading(true);
      const offset = (page - 1) * pageSize;
      
      const params = new URLSearchParams({
        limit: pageSize.toString(),
        offset: offset.toString(),
      });
      
      if (searchTerm) params.append("search", searchTerm);
      if (filterLanguage !== "all") params.append("language", filterLanguage);
      if (filterLevel !== "all") params.append("level", filterLevel);
      if (filterSkill !== "all") params.append("skill", filterSkill);
      
      const res = await api.get(`/admin/youtube?${params.toString()}`);
      
      setCourses(res.data || []);
      setCurrentPage(page);
    } catch (err) {
      console.error(err);
      toast.error(t("error"));
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableSkills = async () => {
    if (!token) return;
    try {
      const res = await api.get("/admin/youtube/skills");
      setAvailableSkills(res.data || []);
    } catch (err) {
      console.error("Failed to fetch skills", err);
    }
  };

  useEffect(() => {
    if (token) {
      fetchYouTubeCache(1);
      fetchAvailableSkills();
    }
  }, [token]);

  // Handle search and filters reset pagination
  useEffect(() => {
    const timer = setTimeout(() => {
      if (token) fetchYouTubeCache(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm, filterLanguage, filterLevel, filterSkill]);

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
      const res = await api.delete(`admin/youtube/${videoToDelete.video_id}`);

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
      const res = await api.post("admin/youtube/verify-all", {});
      toast.success(t("admin_youtube_verify_success"));
    } catch (err) {
      toast.error(t("admin_youtube_verify_error"));
    } finally {
      setSubmitting(false);
    }
  };

  const extractVideoId = (input: string): string | null => {
    // Extract video ID from various YouTube URL formats
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/,
      /^([a-zA-Z0-9_-]{11})$/
    ];
    
    for (const pattern of patterns) {
      const match = input.match(pattern);
      if (match) return match[1];
    }
    
    return null;
  };

  const handleFetchMetadata = async () => {
    const videoId = extractVideoId(videoInput);
    if (!videoId) {
      toast.error("Invalid YouTube URL or ID");
      return;
    }

    setFetchingMetadata(true);
    try {
      const res = await api.post("/admin/youtube/fetch-metadata", { video_id: videoId });
      setVideoPreview(res.data);
      toast.success("Video metadata fetched successfully");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to fetch video metadata");
      setVideoPreview(null);
    } finally {
      setFetchingMetadata(false);
    }
  };

  const handleSaveVideo = async () => {
    if (!videoPreview || selectedSkills.length === 0 || !selectedLevel || !selectedLanguage) {
      toast.error("Please fill all required fields");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/admin/youtube/curated", {
        video_id: videoPreview.video_id,
        skills: selectedSkills,
        skill_level: selectedLevel,
        language: selectedLanguage,
      });
      
      toast.success("Video added successfully");
      setShowAddVideoModal(false);
      resetAddVideoForm();
      fetchYouTubeCache(currentPage);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to save video");
    } finally {
      setSubmitting(false);
    }
  };

  const resetAddVideoForm = () => {
    setVideoInput("");
    setVideoPreview(null);
    setSelectedSkills([]);
    setSelectedLevel("");
    setSelectedLanguage("");
    setEditingVideo(null);
  };

  const handleOpenEdit = (course: YouTubeCourse) => {
    setEditingVideo(course);
    setVideoInput(course.video_id);
    setVideoPreview({
      video_id: course.video_id,
      title: course.title,
      description: course.description || "",
      channel_name: course.channel_name || "",
      thumbnail: course.thumbnail || "",
      published_at: course.published_at || "",
      duration_raw: course.duration_raw || ""
    });
    setSelectedSkills(course.skills || []);
    setSelectedLevel(course.skill_level || "");
    setSelectedLanguage(course.language || "");
    setShowAddVideoModal(true);
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
          <div className="flex gap-2">
            <button 
              onClick={() => setShowAddVideoModal(true)}
              className={styles.addBtn}
            >
              <Video size={18} /> 
              <span>{t("admin_youtube_add_video")}</span>
            </button>
            <button 
              onClick={handleVerifyAll}
              disabled={submitting}
              className={styles.verifyBtn}
            >
              <RefreshCcw size={18} className={cn(submitting && "animate-spin")} /> 
              <span>{t("admin_youtube_verify_all")}</span>
            </button>
          </div>
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
          
          {/* Filters */}
          <div className={styles.filterGroup}>
            <select 
              value={filterLanguage} 
              onChange={(e) => setFilterLanguage(e.target.value)}
              className={styles.filterSelect}
            >
              <option value="all">{t("admin_youtube_filter_language")}: {t("admin_youtube_filter_all")}</option>
              <option value="en">English</option>
              <option value="vi">Tiếng Việt</option>
            </select>

            <select 
              value={filterLevel} 
              onChange={(e) => setFilterLevel(e.target.value)}
              className={styles.filterSelect}
            >
              <option value="all">{t("admin_youtube_filter_level")}: {t("admin_youtube_filter_all")}</option>
              <option value="Junior">Junior</option>
              <option value="Mid-level">Mid-level</option>
              <option value="Senior">Senior</option>
              <option value="Expert">Expert</option>
            </select>

            <select 
              value={filterSkill} 
              onChange={(e) => setFilterSkill(e.target.value)}
              className={styles.filterSelect}
            >
              <option value="all">{t("admin_youtube_filter_skill")}: {t("admin_youtube_filter_all")}</option>
              {availableSkills.map(skill => (
                <option key={skill} value={skill}>{skill}</option>
              ))}
            </select>
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
                <th className={styles.th}>{t("admin_youtube_table_skills")}</th>
                <th className={styles.th}>{t("admin_youtube_table_level")}</th>
                <th className={styles.th}>{t("admin_youtube_table_language")}</th>
                <th className={styles.th}>{t("admin_youtube_table_published")}</th>
                <th className={styles.th}>Status</th>
                <th className={cn(styles.th, styles.thRight)}>{t("admin_users_table_actions")}</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7}>
                    <div className={styles.skeletonRow}>
                      <div className={styles.spinner}></div>
                      <span className={styles.skeletonText}>{t("syncing_dots")}</span>
                    </div>
                  </td>
                </tr>
              ) : courses.length === 0 ? (
                <tr>
                  <td colSpan={7}>
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
                          <div className="flex items-center gap-2">
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
                            {course.is_curated && (
                              <span className={styles.curatedBadge}>
                                <CheckCircle2 size={12} />
                                {t("admin_youtube_curated_badge")}
                              </span>
                            )}
                          </div>
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
                      <div className={styles.skillsCell}>
                        {course.skills && course.skills.length > 0 ? (
                          <div className={styles.skillTags}>
                            {course.skills.slice(0, 3).map((skill, idx) => (
                              <span key={idx} className={styles.skillTag}>{skill}</span>
                            ))}
                            {course.skills.length > 3 && (
                              <span className={styles.skillTag}>+{course.skills.length - 3}</span>
                            )}
                          </div>
                        ) : (
                          <span className={styles.notAvailable}>—</span>
                        )}
                      </div>
                    </td>
                    <td className={styles.td}>
                      {course.skill_level ? (
                        <span className={styles.levelBadge}>{course.skill_level}</span>
                      ) : (
                        <span className={styles.notAvailable}>—</span>
                      )}
                    </td>
                    <td className={styles.td}>
                      {course.language ? (
                        <span className={styles.languageBadge}>
                          {course.language === "en" ? "🇬🇧 EN" : "🇻🇳 VI"}
                        </span>
                      ) : (
                        <span className={styles.notAvailable}>—</span>
                      )}
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
                          <button 
                            onClick={() => handleOpenEdit(course)}
                            className={styles.actionBtn}
                            title={t("edit")}
                          >
                             <Edit size={16} />
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
                   <label>Skills</label>
                   <div className={styles.detailValue}>
                     {selectedCourse.skills?.join(", ") || "—"}
                   </div>
                </div>
                <div className={styles.detailItem}>
                   <label>Level</label>
                   <div className={styles.detailValue}>{selectedCourse.skill_level || "—"}</div>
                </div>
                <div className={styles.detailItem}>
                   <label>Language</label>
                   <div className={styles.detailValue}>{selectedCourse.language || "—"}</div>
                </div>
                <div className={styles.detailItem}>
                   <label>Curated</label>
                   <div className={styles.detailValue}>{selectedCourse.is_curated ? "Yes" : "No"}</div>
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

        {/* Add/Edit Video Modal */}
        <Modal
          isOpen={showAddVideoModal}
          onClose={() => {
            setShowAddVideoModal(false);
            resetAddVideoForm();
          }}
          title={editingVideo ? t("admin_youtube_edit_modal_title") : t("admin_youtube_add_modal_title")}
          maxWidth="45rem"
        >
          <div className={styles.addVideoContent}>
            {/* Step 1: Input YouTube URL */}
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>{t("admin_youtube_video_input")}</label>
              <div className={styles.inputWithButton}>
                <input
                  type="text"
                  placeholder={t("admin_youtube_video_input_placeholder")}
                  value={videoInput}
                  onChange={(e) => setVideoInput(e.target.value)}
                  className={styles.formInput}
                  disabled={fetchingMetadata || !!editingVideo}
                />
                {!editingVideo && (
                  <button
                    onClick={handleFetchMetadata}
                    disabled={!videoInput || fetchingMetadata}
                    className={styles.fetchBtn}
                  >
                    {fetchingMetadata ? t("admin_youtube_fetching") : t("admin_youtube_fetch_info")}
                  </button>
                )}
              </div>
              {editingVideo && (
                <p className={styles.formHint}>
                  {t("admin_youtube_editing_hint")}
                </p>
              )}
            </div>

            {/* Step 2: Video Preview */}
            {videoPreview && (
              <>
                <div className={styles.videoPreview}>
                  <img 
                    src={videoPreview.thumbnail} 
                    alt={videoPreview.title}
                    className={styles.previewThumbnail}
                  />
                  <div className={styles.previewInfo}>
                    <h4 className={styles.previewTitle}>{videoPreview.title}</h4>
                    <p className={styles.previewChannel}>{videoPreview.channel_name}</p>
                    <p className={styles.previewMeta}>
                      {videoPreview.duration_raw} • {videoPreview.published_at && format(new Date(videoPreview.published_at), "dd/MM/yyyy")}
                    </p>
                  </div>
                </div>

                {/* Step 3: Tag with Skills, Level, Language */}
                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>{t("admin_youtube_select_skills")}</label>
                  <TagInput
                    value={selectedSkills}
                    onChange={setSelectedSkills}
                    placeholder="Type to search skills or add new ones..."
                    maxTags={20}
                    disabled={submitting}
                  />
                </div>

                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>{t("admin_youtube_select_level")}</label>
                    <select
                      value={selectedLevel}
                      onChange={(e) => setSelectedLevel(e.target.value)}
                      className={styles.formSelect}
                    >
                      <option value="">Select level...</option>
                      <option value="Junior">Junior</option>
                      <option value="Mid-level">Mid-level</option>
                      <option value="Senior">Senior</option>
                      <option value="Expert">Expert</option>
                    </select>
                  </div>

                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>{t("admin_youtube_select_language")}</label>
                    <select
                      value={selectedLanguage}
                      onChange={(e) => setSelectedLanguage(e.target.value)}
                      className={styles.formSelect}
                    >
                      <option value="">Select language...</option>
                      <option value="en">English</option>
                      <option value="vi">Tiếng Việt</option>
                    </select>
                  </div>
                </div>

                <div className={styles.formActions}>
                  <button
                    onClick={() => {
                      setShowAddVideoModal(false);
                      resetAddVideoForm();
                    }}
                    className={styles.cancelBtn}
                  >
                    {t("cancel")}
                  </button>
                  <button
                    onClick={handleSaveVideo}
                    disabled={submitting || selectedSkills.length === 0 || !selectedLevel || !selectedLanguage}
                    className={styles.saveBtn}
                  >
                    {submitting ? t("processing") : (editingVideo ? t("admin_youtube_update_video") : t("admin_youtube_save_video"))}
                  </button>
                </div>
              </>
            )}
          </div>
        </Modal>
      </PageContainer>
    </AuthGuard>
  );
};

export default AdminYouTubePage;




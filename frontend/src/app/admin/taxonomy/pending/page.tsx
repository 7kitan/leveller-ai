"use client";

import React, { useEffect, useState } from "react";
import { 
  Search,
  CheckCircle,
  XCircle,
  GitMerge,
  Clock,
  AlertCircle,
  Tag,
  ExternalLink
} from "lucide-react";
import toast from "react-hot-toast";
import Pagination from "@/components/shared/Pagination";
import Modal from "@/components/shared/Modal";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import AuthGuard from "@/components/auth/AuthGuard";
import styles from "./pending-skills.module.css";
import { useLanguage } from "@/context/LanguageContext";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";

interface PendingSkill {
  id: string;
  skill_name: string;
  category: string | null;
  suggested_by: string | null;
  video_id: string | null;
  status: "pending" | "approved" | "rejected";
  created_at: string;
}

interface MasterSkill {
  id: string;
  name: string;
  category: string | null;
}

const PendingSkillsPage = () => {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [pendingSkills, setPendingSkills] = useState<PendingSkill[]>([]);
  const [masterSkills, setMasterSkills] = useState<MasterSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Modals
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [showMergeModal, setShowMergeModal] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<PendingSkill | null>(null);
  const [submitting, setSubmitting] = useState(false);
  
  // Form state for approve
  const [approveCategory, setApproveCategory] = useState("");
  
  // Form state for merge
  const [mergeTargetId, setMergeTargetId] = useState("");
  const [mergeSearchTerm, setMergeSearchTerm] = useState("");
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalSkills, setTotalSkills] = useState(0);
  const [pageSize] = useState(50);

  const fetchPendingSkills = async (page = 1) => {
    if (!token) return;
    try {
      setLoading(true);
      const offset = (page - 1) * pageSize;
      
      const params = new URLSearchParams({
        limit: pageSize.toString(),
        offset: offset.toString(),
        status: "pending"
      });
      
      if (searchTerm) params.append("search", searchTerm);
      
      const res = await api.get(`/admin/skills/pending?${params.toString()}`);
      
      setPendingSkills(res.data.pending_skills || []);
      setTotalSkills(res.data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      console.error(err);
      toast.error(t("error"));
    } finally {
      setLoading(false);
    }
  };

  const fetchMasterSkills = async () => {
    if (!token) return;
    try {
      const res = await api.get("/admin/skills?limit=2000");
      setMasterSkills(res.data.skills || []);
    } catch (err) {
      console.error("Failed to fetch master skills", err);
    }
  };

  useEffect(() => {
    if (token) {
      fetchPendingSkills(1);
      fetchMasterSkills();
    }
  }, [token]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (token) fetchPendingSkills(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const handleOpenApprove = (skill: PendingSkill) => {
    setSelectedSkill(skill);
    setApproveCategory(skill.category || "");
    setShowApproveModal(true);
  };

  const handleOpenReject = (skill: PendingSkill) => {
    setSelectedSkill(skill);
    setShowRejectModal(true);
  };

  const handleOpenMerge = (skill: PendingSkill) => {
    setSelectedSkill(skill);
    setMergeTargetId("");
    setMergeSearchTerm("");
    setShowMergeModal(true);
  };

  const handleApprove = async () => {
    if (!selectedSkill || !token) return;
    setSubmitting(true);

    try {
      await api.post(`/admin/skills/pending/${selectedSkill.id}/approve`, {
        category: approveCategory.trim() || null
      });
      
      toast.success(`Approved "${selectedSkill.skill_name}"`);
      setShowApproveModal(false);
      fetchPendingSkills(currentPage);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to approve skill");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!selectedSkill || !token) return;
    setSubmitting(true);

    try {
      await api.post(`/admin/skills/pending/${selectedSkill.id}/reject`);
      toast.success(`Rejected "${selectedSkill.skill_name}"`);
      setShowRejectModal(false);
      fetchPendingSkills(currentPage);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to reject skill");
    } finally {
      setSubmitting(false);
    }
  };

  const handleMerge = async () => {
    if (!selectedSkill || !mergeTargetId || !token) return;
    setSubmitting(true);

    try {
      await api.post(`/admin/skills/pending/${selectedSkill.id}/merge`, {
        target_skill_id: mergeTargetId
      });
      
      const targetSkill = masterSkills.find(s => s.id === mergeTargetId);
      toast.success(`Merged "${selectedSkill.skill_name}" into "${targetSkill?.name}"`);
      setShowMergeModal(false);
      fetchPendingSkills(currentPage);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to merge skill");
    } finally {
      setSubmitting(false);
    }
  };

  const filteredMasterSkills = masterSkills.filter(skill =>
    skill.name.toLowerCase().includes(mergeSearchTerm.toLowerCase())
  );

  const totalPages = Math.ceil(totalSkills / pageSize);

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <PageHeader 
          title="Pending Skills Review"
          subtitle="Review and approve user-suggested skills"
        />

        {/* Control Bar */}
        <div className={styles.controlBar}>
          <div className={styles.searchContainer}>
            <Search className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Search pending skills..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={styles.searchInput}
              maxLength={200}
            />
          </div>

          <div className={styles.stats}>
            <Clock size={16} />
            <span className={styles.statsText}>
              {totalSkills} pending
            </span>
          </div>
        </div>

        {/* Skills Table */}
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr className={styles.tableHeader}>
                <th className={styles.th}>Skill Name</th>
                <th className={styles.th}>Category</th>
                <th className={styles.th}>Source</th>
                <th className={styles.th}>Submitted</th>
                <th className={cn(styles.th, styles.thRight)}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5}>
                    <div className={styles.skeletonRow}>
                      <div className={styles.spinner}></div>
                      <span className={styles.skeletonText}>Loading pending skills...</span>
                    </div>
                  </td>
                </tr>
              ) : pendingSkills.length === 0 ? (
                <tr>
                  <td colSpan={5}>
                     <div className={styles.emptyState}>
                        <CheckCircle size={48} className={styles.emptyStateIcon} />
                        <p className={styles.emptyStateText}>No pending skills</p>
                        <p className={styles.emptyStateSubtext}>All suggestions have been reviewed</p>
                     </div>
                  </td>
                </tr>
              ) : (
                pendingSkills.map((skill) => (
                  <tr key={skill.id} className={styles.tr}>
                    <td className={styles.td}>
                      <div className={styles.skillName}>
                        <Tag size={16} className={styles.skillIcon} />
                        {skill.skill_name}
                      </div>
                    </td>
                    <td className={styles.td}>
                      {skill.category ? (
                        <span className={styles.categoryBadge}>{skill.category}</span>
                      ) : (
                        <span className={styles.noCategory}>—</span>
                      )}
                    </td>
                    <td className={styles.td}>
                      {skill.video_id ? (
                        <a 
                          href={`/admin/youtube?video=${skill.video_id}`}
                          className={styles.videoLink}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink size={14} />
                          Video
                        </a>
                      ) : (
                        <span className={styles.noSource}>Manual</span>
                      )}
                    </td>
                    <td className={styles.td}>
                      <span className={styles.dateText}>
                        {new Date(skill.created_at).toLocaleDateString()}
                      </span>
                    </td>
                    <td className={styles.td}>
                       <div className={styles.actionBtnGroup}>
                          <button 
                            onClick={() => handleOpenApprove(skill)}
                            className={cn(styles.actionBtn, styles.actionBtnApprove)}
                            title="Approve"
                          >
                             <CheckCircle size={16} />
                          </button>
                          <button 
                            onClick={() => handleOpenMerge(skill)}
                            className={cn(styles.actionBtn, styles.actionBtnMerge)}
                            title="Merge with existing"
                          >
                            <GitMerge size={16} />
                          </button>
                          <button 
                            onClick={() => handleOpenReject(skill)}
                            className={cn(styles.actionBtn, styles.actionBtnReject)}
                            title="Reject"
                          >
                            <XCircle size={16} />
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
            onPageChange={(page) => fetchPendingSkills(page)}
          />
        )}

        {/* Approve Modal */}
        <Modal
          isOpen={showApproveModal}
          onClose={() => setShowApproveModal(false)}
          title="Approve Skill"
          maxWidth="32rem"
        >
          <div className={styles.modalContent}>
            <div className={styles.approveInfo}>
              <CheckCircle size={24} className={styles.approveIcon} />
              <div>
                <p className={styles.approveText}>
                  Add <span className={styles.skillHighlight}>{selectedSkill?.skill_name}</span> to master skills database?
                </p>
              </div>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Category (optional)</label>
              <input
                type="text"
                placeholder="e.g., Technology, Tool, Methodology"
                value={approveCategory}
                onChange={(e) => setApproveCategory(e.target.value)}
                className={styles.formInput}
                maxLength={100}
              />
            </div>

            <div className={styles.modalActions}>
              <button
                onClick={() => setShowApproveModal(false)}
                className={styles.cancelBtn}
              >
                Cancel
              </button>
              <button
                onClick={handleApprove}
                disabled={submitting}
                className={styles.approveBtn}
              >
                {submitting ? "Approving..." : "Approve"}
              </button>
            </div>
          </div>
        </Modal>

        {/* Reject Modal */}
        <Modal
          isOpen={showRejectModal}
          onClose={() => setShowRejectModal(false)}
          maxWidth="28rem"
        >
          <div className={styles.rejectModalContent}>
              <div className={styles.rejectIconBox}>
                  <XCircle size={32} className={styles.rejectIcon} />
              </div>
              <div>
                <h3 className={styles.rejectTitle}>Reject Skill?</h3>
                <p className={styles.rejectDesc}>
                  Are you sure you want to reject <span className={styles.skillHighlight}>{selectedSkill?.skill_name}</span>?
                  <br />This action cannot be undone.
                </p>
              </div>
              <div className={styles.rejectActions}>
                  <button onClick={() => setShowRejectModal(false)} className={styles.cancelRejectBtn}>
                    Cancel
                  </button>
                  <button 
                    onClick={handleReject} 
                    disabled={submitting} 
                    className={styles.confirmRejectBtn}
                  >
                    {submitting ? "Rejecting..." : "Reject"}
                  </button>
              </div>
          </div>
        </Modal>

        {/* Merge Modal */}
        <Modal
          isOpen={showMergeModal}
          onClose={() => setShowMergeModal(false)}
          title="Merge with Existing Skill"
          maxWidth="36rem"
        >
          <div className={styles.modalContent}>
            <div className={styles.mergeInfo}>
              <GitMerge size={24} className={styles.mergeIcon} />
              <p className={styles.mergeText}>
                Merge <span className={styles.skillHighlight}>{selectedSkill?.skill_name}</span> into an existing skill
              </p>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Search existing skills</label>
              <input
                type="text"
                placeholder="Type to search..."
                value={mergeSearchTerm}
                onChange={(e) => setMergeSearchTerm(e.target.value)}
                className={styles.formInput}
              />
            </div>

            <div className={styles.skillList}>
              {filteredMasterSkills.slice(0, 10).map(skill => (
                <label key={skill.id} className={styles.skillOption}>
                  <input
                    type="radio"
                    name="merge-target"
                    value={skill.id}
                    checked={mergeTargetId === skill.id}
                    onChange={(e) => setMergeTargetId(e.target.value)}
                    className={styles.radio}
                  />
                  <div className={styles.skillOptionContent}>
                    <span className={styles.skillOptionName}>{skill.name}</span>
                    {skill.category && (
                      <span className={styles.skillOptionCategory}>{skill.category}</span>
                    )}
                  </div>
                </label>
              ))}
              {filteredMasterSkills.length === 0 && (
                <p className={styles.noResults}>No matching skills found</p>
              )}
            </div>

            <div className={styles.modalActions}>
              <button
                onClick={() => setShowMergeModal(false)}
                className={styles.cancelBtn}
              >
                Cancel
              </button>
              <button
                onClick={handleMerge}
                disabled={submitting || !mergeTargetId}
                className={styles.mergeBtn}
              >
                {submitting ? "Merging..." : "Merge"}
              </button>
            </div>
          </div>
        </Modal>
      </PageContainer>
    </AuthGuard>
  );
};

export default PendingSkillsPage;

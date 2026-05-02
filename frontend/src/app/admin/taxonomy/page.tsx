"use client";

import React, { useEffect, useState } from "react";
import { 
  Search,
  Plus,
  Edit,
  Trash2,
  AlertTriangle,
  Tag,
  Filter
} from "lucide-react";
import toast from "react-hot-toast";
import Pagination from "@/components/shared/Pagination";
import Modal from "@/components/shared/Modal";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import AuthGuard from "@/components/auth/AuthGuard";
import styles from "./admin-taxonomy.module.css";
import { useLanguage } from "@/context/LanguageContext";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";

interface Skill {
  id: string;
  name: string;
  category: string | null;
  parent_skill_id: string | null;
  usage_count: number;
}

interface Category {
  name: string;
  count: number;
}

const AdminTaxonomyPage = () => {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterCategory, setFilterCategory] = useState("all");
  
  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [submitting, setSubmitting] = useState(false);
  
  // Form state
  const [formName, setFormName] = useState("");
  const [formCategory, setFormCategory] = useState("");
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalSkills, setTotalSkills] = useState(0);
  const [pageSize] = useState(50);

  const fetchSkills = async (page = 1) => {
    if (!token) return;
    try {
      setLoading(true);
      const offset = (page - 1) * pageSize;
      
      const params = new URLSearchParams({
        limit: pageSize.toString(),
        offset: offset.toString(),
      });
      
      if (searchTerm) params.append("search", searchTerm);
      if (filterCategory !== "all") params.append("category", filterCategory);
      
      const res = await api.get(`/admin/skills?${params.toString()}`);
      
      setSkills(res.data.skills || []);
      setTotalSkills(res.data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      console.error(err);
      toast.error(t("error"));
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    if (!token) return;
    try {
      const res = await api.get("/admin/skills/categories");
      setCategories(res.data.categories || []);
    } catch (err) {
      console.error("Failed to fetch categories", err);
    }
  };

  useEffect(() => {
    if (token) {
      fetchSkills(1);
      fetchCategories();
    }
  }, [token]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (token) fetchSkills(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm, filterCategory]);

  const handleOpenAdd = () => {
    setFormName("");
    setFormCategory("");
    setShowAddModal(true);
  };

  const handleOpenEdit = (skill: Skill) => {
    setSelectedSkill(skill);
    setFormName(skill.name);
    setFormCategory(skill.category || "");
    setShowEditModal(true);
  };

  const handleOpenDelete = (skill: Skill) => {
    setSelectedSkill(skill);
    setShowDeleteConfirm(true);
  };

  const handleAddSkill = async () => {
    if (!formName.trim()) {
      toast.error("Skill name is required");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/admin/skills", {
        name: formName.trim(),
        category: formCategory.trim() || null
      });
      
      toast.success("Skill added successfully");
      setShowAddModal(false);
      fetchSkills(currentPage);
      fetchCategories();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to add skill");
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateSkill = async () => {
    if (!formName.trim() || !selectedSkill) {
      toast.error("Skill name is required");
      return;
    }

    setSubmitting(true);
    try {
      await api.put(`/admin/skills/${selectedSkill.id}`, {
        name: formName.trim(),
        category: formCategory.trim() || null
      });
      
      toast.success("Skill updated successfully");
      setShowEditModal(false);
      fetchSkills(currentPage);
      fetchCategories();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to update skill");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedSkill || !token) return;
    setSubmitting(true);

    try {
      await api.delete(`/admin/skills/${selectedSkill.id}`);
      toast.success("Skill deleted successfully");
      setShowDeleteConfirm(false);
      fetchSkills(currentPage);
      fetchCategories();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to delete skill");
    } finally {
      setSubmitting(false);
    }
  };

  const totalPages = Math.ceil(totalSkills / pageSize);

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <PageHeader 
          title="Skills Taxonomy"
          subtitle="Manage master skills database and categories"
        >
          <button 
            onClick={handleOpenAdd}
            className={styles.addBtn}
          >
            <Plus size={18} /> 
            <span>Add Skill</span>
          </button>
        </PageHeader>

        {/* Control Bar */}
        <div className={styles.controlBar}>
          <div className={styles.searchContainer}>
            <Search className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Search skills..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={styles.searchInput}
              maxLength={200}
            />
          </div>
          
          <div className={styles.filterGroup}>
            <Filter size={16} />
            <select 
              value={filterCategory} 
              onChange={(e) => setFilterCategory(e.target.value)}
              className={styles.filterSelect}
            >
              <option value="all">All Categories</option>
              {categories.map(cat => (
                <option key={cat.name} value={cat.name}>
                  {cat.name} ({cat.count})
                </option>
              ))}
            </select>
          </div>

          <div className={styles.stats}>
            <span className={styles.statsText}>
              {totalSkills.toLocaleString()} skills
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
                <th className={styles.th}>Usage</th>
                <th className={cn(styles.th, styles.thRight)}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4}>
                    <div className={styles.skeletonRow}>
                      <div className={styles.spinner}></div>
                      <span className={styles.skeletonText}>Loading skills...</span>
                    </div>
                  </td>
                </tr>
              ) : skills.length === 0 ? (
                <tr>
                  <td colSpan={4}>
                     <div className={styles.emptyState}>
                        <Tag size={48} className={styles.emptyStateIcon} />
                        <p className={styles.emptyStateText}>No skills found</p>
                     </div>
                  </td>
                </tr>
              ) : (
                skills.map((skill) => (
                  <tr key={skill.id} className={styles.tr}>
                    <td className={styles.td}>
                      <div className={styles.skillName}>
                        <Tag size={16} className={styles.skillIcon} />
                        {skill.name}
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
                      <span className={styles.usageCount}>
                        {skill.usage_count} {skill.usage_count === 1 ? 'video' : 'videos'}
                      </span>
                    </td>
                    <td className={styles.td}>
                       <div className={styles.actionBtnGroup}>
                          <button 
                            onClick={() => handleOpenEdit(skill)}
                            className={styles.actionBtn}
                            title="Edit"
                          >
                             <Edit size={16} />
                          </button>
                          <button 
                            onClick={() => handleOpenDelete(skill)}
                            className={cn(styles.actionBtn, styles.actionBtnDelete)}
                            title="Delete"
                            disabled={skill.usage_count > 0}
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
            onPageChange={(page) => fetchSkills(page)}
          />
        )}

        {/* Add Skill Modal */}
        <Modal
          isOpen={showAddModal}
          onClose={() => setShowAddModal(false)}
          title="Add New Skill"
          maxWidth="32rem"
        >
          <div className={styles.modalContent}>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Skill Name *</label>
              <input
                type="text"
                placeholder="e.g., React, Python, Docker"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                className={styles.formInput}
                maxLength={200}
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Category</label>
              <input
                type="text"
                placeholder="e.g., Technology, Tool, Methodology"
                value={formCategory}
                onChange={(e) => setFormCategory(e.target.value)}
                className={styles.formInput}
                maxLength={100}
              />
            </div>

            <div className={styles.modalActions}>
              <button
                onClick={() => setShowAddModal(false)}
                className={styles.cancelBtn}
              >
                Cancel
              </button>
              <button
                onClick={handleAddSkill}
                disabled={submitting || !formName.trim()}
                className={styles.saveBtn}
              >
                {submitting ? "Adding..." : "Add Skill"}
              </button>
            </div>
          </div>
        </Modal>

        {/* Edit Skill Modal */}
        <Modal
          isOpen={showEditModal}
          onClose={() => setShowEditModal(false)}
          title="Edit Skill"
          maxWidth="32rem"
        >
          <div className={styles.modalContent}>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Skill Name *</label>
              <input
                type="text"
                placeholder="e.g., React, Python, Docker"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                className={styles.formInput}
                maxLength={200}
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Category</label>
              <input
                type="text"
                placeholder="e.g., Technology, Tool, Methodology"
                value={formCategory}
                onChange={(e) => setFormCategory(e.target.value)}
                className={styles.formInput}
                maxLength={100}
              />
            </div>

            <div className={styles.modalActions}>
              <button
                onClick={() => setShowEditModal(false)}
                className={styles.cancelBtn}
              >
                Cancel
              </button>
              <button
                onClick={handleUpdateSkill}
                disabled={submitting || !formName.trim()}
                className={styles.saveBtn}
              >
                {submitting ? "Updating..." : "Update Skill"}
              </button>
            </div>
          </div>
        </Modal>

        {/* Delete Confirmation Modal */}
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
                <h3 className={styles.deleteConfirmTitle}>Delete Skill?</h3>
                <p className={styles.deleteConfirmDesc}>
                  Are you sure you want to delete <span className={styles.deleteConfirmTarget}>{selectedSkill?.name}</span>?
                  {selectedSkill && selectedSkill.usage_count > 0 && (
                    <span className={styles.deleteWarning}>
                      <br />⚠️ This skill is used in {selectedSkill.usage_count} video(s). Consider merging instead.
                    </span>
                  )}
                </p>
              </div>
              <div className={styles.deleteActions}>
                  <button onClick={() => setShowDeleteConfirm(false)} className={styles.cancelDeleteBtn}>
                    Cancel
                  </button>
                  <button 
                    onClick={handleDelete} 
                    disabled={submitting || (selectedSkill?.usage_count || 0) > 0} 
                    className={styles.confirmDeleteBtn}
                  >
                    {submitting ? "Deleting..." : "Delete"}
                  </button>
              </div>
          </div>
        </Modal>
      </PageContainer>
    </AuthGuard>
  );
};

export default AdminTaxonomyPage;

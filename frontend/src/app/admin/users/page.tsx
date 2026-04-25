"use client";

import React, { useEffect, useState } from "react";
import { 
  Shield, 
  Search,
  UserPlus,
  Trash2,
  Edit2,
  AlertTriangle,
  RefreshCcw,
  Users as UsersIcon,
  UserCheck,
  UserX
} from "lucide-react";
import { format } from "date-fns";
import toast from "react-hot-toast";
import Pagination from "@/components/shared/Pagination";
import Portal from "@/components/shared/Portal";
import Modal from "@/components/shared/Modal";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import AuthGuard from "@/components/auth/AuthGuard";
import styles from "./admin-users.module.css";
import { motion, AnimatePresence } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";
import { UserRole } from "@/types/roles";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";
import api from "@/lib/api";

interface AdminUser {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_flagged: boolean;
  daily_token_limit: number;
  today_usage: number;
  created_at: string | null;
}

const AdminUsersPage = () => {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Modal states
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");
  const [currentUser, setCurrentUser] = useState<Partial<AdminUser>>({});
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  
  // Delete confirmation
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [userToDelete, setUserToDelete] = useState<AdminUser | null>(null);
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [pageSize] = useState(10);

  const fetchUsers = async (page = 1) => {
    if (!token) return;
    try {
      setLoading(true);
      const offset = (page - 1) * pageSize;
      const url = `/auth/admin/users?limit=${pageSize}&offset=${offset}${searchTerm ? `&q=${encodeURIComponent(searchTerm)}` : ""}`;
      
      const res = await api.get(url);
      const data = res.data;
      setUsers(data.items || []);
      setTotalPages(data.pages || 0);
      setCurrentPage(page);
    } catch (err) {
      console.error(err);
      toast.error(t("error"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchUsers(1);
  }, [token]);

  // Handle search resets pagination
  useEffect(() => {
    const timer = setTimeout(() => {
      if (token) fetchUsers(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const handleOpenCreate = () => {
    setModalMode("create");
    setCurrentUser({ 
      email: "", 
      full_name: "", 
      role: UserRole.USER, 
      is_active: true,
      is_flagged: false,
      daily_token_limit: 0
    });
    setPassword("");
    setShowModal(true);
  };

  const handleOpenEdit = (user: AdminUser) => {
    setModalMode("edit");
    setCurrentUser(user);
    setPassword(""); 
    setShowModal(true);
  };

  const handleOpenDelete = (user: AdminUser) => {
    setUserToDelete(user);
    setShowDeleteConfirm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSubmitting(true);

    try {
      const url = modalMode === "create" 
        ? "/auth/admin/users" 
        : `/auth/admin/users/${currentUser.id}`;
      
      const method = modalMode === "create" ? "POST" : "PATCH";
      
      const payload: any = {
        email: currentUser.email,
        full_name: currentUser.full_name,
        role: currentUser.role,
        is_active: currentUser.is_active,
        is_flagged: currentUser.is_flagged,
        daily_token_limit: currentUser.daily_token_limit,
      };
      
      if (password) payload.password = password;
      if (modalMode === "create" && !password) {
          toast.error(t("admin_users_password_hint"));
          setSubmitting(false);
          return;
      }

      const res = modalMode === "create"
        ? await api.post(url, payload)
        : await api.patch(url, payload);

      if (res.status === 200 || res.status === 201) {
        toast.success(modalMode === "create" ? t("admin_users_create_success") : t("admin_users_update_success"));
        setShowModal(false);
        fetchUsers();
      } else {
        toast.error(t("error"));
      }
    } catch (err) {
      toast.error(t("error"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!userToDelete || !token) return;
    setSubmitting(true);

    try {
      const res = await api.delete(`/auth/admin/users/${userToDelete.id}`);

      if (res.status === 200 || res.status === 204) {
        toast.success(t("admin_users_delete_success"));
        setShowDeleteConfirm(false);
        fetchUsers();
      } else {
        toast.error(t("error"));
      }
    } catch (err) {
      toast.error(t("error"));
    } finally {
      setSubmitting(false);
    }
  };

  const filteredUsers = users;

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <PageHeader 
          title={t("admin_users_title")}
          subtitle={t("admin_users_subtitle")}
        >
          <button 
            onClick={handleOpenCreate}
            className={styles.addBtn}
          >
            <UserPlus size={18} /> 
            <span>{t("admin_users_add_btn")}</span>
          </button>
        </PageHeader>

        {/* Control Bar */}
        <div className={styles.controlBar}>
          <div className={styles.searchContainer}>
            <Search className={styles.searchIcon} />
            <input
              type="text"
              placeholder={t("admin_users_search_placeholder")}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={styles.searchInput}
              maxLength={200}
            />
          </div>
          <button onClick={() => fetchUsers(currentPage)} className={styles.refreshBtn}>
            <RefreshCcw size={20} className={cn(loading && "animate-spin")} />
          </button>
        </div>

        {/* Users Table */}
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr className={styles.tableHeader}>
                <th className={styles.th}>{t("admin_users_table_user")}</th>
                <th className={styles.th}>{t("admin_users_table_role")}</th>
                <th className={styles.th}>Usage (Today)</th>
                <th className={styles.th}>{t("admin_users_table_status")}</th>
                <th className={styles.th}>{t("admin_users_table_date")}</th>
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
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                     <div className={styles.emptyState}>
                        <UsersIcon size={48} className={styles.emptyStateIcon} />
                        <p className={styles.emptyStateText}>{t("jobs_no_results")}</p>
                     </div>
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => (
                  <tr key={user.id} className={styles.tr}>
                    <td className={styles.td}>
                      <div className={styles.userCell}>
                        <div className={styles.avatar}>
                          {(user.full_name?.[0] || user.email[0]).toUpperCase()}
                        </div>
                        <div>
                          <div className={styles.userName}>
                            {user.full_name || t("fail")}
                            {user.is_flagged && <span title="Flagged for review"><AlertTriangle size={14} className="inline ml-2 text-amber-500" /></span>}
                          </div>
                          <div className={styles.userEmail}>{user.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className={styles.td}>
                      <span className={cn(
                        styles.roleBadge,
                        user.role === UserRole.ADMIN ? styles.roleAdmin : styles.roleUser
                      )}>
                        {user.role === UserRole.ADMIN ? t("admin_users_role_admin") : 
                         user.role === UserRole.USER ? t("admin_users_role_user") : 
                         user.role?.toUpperCase()}
                      </span>
                    </td>
                    <td className={styles.td}>
                       <div className={styles.usageContainer}>
                          <div className={styles.usageText}>
                            {user.today_usage.toLocaleString()} / {user.daily_token_limit > 0 ? user.daily_token_limit.toLocaleString() : "Global"}
                          </div>
                          <div className={styles.usageBar}>
                             <div 
                                className={styles.usageFill} 
                                style={{ 
                                  width: `${Math.min(100, (user.today_usage / (user.daily_token_limit || 50000)) * 100)}%`,
                                  backgroundColor: (user.today_usage / (user.daily_token_limit || 50000)) > 0.8 ? '#f43f5e' : '#10b981'
                                }} 
                             />
                          </div>
                       </div>
                    </td>
                    <td className={styles.td}>
                      <span className={cn(
                        styles.statusBadge,
                        user.is_active ? styles.statusActive : styles.statusBanned
                      )}>
                        {user.is_active ? t("admin_users_status_active") : t("admin_users_status_banned")}
                      </span>
                    </td>
                    <td className={styles.td}>
                      <div className={styles.userDate}>
                        {user.created_at ? format(new Date(user.created_at), "dd/MM/yyyy") : t("not_available")}
                      </div>
                    </td>
                    <td className={styles.td}>
                       <div className={styles.actionBtnGroup}>
                          <button 
                            onClick={async () => {
                              if (!token) return;
                              const res = await fetch(`/auth/admin/users/${user.id}`, {
                                method: "PATCH",
                                headers: {
                                  "Content-Type": "application/json",
                                  "Authorization": `Bearer ${token}`
                                },
                                body: JSON.stringify({ is_active: !user.is_active })
                              });
                              if (res.ok) {
                                toast.success(user.is_active ? t("admin_users_status_banned") : t("admin_users_status_active"));
                                fetchUsers(currentPage);
                              } else {
                                toast.error(t("error"));
                              }
                            }}
                            className={styles.actionBtn}
                            title={user.is_active ? t("admin_users_status_banned") : t("admin_users_status_active")}
                          >
                            {user.is_active ? <UserX size={16} /> : <UserCheck size={16} />}
                          </button>
                          <button 
                            onClick={() => handleOpenEdit(user)}
                            className={cn(styles.actionBtn, styles.actionBtnEdit)}
                          >
                            <Edit2 size={16} />
                          </button>
                          <button 
                            onClick={() => handleOpenDelete(user)}
                            className={cn(styles.actionBtn, styles.actionBtnDelete)}
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

        <Pagination 
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={(page) => fetchUsers(page)}
        />

        <Modal
          isOpen={showModal}
          onClose={() => setShowModal(false)}
          title={
            <h3 className={styles.modalTitle}>
              <UsersIcon size={24} /> 
              <span>{modalMode === "create" ? t("admin_users_create_modal_title") : t("admin_users_edit_modal_title")}</span>
            </h3>
          }
        >
          <form onSubmit={handleSubmit} className={styles.modalForm}>
              <div className={styles.formFieldGroup}>
                  <div className={styles.formField}>
                      <label className={styles.inputLabel}>{t("admin_users_email_label")}</label>
                      <input
                          type="email"
                          required
                          value={currentUser.email || ""}
                          onChange={(e) => setCurrentUser({...currentUser, email: e.target.value})}
                          className={styles.modalInput}
                          maxLength={255}
                      />
                  </div>
                  <div className={styles.formField}>
                      <label className={styles.inputLabel}>{t("admin_users_name_label")}</label>
                      <input
                          type="text"
                          value={currentUser.full_name || ""}
                          onChange={(e) => setCurrentUser({...currentUser, full_name: e.target.value})}
                          className={styles.modalInput}
                          maxLength={255}
                      />
                  </div>
                  <div className={styles.formField}>
                      <label className={styles.inputLabel}>{t("admin_users_password_label")} {modalMode === "edit" && t("admin_users_password_hint")}</label>
                      <input
                          type="password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          className={styles.modalInput}
                          maxLength={128}
                          minLength={8}
                      />
                  </div>
                  <div className={styles.formField}>
                      <label className={styles.inputLabel}>{t("admin_users_role_label") || "Role"}</label>
                      <select 
                          value={currentUser.role || UserRole.USER}
                          onChange={(e) => setCurrentUser({...currentUser, role: e.target.value})}
                          className={styles.modalInput}
                      >
                          <option value={UserRole.USER}>{t("admin_users_role_user")}</option>
                          <option value={UserRole.ADMIN}>{t("admin_users_role_admin")}</option>
                          <option value={UserRole.STUDENT}>{t("admin_users_role_student") || "STUDENT"}</option>
                      </select>
                  </div>
                   <div className={styles.checkboxGroup}>
                      <div className={styles.checkboxLabelArea}>
                          <span className={styles.checkboxTitle}>Flagged for Review</span>
                          <span className={styles.checkboxDesc}>Mark user as suspicious</span>
                      </div>
                      <input 
                          type="checkbox"
                          checked={currentUser.is_flagged || false}
                          onChange={(e) => setCurrentUser({...currentUser, is_flagged: e.target.checked})}
                          className={styles.checkboxInput}
                      />
                  </div>
                  <div className={styles.formField}>
                      <label className={styles.inputLabel}>Daily Token Limit (0 = Default)</label>
                      <input
                          type="number"
                          value={currentUser.daily_token_limit ?? 0}
                          onChange={(e) => setCurrentUser({...currentUser, daily_token_limit: parseInt(e.target.value) || 0})}
                          className={styles.modalInput}
                          min={0}
                          max={1000000}
                      />
                  </div>
              </div>

              <div className={styles.formActions}>
                  <button type="button" onClick={() => setShowModal(false)} className={styles.cancelBtn}>
                    {t("cancel")}
                  </button>
                  <button type="submit" disabled={submitting} className={styles.submitBtn}>
                      {submitting ? t("processing") : t("admin_users_save_btn")}
                  </button>
              </div>
          </form>
        </Modal>

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
                <h3 className={styles.deleteConfirmTitle}>{t("admin_users_delete_title")}</h3>
                <p className={styles.deleteConfirmDesc}>{t("admin_users_table_user")} <span className={styles.deleteConfirmTarget}>{userToDelete?.full_name || userToDelete?.email}</span> {t("admin_users_delete_desc")}</p>
              </div>
              <div className={styles.deleteActions}>
                  <button onClick={() => setShowDeleteConfirm(false)} className={styles.cancelDeleteBtn}>
                    {t("cancel")}
                  </button>
                  <button onClick={handleDelete} className={styles.confirmDeleteBtn}>
                    {t("admin_users_delete_confirm")}
                  </button>
              </div>
          </div>
        </Modal>
      </PageContainer>
    </AuthGuard>
  );
};

export default AdminUsersPage;



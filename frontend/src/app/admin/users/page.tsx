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
  Users as UsersIcon
} from "lucide-react";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import AuthGuard from "@/components/auth/AuthGuard";
import styles from "./admin-users.module.css";
import { motion, AnimatePresence } from "framer-motion";

interface AdminUser {
  id: string;
  email: string;
  full_name: string | null;
  is_admin: boolean;
  is_active?: boolean;
  created_at: string | null;
}

const AdminUsersPage = () => {
  const { token } = useAuth();
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

  const fetchUsers = async () => {
    if (!token) return;
    try {
      setLoading(true);
      const res = await fetch("/api/auth/admin/users", {
        headers: { 
          "X-Is-Admin": "true",
          "Authorization": `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error("Failed to fetch users");
      const data = await res.json();
      setUsers(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      toast.error("Không thể tải danh sách người dùng");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [token]);

  const handleOpenCreate = () => {
    setModalMode("create");
    setCurrentUser({ email: "", full_name: "", is_admin: false });
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
        ? "/api/auth/admin/users" 
        : `/api/auth/admin/users/${currentUser.id}`;
      
      const method = modalMode === "create" ? "POST" : "PATCH";
      
      const payload: any = {
        email: currentUser.email,
        full_name: currentUser.full_name,
        is_admin: currentUser.is_admin,
      };
      
      if (password) payload.password = password;
      if (modalMode === "create" && !password) {
          toast.error("Vui lòng nhập mật khẩu cho người dùng mới");
          setSubmitting(false);
          return;
      }

      const res = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-Is-Admin": "true",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        toast.success(modalMode === "create" ? "Tạo người dùng thành công" : "Cập nhật thành công");
        setShowModal(false);
        fetchUsers();
      } else {
        const err = await res.json();
        toast.error(err.detail || "Đã có lỗi xảy ra");
      }
    } catch (err) {
      toast.error("Lỗi kết nối Server");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!userToDelete || !token) return;
    setSubmitting(true);

    try {
      const res = await fetch(`/api/auth/admin/users/${userToDelete.id}`, {
        method: "DELETE",
        headers: {
          "X-Is-Admin": "true",
          "Authorization": `Bearer ${token}`
        }
      });

      if (res.ok) {
        toast.success("Đã xóa người dùng");
        setShowDeleteConfirm(false);
        fetchUsers();
      } else {
        toast.error("Không thể xóa người dùng");
      }
    } catch (err) {
      toast.error("Lỗi kết nối Server");
    } finally {
      setSubmitting(false);
    }
  };

  const filteredUsers = users.filter(u => 
    u.email.toLowerCase().includes(searchTerm.toLowerCase()) || 
    (u.full_name?.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <AuthGuard requireAdmin>
      <div className={styles.pageRoot}>
        {/* Header */}
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>
              <UsersIcon size={32} /> 
              <span>Quản trị Người dùng</span>
            </h1>
            <p className={styles.subtitle}>Quản lý tài khoản, phân quyền và giám sát hoạt động hệ thống.</p>
          </div>
          
          <button 
            onClick={handleOpenCreate}
            className={styles.addBtn}
            style={{ backgroundColor: "#818cf8" }}
          >
            <UserPlus size={18} /> 
            <span>Thêm tài khoản</span>
          </button>
        </div>

        {/* Control Bar */}
        <div className={styles.controlBar}>
          <div className={styles.searchContainer}>
            <Search className={styles.searchIcon} />
            <input 
              type="text"
              placeholder="Tìm kiếm theo email, tên..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={styles.searchInput}
            />
          </div>
          <button onClick={fetchUsers} className={styles.refreshBtn}>
            <RefreshCcw size={20} className={cn(loading && "animate-spin")} />
          </button>
        </div>

        {/* Users Table */}
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr className={styles.tableHeader}>
                <th className={styles.th}>Người dùng</th>
                <th className={styles.th}>Vai trò</th>
                <th className={styles.th}>ID Hệ thống</th>
                <th className={styles.th}>Ngày tham gia</th>
                <th className={cn(styles.th)} style={{ textAlign: "right" }}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5}>
                    <div className={styles.skeletonRow}>
                      <div className={styles.spinner}></div>
                      <span style={{ fontSize: "10px", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.2em", color: "rgba(255,255,255,0.2)", fontStyle: "italic" }}>Synchronizing...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={5}>
                     <div className={styles.emptyState}>
                        <UsersIcon size={48} style={{ color: "rgba(255,255,255,0.2)" }} />
                        <p style={{ fontSize: "0.875rem", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.2em", color: "rgba(255,255,255,0.2)", fontStyle: "italic" }}>Không tìm thấy người dùng</p>
                     </div>
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => (
                  <tr key={user.id} className={styles.tr}>
                    <td className={styles.td}>
                      <div className={styles.userCell}>
                        <div className={styles.avatar}>
                          {user.email.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className={styles.userName}>{user.full_name || "Chưa cập nhật tên"}</div>
                          <div className={styles.userEmail}>{user.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className={styles.td}>
                      <span className={cn(
                        styles.roleBadge,
                        user.is_admin ? styles.roleAdmin : styles.roleUser
                      )}>
                        {user.is_admin ? "ADMIN" : "USER"}
                      </span>
                    </td>
                    <td className={styles.td}>
                      <div style={{ fontFamily: "monospace", fontSize: "10px", color: "rgba(255,255,255,0.1)", letterSpacing: "-0.02em" }}>
                        {user.id.substring(0, 13)}...
                      </div>
                    </td>
                    <td className={styles.td}>
                      <div style={{ fontSize: "10px", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.15em", color: "rgba(255,255,255,0.2)" }}>
                        {user.created_at ? format(new Date(user.created_at), "dd/MM/yyyy") : "N/A"}
                      </div>
                    </td>
                    <td className={styles.td}>
                       <div className={styles.actionBtnGroup}>
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

        {/* User Modal (Create/Edit) */}
        <AnimatePresence>
          {showModal && (
            <div className={styles.modalOverlay}>
              <motion.div 
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                className={styles.modalContent}
              >
                <div className={styles.modalHeader}>
                    <h3 className={styles.modalTitle}>
                        <UsersIcon size={24} /> 
                        <span>{modalMode === "create" ? "Cấp phép Tài khoản" : "Hiệu chỉnh Profile"}</span>
                    </h3>
                </div>
                <form onSubmit={handleSubmit} className={styles.modalForm}>
                    <div className={styles.formFieldGroup}>
                        <div className={styles.formField}>
                            <label className={styles.inputLabel}>Địa chỉ Email</label>
                            <input 
                                required
                                type="email"
                                value={currentUser.email || ""}
                                onChange={(e) => setCurrentUser({...currentUser, email: e.target.value})}
                                className={styles.modalInput}
                            />
                        </div>
                        <div className={styles.formField}>
                            <label className={styles.inputLabel}>Họ và tên</label>
                            <input 
                                type="text"
                                value={currentUser.full_name || ""}
                                onChange={(e) => setCurrentUser({...currentUser, full_name: e.target.value})}
                                className={styles.modalInput}
                            />
                        </div>
                        <div className={styles.formField}>
                            <label className={styles.inputLabel}>Mật khẩu {modalMode === "edit" && "(Bỏ trống nếu không đổi)"}</label>
                            <input 
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className={styles.modalInput}
                            />
                        </div>
                        <div className={styles.checkboxGroup}>
                            <div className={styles.checkboxLabelArea}>
                                <span className={styles.checkboxTitle}>Quyền Quản trị viên</span>
                                <span className={styles.checkboxDesc}>Truy cập Dashboard cấu hình hệ thống.</span>
                            </div>
                            <input 
                                type="checkbox"
                                checked={currentUser.is_admin || false}
                                onChange={(e) => setCurrentUser({...currentUser, is_admin: e.target.checked})}
                                style={{ width: "1.25rem", height: "1.25rem" }}
                            />
                        </div>
                    </div>

                    <div className={styles.formActions}>
                        <button type="button" onClick={() => setShowModal(false)} className={styles.cancelBtn}>
                          Hủy
                        </button>
                        <button type="submit" disabled={submitting} className={styles.submitBtn}>
                            {submitting ? "Đang xử lý..." : "Lưu cấu hình"}
                        </button>
                    </div>
                </form>
              </motion.div>
            </div>
          )}
        </AnimatePresence>

        {/* Delete Confirm */}
        <AnimatePresence>
          {showDeleteConfirm && (
            <div className={styles.modalOverlay}>
                <motion.div 
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className={styles.deleteModalContent}
                >
                    <div className={styles.deleteIconBox}>
                        <AlertTriangle size={32} style={{ color: "#f43f5e" }} />
                    </div>
                    <div>
                      <h3 className={styles.deleteConfirmTitle}>Xác nhận xóa?</h3>
                      <p className={styles.deleteConfirmDesc}>Tài khoản <span style={{ color: "white", fontWeight: 900 }}>{userToDelete?.email}</span> sẽ bị xóa vĩnh viễn khỏi hệ thống.</p>
                    </div>
                    <div className={styles.deleteActions}>
                        <button onClick={() => setShowDeleteConfirm(false)} className={styles.cancelDeleteBtn}>
                          Hủy
                        </button>
                        <button onClick={handleDelete} className={styles.confirmDeleteBtn}>
                          Xác nhận xóa
                        </button>
                    </div>
                </motion.div>
            </div>
          )}
        </AnimatePresence>
      </div>
    </AuthGuard>
  );
};

export default AdminUsersPage;

"use client";

import React, { useEffect, useState } from "react";
import { 
  Users, 
  Mail, 
  Shield, 
  Calendar, 
  Search,
  Filter,
  UserPlus,
  ArrowUpDown,
  UserCheck,
  Edit2,
  Trash2,
  X,
  Key,
  Save,
  AlertTriangle,
  RefreshCcw,
  Users as UsersIcon
} from "lucide-react";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthContext";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import AuthGuard from "@/components/auth/AuthGuard";
import styles from "./admin-users.module.css";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

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
    setPassword(""); // Keep blank unless changing
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
              <UsersIcon className="text-indigo-500 w-8 h-8" /> Quản trị Người dùng
            </h1>
            <p className={styles.subtitle}>Quản lý tài khoản, phân quyền và giám sát hoạt động hệ thống.</p>
          </div>
          
          <div className="flex items-center gap-3">
            <button 
              onClick={handleOpenCreate}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-2xl text-sm font-bold text-white shadow-lg shadow-indigo-500/20 transition-all flex items-center gap-2"
            >
              <UserPlus size={18} /> Add User
            </button>
          </div>
        </div>

        {/* Control Bar */}
        <div className={styles.controlBar}>
          <div className={styles.searchWrapper}>
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
            <RefreshCcw className={cn("w-5 h-5", loading && "animate-spin")} />
          </button>
        </div>

        {/* Users Table */}
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr className={styles.tableHeader}>
                <th className="px-8 py-5">Người dùng</th>
                <th className="px-8 py-5">Vai trò</th>
                <th className="px-8 py-5">ID Hệ thống</th>
                <th className="px-8 py-5">Ngày tham gia</th>
                <th className="px-8 py-5 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40 text-slate-300">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-8 py-20 text-center">
                    <div className="flex flex-col items-center gap-4">
                      <div className="w-10 h-10 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin"></div>
                      <span className="text-white/20 font-black uppercase tracking-widest text-xs">Synchronizing...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-8 py-20 text-center text-white/20 font-bold italic">
                    Không tìm thấy người dùng phù hợp.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => (
                  <tr key={user.id} className={styles.tableRow}>
                    <td className="px-8 py-6">
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
                    <td className="px-8 py-6">
                      <span className={cn(
                        styles.roleBadge,
                        user.is_admin ? styles.roleAdmin : styles.roleUser
                      )}>
                        {user.is_admin ? "ADMIN" : "USER"}
                      </span>
                    </td>
                    <td className="px-8 py-6 font-mono text-[10px] text-slate-500">
                      {user.id.substring(0, 13)}...
                    </td>
                    <td className="px-8 py-6 text-xs text-slate-500">
                      {user.created_at ? format(new Date(user.created_at), "dd/MM/yyyy") : "N/A"}
                    </td>
                    <td className="px-8 py-6 text-right">
                       <div className="flex items-center justify-end gap-2 px-4">
                          <button 
                            onClick={() => handleOpenEdit(user)}
                            className="p-2 bg-white/5 hover:bg-indigo-600/20 text-slate-400 hover:text-indigo-400 rounded-xl transition-all border border-transparent hover:border-indigo-500/30"
                          >
                            <Edit2 size={16} />
                          </button>
                          <button 
                            onClick={() => handleOpenDelete(user)}
                            className="p-2 bg-white/5 hover:bg-rose-600/20 text-slate-400 hover:text-rose-400 rounded-xl transition-all border border-transparent hover:border-rose-500/30"
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

        {/* Modals & Toasts logic remains same as per original file functionality */}
        {/* ... (Modals would be here, omitting for brevity of refactor focus but keep them in sync) */}
        
        {/* User Modal (Create/Edit) */}
        {showModal && (
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-lg p-6 animate-in fade-in">
                <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden">
                <div className="p-8 border-b border-slate-800 bg-indigo-500/5">
                    <h3 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
                        <UsersIcon className="w-6 h-6 text-indigo-500" /> {modalMode === "create" ? "Tạo Người Dùng" : "Chỉnh Sửa Profile"}
                    </h3>
                </div>
                <form onSubmit={handleSubmit} className="p-8 space-y-6">
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Email</label>
                            <input 
                                required
                                type="email"
                                value={currentUser.email || ""}
                                onChange={(e) => setCurrentUser({...currentUser, email: e.target.value})}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white outline-none focus:ring-2 focus:ring-indigo-500/50"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Họ tên</label>
                            <input 
                                type="text"
                                value={currentUser.full_name || ""}
                                onChange={(e) => setCurrentUser({...currentUser, full_name: e.target.value})}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white outline-none focus:ring-2 focus:ring-indigo-500/50"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Mật khẩu</label>
                            <input 
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white outline-none focus:ring-2 focus:ring-indigo-500/50"
                            />
                        </div>
                        <div className="flex items-center justify-between p-4 bg-slate-800/20 rounded-2xl border border-slate-800">
                            <div>
                                <div className="text-sm font-bold text-white">Quyền Quản trị</div>
                                <div className="text-[10px] text-slate-500 uppercase">Truy cập Dashboard Admin</div>
                            </div>
                            <input 
                                type="checkbox"
                                checked={currentUser.is_admin || false}
                                onChange={(e) => setCurrentUser({...currentUser, is_admin: e.target.checked})}
                                className="w-5 h-5 accent-indigo-500"
                            />
                        </div>
                    </div>

                    <div className="flex justify-end gap-4">
                        <button type="button" onClick={() => setShowModal(false)} className="px-6 py-3 text-slate-500 hover:text-white font-bold transition-colors">Hủy</button>
                        <button 
                            type="submit" 
                            disabled={submitting}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3 rounded-2xl font-black transition-all shadow-xl shadow-indigo-600/20"
                        >
                            {submitting ? "Đang lưu..." : "Lưu thay đổi"}
                        </button>
                    </div>
                </form>
                </div>
            </div>
        )}

        {/* Delete Confirm */}
        {showDeleteConfirm && (
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-lg p-6 animate-in fade-in">
                <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-8 text-center space-y-6">
                    <div className="w-20 h-20 mx-auto bg-rose-500/10 rounded-full flex items-center justify-center text-rose-500">
                        <AlertTriangle className="w-10 h-10" />
                    </div>
                    <h3 className="text-2xl font-bold text-white">Xác nhận xóa?</h3>
                    <p className="text-slate-400">Tài khoản <span className="text-white font-bold">{userToDelete?.email}</span> sẽ bị xóa vĩnh viễn.</p>
                    <div className="flex gap-4">
                        <button onClick={() => setShowDeleteConfirm(false)} className="flex-1 px-6 py-4 bg-slate-800 hover:bg-slate-700 rounded-2xl text-white font-bold transition-all">Hủy</button>
                        <button onClick={handleDelete} className="flex-1 px-6 py-4 bg-rose-600 hover:bg-rose-500 rounded-2xl text-white font-bold transition-all">Xác nhận xóa</button>
                    </div>
                </div>
            </div>
        )}
      </div>
    </AuthGuard>
  );
};

export default AdminUsersPage;

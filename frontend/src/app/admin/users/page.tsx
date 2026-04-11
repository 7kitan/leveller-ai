"use client";

import React, { useEffect, useState } from "react";
import { 
  Users, 
  Mail, 
  Shield, 
  Calendar, 
  Search,
  Filter,
  MoreVertical,
  UserPlus,
  ArrowUpDown,
  UserCheck,
  UserX,
  Edit2,
  Trash2,
  X,
  Key,
  Save,
  AlertTriangle
} from "lucide-react";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthContext";

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
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center gap-3 text-violet-400 font-black text-xs uppercase tracking-[0.3em] mb-2">
            <Shield size={14} /> Security Module
          </div>
          <h1 className="text-4xl font-black text-white tracking-tighter">User Management</h1>
          <p className="text-white/40 font-medium tracking-tight">Quản lý định danh và phân quyền hệ thống.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <button 
            onClick={fetchUsers}
            className="px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-2xl text-sm font-bold text-white transition-all flex items-center gap-2"
          >
            Refresh
          </button>
          <button 
            onClick={handleOpenCreate}
            className="px-6 py-3 bg-violet-600 hover:bg-violet-500 rounded-2xl text-sm font-bold text-white shadow-lg shadow-violet-500/20 transition-all flex items-center gap-2"
          >
            <UserPlus size={18} /> Add User
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white/3 border border-white/5 rounded-3xl p-6 backdrop-blur-xl">
          <div className="text-white/30 text-xs font-black uppercase tracking-widest mb-4">Tổng tài khoản</div>
          <div className="text-3xl font-black text-white">{users.length}</div>
        </div>
        <div className="bg-white/3 border border-white/5 rounded-3xl p-6 backdrop-blur-xl">
          <div className="text-white/30 text-xs font-black uppercase tracking-widest mb-4">Quản trị viên</div>
          <div className="text-3xl font-black text-emerald-400">{users.filter(u => u.is_admin).length}</div>
        </div>
        <div className="bg-white/3 border border-white/5 rounded-3xl p-6 backdrop-blur-xl">
          <div className="text-white/30 text-xs font-black uppercase tracking-widest mb-4">Người dùng mới (30d)</div>
          <div className="text-3xl font-black text-violet-400">
            {users.filter(u => u.created_at && new Date(u.created_at) > new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)).length}
          </div>
        </div>
      </div>

      {/* Control Bar */}
      <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-white/3 border border-white/5 p-4 rounded-[2rem] backdrop-blur-xl">
        <div className="relative w-full md:w-96 group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20 group-focus-within:text-violet-500 transition-colors" size={18} />
          <input 
            type="text"
            placeholder="Tìm kiếm theo email, tên..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-sm text-white focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500/50 transition-all"
          />
        </div>
        <div className="flex items-center gap-2">
           <button className="p-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-white/60 hover:text-white transition-all">
              <Filter size={18} />
           </button>
           <button className="p-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-white/60 hover:text-white transition-all text-xs font-bold px-4 uppercase tracking-widest">
              Export
           </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white/3 border border-white/5 rounded-[2.5rem] overflow-hidden backdrop-blur-xl relative">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/5">
                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">User Info</th>
                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">Role</th>
                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">Hệ thống ID</th>
                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">Joined Date</th>
                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-[0.2em] text-white/30 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-8 py-20 text-center">
                    <div className="flex flex-col items-center gap-4">
                      <div className="w-10 h-10 border-4 border-violet-500/20 border-t-violet-500 rounded-full animate-spin"></div>
                      <span className="text-white/20 font-black uppercase tracking-widest text-xs">Synchronizing users...</span>
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
                  <tr key={user.id} className="group hover:bg-white/[0.02] transition-colors">
                    <td className="px-8 py-6">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-white/5 to-white/10 border border-white/10 flex items-center justify-center text-white/40 font-black">
                          {user.email.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="text-white font-bold group-hover:text-violet-400 transition-colors">{user.full_name || "Chưa cập nhật tên"}</div>
                          <div className="text-xs text-white/40 flex items-center gap-1.5 mt-1">
                            <Mail size={12} className="opacity-50" /> {user.email}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-8 py-6">
                      {user.is_admin ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-black uppercase tracking-widest rounded-lg">
                          <UserCheck size={12} /> Administrator
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/5 border border-white/10 text-white/40 text-[10px] font-black uppercase tracking-widest rounded-lg">
                          Normal User
                        </span>
                      )}
                    </td>
                    <td className="px-8 py-6">
                      <code className="text-[10px] font-mono text-white/30 bg-black/20 px-2 py-1 rounded">
                        {user.id.substring(0, 13)}...
                      </code>
                    </td>
                    <td className="px-8 py-6">
                      <div className="flex items-center gap-2 text-white/50 text-xs font-medium">
                        <Calendar size={14} className="opacity-50" />
                        {user.created_at ? format(new Date(user.created_at), "MMM dd, yyyy") : "N/A"}
                      </div>
                    </td>
                    <td className="px-8 py-6 text-right">
                       <div className="flex items-center justify-end gap-2 px-4 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button 
                            onClick={() => handleOpenEdit(user)}
                            className="p-2 bg-white/5 hover:bg-violet-600/20 text-white/40 hover:text-violet-400 rounded-xl transition-all border border-transparent hover:border-violet-500/30"
                            title="Edit User"
                          >
                            <Edit2 size={16} />
                          </button>
                          <button 
                            onClick={() => handleOpenDelete(user)}
                            className="p-2 bg-white/5 hover:bg-rose-600/20 text-white/40 hover:text-rose-400 rounded-xl transition-all border border-transparent hover:border-rose-500/30"
                            title="Delete User"
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
      </div>

      {/* User Modal (Create/Edit) */}
      {showModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-[#020617]/80 backdrop-blur-md" onClick={() => setShowModal(false)}></div>
          
          <div className="relative w-full max-w-lg bg-slate-900 border border-white/10 rounded-[2.5rem] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
            {/* Modal Header */}
            <div className="px-8 py-6 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
               <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400">
                     {modalMode === "create" ? <UserPlus size={20} /> : <Edit2 size={20} />}
                  </div>
                  <div>
                     <h3 className="text-xl font-black text-white">{modalMode === "create" ? "Add New User" : "Edit User Profile"}</h3>
                     <p className="text-[10px] text-white/40 font-bold uppercase tracking-widest">{modalMode === "create" ? "Khởi tạo tài khoản mới" : "Cập nhật định danh hệ thống"}</p>
                  </div>
               </div>
               <button onClick={() => setShowModal(false)} className="p-2 hover:bg-white/5 rounded-xl text-white/40 transition-all">
                  <X size={20} />
               </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleSubmit} className="p-8 space-y-6">
               <div className="space-y-4">
                  <div className="space-y-2">
                     <label className="text-[10px] font-black uppercase tracking-widest text-white/30 px-1">Email Address</label>
                     <div className="relative group">
                        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20 group-focus-within:text-violet-500 transition-colors" size={18} />
                        <input 
                          required
                          type="email"
                          value={currentUser.email || ""}
                          onChange={(e) => setCurrentUser({...currentUser, email: e.target.value})}
                          placeholder="name@example.com"
                          className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500/50 transition-all"
                        />
                     </div>
                  </div>

                  <div className="space-y-2">
                     <label className="text-[10px] font-black uppercase tracking-widest text-white/30 px-1">Full Name</label>
                     <input 
                       type="text"
                       value={currentUser.full_name || ""}
                       onChange={(e) => setCurrentUser({...currentUser, full_name: e.target.value})}
                       placeholder="Nguyễn Văn A"
                       className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 px-5 text-white focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500/50 transition-all"
                     />
                  </div>

                  <div className="space-y-2">
                     <label className="text-[10px] font-black uppercase tracking-widest text-white/30 px-1">
                        {modalMode === "create" ? "Password" : "New Password (Optional)"}
                     </label>
                     <div className="relative group">
                        <Key className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20 group-focus-within:text-violet-500 transition-colors" size={18} />
                        <input 
                          type="password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="••••••••"
                          className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500/50 transition-all"
                        />
                     </div>
                     {modalMode === "edit" && <p className="text-[10px] text-white/30 italic px-1 pt-1">Bỏ trống nếu không muốn thay đổi mật khẩu.</p>}
                  </div>

                  <div className="pt-4 flex items-center justify-between p-5 bg-white/3 rounded-3xl border border-white/5">
                     <div>
                        <div className="text-sm font-bold text-white">Administrator Privileges</div>
                        <div className="text-[10px] text-white/40 font-medium">Cấp quyền truy cập Command Center</div>
                     </div>
                     <button
                        type="button"
                        onClick={() => setCurrentUser({...currentUser, is_admin: !currentUser.is_admin})}
                        className={`w-14 h-8 rounded-full transition-all relative ${currentUser.is_admin ? "bg-violet-600 shadow-[0_0_15px_rgba(139,92,246,0.4)]" : "bg-white/10"}`}
                     >
                        <div className={`absolute top-1 w-6 h-6 rounded-full bg-white transition-all ${currentUser.is_admin ? "left-7" : "left-1 shadow-md shadow-black/20"}`}></div>
                     </button>
                  </div>
               </div>

               {/* Modal Footer */}
               <div className="flex items-center gap-3 pt-4">
                  <button 
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="flex-1 px-6 py-4 bg-white/5 hover:bg-white/10 rounded-2xl text-sm font-bold text-white/60 hover:text-white transition-all border border-white/5"
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit"
                    disabled={submitting}
                    className="flex-1 px-6 py-4 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-2xl text-sm font-bold text-white shadow-lg shadow-violet-500/20 transition-all flex items-center justify-center gap-2"
                  >
                    {submitting ? (
                      <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
                    ) : (
                      <>
                        <Save size={18} />
                        {modalMode === "create" ? "Create Account" : "Save Changes"}
                      </>
                    )}
                  </button>
               </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-red-950/20 backdrop-blur-md" onClick={() => setShowDeleteConfirm(false)}></div>
          
          <div className="relative w-full max-w-md bg-slate-900 border border-white/10 rounded-[2.5rem] shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-300">
             <div className="p-8 text-center space-y-6">
                <div className="w-20 h-20 mx-auto rounded-3xl bg-rose-600/20 border border-rose-500/30 flex items-center justify-center text-rose-500 shadow-xl shadow-rose-600/10">
                   <AlertTriangle size={40} />
                </div>
                <div>
                   <h3 className="text-2xl font-black text-white mb-2">Confirm Account Deletion</h3>
                   <p className="text-white/40 text-sm leading-relaxed px-4">
                      Hành động này sẽ xóa vĩnh viễn tài khoản <span className="text-white font-bold">{userToDelete?.email}</span> và toàn bộ dữ liệu liên quan. Bạn có chắc chắn?
                   </p>
                </div>
                
                <div className="flex items-center gap-3">
                   <button 
                    onClick={() => setShowDeleteConfirm(false)}
                    className="flex-1 px-6 py-4 bg-white/5 hover:bg-white/10 rounded-2xl text-sm font-bold text-white/60 hover:text-white transition-all border border-white/5"
                   >
                     Hủy bỏ
                   </button>
                   <button 
                    onClick={handleDelete}
                    disabled={submitting}
                    className="flex-1 px-6 py-4 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 rounded-2xl text-sm font-bold text-white shadow-lg shadow-rose-500/20 transition-all flex items-center justify-center gap-2"
                   >
                     {submitting ? (
                        <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
                     ) : (
                        <>
                          <Trash2 size={18} />
                          Xác nhận xóa
                        </>
                     )}
                   </button>
                </div>
             </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminUsersPage;

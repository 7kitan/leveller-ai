"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Users, 
  FileText, 
  BookOpen, 
  Network, 
  Settings, 
  Menu, 
  X,
  ShieldCheck,
  ChevronRight,
  LogOut
} from "lucide-react";
import AuthGuard from "@/components/auth/AuthGuard";
import { useAuth } from "@/context/AuthContext";

const AdminLayout = ({ children }: { children: React.ReactNode }) => {
  const pathname = usePathname();
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const { logout } = useAuth();

  const navigation = [
    { name: "Dashboard", href: "/admin", icon: LayoutDashboard },
    { name: "Users", href: "/admin/users", icon: Users },
    { name: "CV Repository", href: "/admin/cvs", icon: FileText },
    { name: "Taxonomy", href: "/admin/taxonomy", icon: BookOpen },
    { name: "Graph Relations", href: "/admin/relations", icon: Network },
  ];

  return (
    <AuthGuard requireRole="admin">
      <div className="min-h-screen bg-[#020617] text-slate-200 selection:bg-violet-500/30">
        {/* Sidebar */}
        <aside 
          className={`fixed top-0 left-0 z-50 h-screen transition-all duration-500 ease-in-out border-r border-white/5 bg-black/20 backdrop-blur-3xl 
          ${isSidebarOpen ? "w-72" : "w-20"}`}
        >
          <div className="flex flex-col h-full p-4">
            {/* Header / Logo */}
            <div className="flex items-center justify-between mb-10 px-2 mt-4">
              {isSidebarOpen ? (
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
                    <ShieldCheck className="text-white w-6 h-6" />
                  </div>
                  <div>
                    <h1 className="text-lg font-black text-white tracking-widest uppercase">Admin</h1>
                    <p className="text-[9px] text-violet-400 font-bold uppercase tracking-[0.2em]">Core Controller</p>
                  </div>
                </div>
              ) : (
                <div className="w-10 h-10 mx-auto rounded-xl bg-violet-600 flex items-center justify-center">
                  <ShieldCheck className="text-white w-6 h-6" />
                </div>
              )}
              <button 
                onClick={() => setSidebarOpen(!isSidebarOpen)}
                className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/40 hover:text-white transition-all xl:flex hidden"
              >
                {isSidebarOpen ? <X size={18} /> : <Menu size={18} />}
              </button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-2">
              {navigation.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`flex items-center gap-4 px-4 py-4 rounded-2xl transition-all group relative overflow-hidden
                    ${isActive 
                      ? "bg-violet-500/10 text-white border border-violet-500/20" 
                      : "text-slate-400 hover:text-white hover:bg-white/5 border border-transparent"}`}
                  >
                    {isActive && (
                      <div className="absolute left-0 top-0 w-1 h-full bg-violet-500 shadow-[0_0_15px_rgba(139,92,246,0.5)]"></div>
                    )}
                    <item.icon className={`transition-transform duration-500 ${isActive ? "scale-110 text-violet-400" : "group-hover:scale-110"}`} size={20} />
                    {isSidebarOpen && (
                      <span className="text-sm font-bold tracking-tight">{item.name}</span>
                    )}
                    {isSidebarOpen && isActive && (
                      <ChevronRight className="ml-auto w-4 h-4 opacity-50" />
                    )}
                    {!isSidebarOpen && (
                        <div className="absolute left-full ml-6 px-3 py-2 bg-slate-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-all whitespace-nowrap border border-white/10 shadow-2xl z-[100]">
                            {item.name}
                        </div>
                    )}
                  </Link>
                );
              })}
            </nav>

            {/* Logout Button */}
            <div className="mt-auto border-t border-white/5 pt-6 pb-2">
              <button 
                onClick={logout} 
                className="w-full flex items-center gap-4 px-4 py-3 rounded-2xl hover:bg-rose-500/10 transition-all text-slate-400 hover:text-rose-400 group"
              >
                <LogOut size={20} className="group-hover:translate-x-1 transition-transform" />
                {isSidebarOpen && <span className="text-sm font-bold">Đăng xuất</span>}
              </button>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className={`transition-all duration-500 ease-in-out min-h-screen p-8 lg:p-12 ${isSidebarOpen ? "ml-72" : "ml-20"}`}>
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>

        {/* Dynamic Background */}
        <div className="fixed top-0 left-0 w-full h-full pointer-events-none z-0 overflow-hidden">
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-violet-600/5 blur-[120px] rounded-full animate-pulse"></div>
          <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-indigo-600/5 blur-[120px] rounded-full"></div>
        </div>
      </div>
    </AuthGuard>
  );
};

export default AdminLayout;

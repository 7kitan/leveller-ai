"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { 
  LayoutDashboard, 
  BookOpen, 
  Briefcase, 
  GraduationCap, 
  Settings, 
  LogOut, 
  Search, 
  FileText, 
  TrendingUp, 
  ShieldCheck,
  Zap,
  LineChart,
  UserCircle,
  Network
} from "lucide-react";

const Sidebar = () => {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const menuItems = {
    admin: [
      { name: "Dashboard", icon: LayoutDashboard, path: "/admin" },
      { name: "Users", icon: UserCircle, path: "/admin/users" },
      { name: "CV Repository", icon: FileText, path: "/admin/cvs" },
      { name: "Technical Dictionary", icon: BookOpen, path: "/admin/taxonomy" },
      { name: "Graph Relations", icon: Network, path: "/admin/relations" },
      { name: "System Settings", icon: Settings, path: "/admin/settings" },
    ],
    user: [
      { name: "Dashboard", icon: LayoutDashboard, path: "/user" },
      { name: "Job Market", icon: Search, path: "/user/jobs" },
      { name: "My CVs", icon: FileText, path: "/user/cv" },
      { name: "Gap Analysis", icon: LineChart, path: "/user/analysis" },
      { name: "Recommended", icon: Zap, path: "/user/recommend" },
    ],
    student: [
      { name: "Learning Path", icon: TrendingUp, path: "/student" },
      { name: "Skill Explorer", icon: GraduationCap, path: "/student/skills" },
      { name: "Courses", icon: BookOpen, path: "/student/courses" },
      { name: "Student Profile", icon: UserCircle, path: "/student/profile" },
    ]
  };

  const currentRoleItems = (user && user.role) ? (menuItems[user.role] || []) : [];

  return (
    <aside className="fixed left-0 top-0 h-full w-[280px] bg-white/3 backdrop-blur-[24px] border-r border-white/10 z-50 flex flex-col p-6">
      {/* Brand Section */}
      <div className="flex items-center gap-3 mb-10 px-2 group">
        <div className="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center shadow-[0_0_20px_rgba(139,92,246,0.5)] transform transition-transform group-hover:rotate-12">
          <ShieldCheck className="text-white w-6 h-6" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tighter text-white">LUMIX AI</h1>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-black">Career Nexus</p>
        </div>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 space-y-2">
        <div className="px-3 mb-4 text-[10px] text-white/30 font-black uppercase tracking-widest">Navigation</div>
        {currentRoleItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link 
              key={item.name} 
              href={item.path}
              className={`flex items-center gap-4 px-4 py-3.5 rounded-xl transition-all duration-300 group ${
                isActive 
                  ? "bg-violet-600/20 text-violet-400 border border-violet-500/20 shadow-[0_0_15px_rgba(139,92,246,0.15)]" 
                  : "text-white/50 hover:text-white hover:bg-white/5"
              }`}
            >
              <item.icon className={`w-5 h-5 transition-transform group-hover:scale-110 ${isActive ? "text-violet-400" : ""}`} />
              <span className="text-sm font-semibold tracking-tight">{item.name}</span>
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-violet-400 shadow-[0_0_8px_rgba(139,92,246,0.8)]"></div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User Session Info & Logout */}
      <div className="mt-auto border-t border-white/5 pt-6 space-y-4">
        <div className="flex items-center gap-4 px-4">
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-violet-600 to-cyan-500 p-0.5 shadow-lg shadow-violet-900/40">
            <div className="w-full h-full rounded-full bg-[#030508] flex items-center justify-center text-xs font-bold text-white uppercase overflow-hidden">
               {user?.email[0]}
            </div>
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold text-white truncate">{user?.email}</p>
            <p className="text-[10px] text-white/30 uppercase tracking-widest font-black truncate">{user?.role}</p>
          </div>
        </div>
        
        <button 
          onClick={logout}
          className="w-full flex items-center gap-4 px-4 py-4 rounded-xl text-white/40 hover:text-rose-400 hover:bg-rose-500/5 transition-all group"
        >
          <LogOut className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          <span className="text-sm font-bold">Logout</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;

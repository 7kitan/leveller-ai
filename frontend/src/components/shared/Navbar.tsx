"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { 
  LogOut, 
  User as UserIcon, 
  Bell, 
  Search,
  Zap,
  LayoutDashboard
} from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();

  if (!user) return null;

  // Derive base dashboard based on role
  const dashboardPath = user.role === 'admin' ? '/admin' : 
                         user.role === 'student' ? '/student' : '/user';

  return (
    <nav className="glass-panel sticky top-4 z-[100] mx-6 mt-4 border-white/5 px-6 py-3 bg-white/2 backdrop-blur-[24px]">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <div className="flex items-center space-x-8">
          <Link href={dashboardPath} className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-violet-600/20 flex items-center justify-center text-violet-400 border border-violet-500/20 group-hover:shadow-[0_0_15px_rgba(139,92,246,0.3)] transition-all">
                <Zap className="w-5 h-5" />
            </div>
            <span className="text-xl font-bold tracking-tighter text-white">LUMIX<span className="text-violet-500">AI</span></span>
          </Link>
          
          <div className="hidden lg:flex items-center space-x-6">
            <div className="h-4 w-[1px] bg-white/10"></div>
            <div className="flex items-center bg-white/5 border border-white/5 rounded-full px-4 py-1.5 focus-within:border-violet-500/40 transition-all group">
                <Search className="w-4 h-4 text-white/20 group-focus-within:text-violet-400 mr-2" />
                <input 
                    type="text" 
                    placeholder="Quick search..." 
                    className="bg-transparent border-none outline-none text-xs text-white/60 placeholder:text-white/20 w-48 font-medium" 
                />
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-6">
          <button className="relative w-10 h-10 flex items-center justify-center text-white/40 hover:text-white transition-colors group">
             <Bell className="w-5 h-5 group-hover:scale-110 transition-transform" />
             <span className="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full border-2 border-[#030508]"></span>
          </button>
          
          <div className="h-8 w-[1px] bg-white/10"></div>

          <div className="flex items-center space-x-4">
            <div className="flex flex-col items-end">
                <span className="text-xs font-black text-white/80 leading-none">{user.email.split('@')[0]}</span>
                <span className="text-[10px] font-black uppercase tracking-widest text-[#60efff]">{user.role}</span>
            </div>
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-violet-600 to-cyan-500 p-[1px]">
                <div className="w-full h-full rounded-full bg-[#030508] flex items-center justify-center text-white">
                    <UserIcon className="h-4 w-4" />
                </div>
            </div>
            <button 
                onClick={logout}
                className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-white/40 hover:bg-rose-500/20 hover:text-rose-500 transition-all border border-white/5 hover:border-rose-500/20"
            >
                <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

"use client";

import React from "react";
import { Sparkles, Zap, ArrowLeft, Construction } from "lucide-react";
import Link from "next/link";

export default function UserRecommendPage() {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center space-y-8 animate-in fade-in zoom-in duration-700">
      <div className="relative">
        <div className="absolute inset-0 bg-cyan-500/20 blur-[100px] rounded-full scale-150 animate-pulse"></div>
        <div className="w-24 h-24 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center relative z-10">
          <Zap className="w-12 h-12 text-cyan-400 animate-bounce" />
        </div>
      </div>
      
      <div className="space-y-4 max-w-md relative z-10">
        <h1 className="text-4xl font-black text-white tracking-tighter uppercase">Smart Recommendations.</h1>
        <p className="text-white/40 font-medium leading-relaxed">
          Hệ thống đang tinh lọc các cơ hội nghề nghiệp và lộ trình học tập tối ưu nhất dựa trên Knowledge Graph của bạn.
        </p>
      </div>

      <div className="flex items-center gap-6 relative z-10">
        <Link 
            href="/user" 
            className="flex items-center gap-2 px-8 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-white rounded-xl font-bold transition-all"
        >
          <ArrowLeft className="w-4 h-4" /> Quay lại Dashboard
        </Link>
        <div className="flex items-center gap-2 px-4 py-2 bg-cyan-500/10 border border-cyan-500/20 rounded-full">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span className="text-[10px] font-black uppercase tracking-widest text-cyan-400">Coming Soon</span>
        </div>
      </div>
    </div>
  );
}

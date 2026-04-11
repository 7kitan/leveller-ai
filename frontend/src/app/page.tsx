"use client";

import React from "react";
import Link from "next/link";
import { 
  Zap, 
  ShieldCheck, 
  Target, 
  ArrowRight, 
  Flame, 
  Sparkles,
  Command
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center relative px-6 py-20 overflow-hidden bg-[#030508]">
      {/* Background Neon Elements */}
      <div className="absolute top-[-10%] left-[-20%] w-[60%] h-[60%] bg-violet-600/20 blur-[180px] rounded-full animate-pulse-glow"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-cyan-500/10 blur-[150px] rounded-full animate-pulse-glow [animation-delay:2s]"></div>
      
      {/* Floating AI Sphere (CSS Animation) */}
      <div className="relative mb-16 animate-float">
        <div className="w-32 h-32 rounded-full bg-gradient-to-tr from-violet-600 to-cyan-400 blur-2xl opacity-20 absolute inset-0 scale-150"></div>
        <div className="w-32 h-32 rounded-full bg-gradient-to-tr from-violet-500 to-cyan-500 shadow-[0_0_60px_rgba(139,92,246,0.5)] flex items-center justify-center relative z-10 border border-white/20">
          <Command className="text-white w-14 h-14 animate-spin [animation-duration:10s]" />
        </div>
      </div>

      {/* Hero Content */}
      <div className="max-w-4xl text-center space-y-8 relative z-10">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-xs font-black uppercase tracking-widest text-violet-400 animate-in fade-in slide-in-from-top-4 duration-1000">
          <Sparkles className="w-3 h-3" /> Career Evolution V6.0
        </div>
        
        <h1 className="text-6xl md:text-8xl font-black tracking-tighter leading-none animate-in fade-in slide-in-from-bottom-8 duration-700">
          <span className="block text-white">RECODE YOUR</span>
          <span className="block bg-gradient-to-r from-violet-400 via-orchid-400 to-cyan-400 bg-clip-text text-transparent italic">FUTURE PATH.</span>
        </h1>

        <p className="text-xl md:text-2xl text-white/50 font-medium max-w-2xl mx-auto leading-relaxed animate-in fade-in duration-1000 delay-300">
          Trải nghiệm trí tuệ nhân tạo hội tụ trong quản trị tri thức kỹ thuật. 
          Định vị bản thân, khỏa lấp khoảng trống, và dẫn đầu thị trường.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-8 animate-in fade-in zoom-in duration-700 delay-500">
          <Link 
            href="/auth/register"
            className="group relative px-10 py-5 bg-violet-600 hover:bg-violet-500 text-white rounded-2xl font-black text-lg transition-all shadow-[0_20px_40px_rgba(139,92,246,0.3)] hover:shadow-[0_25px_50px_rgba(139,92,246,0.5)] flex items-center gap-3 overflow-hidden"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
            Giải mã ngay <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link 
            href="/auth/login"
            className="px-10 py-5 bg-white/5 hover:bg-white/10 border border-white/10 text-white rounded-2xl font-bold text-lg transition-all backdrop-blur-xl"
          >
            Đăng nhập
          </Link>
        </div>
      </div>

      {/* Role Previews */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-32 max-w-6xl w-full animate-in fade-in slide-in-from-bottom-12 duration-1000 delay-700">
        {[
          { title: "Professionals", desc: "Quản trị từ điển tri thức chuyên sâu và kiến trúc Graph.", icon: ShieldCheck, color: "text-violet-400" },
          { title: "Applicants", desc: "Phân tích Gap kỹ năng và săn tìm cơ hội vàng.", icon: Target, color: "text-cyan-400" },
          { title: "Students", desc: "Học tập cá nhân hóa và định hướng sự nghiệp vươn tầm.", icon: GraduationCap, color: "text-amber-400" }
        ].map((role) => (
          <div key={role.title} className="glass-panel p-10 group hover:scale-[1.02] transition-all">
            <role.icon className={`w-12 h-12 ${role.color} mb-6 transform transition-transform group-hover:rotate-12`} />
            <h3 className="text-2xl font-bold text-white mb-4">{role.title}</h3>
            <p className="text-white/40 leading-relaxed font-medium">{role.desc}</p>
          </div>
        ))}
      </div>

      <style jsx>{`
        @keyframes pulse-glow {
          0%, 100% { opacity: 0.1; transform: scale(1); }
          50% { opacity: 0.3; transform: scale(1.1); }
        }
        .animate-pulse-glow {
          animation: pulse-glow 8s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}

const GraduationCap = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"/>
  </svg>
);

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

import styles from "./landing.module.css";

export default function LandingPage() {
  return (
    <div className={styles.pageRoot}>
      {/* Background Neon Elements */}
      <div className={styles.backgroundNeon1}></div>
      <div className={styles.backgroundNeon2}></div>
      
      {/* Floating AI Sphere (CSS Animation) */}
      <div className={styles.floatingSphere}>
        <div className={styles.sphereGlow}></div>
        <div className={styles.sphereCore}>
          <Command className={styles.sphereIcon} />
        </div>
      </div>

      {/* Hero Content */}
      <div className={styles.heroContent}>
        <div className={styles.heroBadge}>
          <Sparkles className="w-3 h-3" /> Career Evolution V6.0
        </div>
        
        <h1 className={styles.heroTitle}>
          <span className="block text-white">RECODE YOUR</span>
          <span className={styles.heroTitleGradient}>FUTURE PATH.</span>
        </h1>

        <p className={styles.heroDescription}>
          Trải nghiệm trí tuệ nhân tạo hội tụ trong quản trị tri thức kỹ thuật. 
          Định vị bản thân, khỏa lấp khoảng trống, và dẫn đầu thị trường.
        </p>

        <div className={styles.heroActions}>
          <Link 
            href="/auth/register"
            className={styles.primaryBtn}
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
            Giải mã ngay <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link 
            href="/auth/login"
            className={styles.secondaryBtn}
          >
            Đăng nhập
          </Link>
        </div>
      </div>

      {/* Role Previews */}
      <div className={styles.roleGrid}>
        {[
          { title: "Professionals", desc: "Quản trị từ điển tri thức chuyên sâu và kiến trúc Graph.", icon: ShieldCheck, color: "text-violet-400" },
          { title: "Applicants", desc: "Phân tích Gap kỹ năng và săn tìm cơ hội vàng.", icon: Target, color: "text-cyan-400" },
          { title: "Students", desc: "Học tập cá nhân hóa và định hướng sự nghiệp vươn tầm.", icon: GraduationCap, color: "text-amber-400" }
        ].map((role) => (
          <div key={role.title} className={styles.roleCard}>
            <role.icon className={`w-12 h-12 ${role.color} mb-6 transform transition-transform group-hover:rotate-12`} />
            <h3 className="text-2xl font-bold text-white mb-4">{role.title}</h3>
            <p className="text-white/40 leading-relaxed font-medium">{role.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

const GraduationCap = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"/>
  </svg>
);

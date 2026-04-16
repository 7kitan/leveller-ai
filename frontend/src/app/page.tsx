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
      {/* Premium Background Accents */}
      <div className={styles.backgroundAccent1}></div>
      <div className={styles.backgroundAccent2}></div>
      
      {/* Hero Content */}
      <div className={styles.heroContent}>
        <div className={styles.heroBadge}>
          <Sparkles className={styles.badgeIcon} /> 
          <span>Career Evolution V6.0</span>
        </div>
        
        <h1 className={styles.heroTitle}>
          <span className={styles.heroTitleSub}>RECODE YOUR</span>
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
            <span>Giải mã ngay</span>
            <ArrowRight className={styles.btnIcon} />
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
          { 
            title: "Professionals", 
            desc: "Quản trị từ điển tri thức chuyên sâu và kiến trúc Graph.", 
            icon: ShieldCheck, 
            iconClass: styles.iconProfessionals 
          },
          { 
            title: "Applicants", 
            desc: "Phân tích Gap kỹ năng và săn tìm cơ hội vàng.", 
            icon: Target, 
            iconClass: styles.iconApplicants 
          },
          { 
            title: "Students", 
            desc: "Học tập cá nhân hóa và định hướng sự nghiệp vươn tầm.", 
            icon: GraduationCap, 
            iconClass: styles.iconStudents 
          }
        ].map((role) => (
          <div key={role.title} className={styles.roleCard}>
            <div className={`${styles.roleIconWrapper} ${role.iconClass}`}>
              <role.icon className={styles.roleIcon} />
            </div>
            <h3 className={styles.roleCardTitle}>{role.title}</h3>
            <p className={styles.roleCardDesc}>{role.desc}</p>
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

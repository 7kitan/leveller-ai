"use client";

import React from "react";
import Link from "next/link";
import { 
  Target, 
  Cpu,
  GraduationCap,
  ChevronRight,
  Menu,
  X
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import styles from "./landing.module.css";

/* ========================================
 * ANIMATION CONFIGURATIONS
 * Extracted for easier tweaking and editing
 * ======================================== */

const NAV_ANIMATION = {
  duration: 0.4,
  ease: [0.32, 0.72, 0, 1] as [number, number, number, number]
};

const MOBILE_MENU_OPEN = {
  height: "auto" as const,
  opacity: 1, 
  transition: { 
    height: { duration: 0.5 },
    staggerChildren: 0.08,
    delayChildren: 0.1
  } 
};

const MOBILE_MENU_CLOSED = { 
  height: 0,
  opacity: 0,
  transition: { 
    height: { duration: 0.4, ease: [0.32, 0.72, 0, 1] },
    opacity: { duration: 0.3 },
    staggerChildren: 0.03,
    staggerDirection: -1
  }
};

const ICON_ANIMATION = {
  duration: 0.4,
  ease: [0.16, 1, 0.3, 1] as [number, number, number, number]
};

/* ========================================
 * HELPER FUNCTIONS
 * ======================================== */

function getNavBackground(isOpen: boolean) {
  return isOpen ? "rgba(255, 255, 255, 1)" : "rgba(255, 255, 255, 0.8)";
}

function getNavBorderRadius(isOpen: boolean) {
  return isOpen ? "28px" : "980px";
}

function getNavPadding(isOpen: boolean) {
  return isOpen ? "20px" : "0px";
}

function getNavShadow(isOpen: boolean) {
  return isOpen ? "0 20px 40px rgba(0, 0, 0, 0.1)" : "0 8px 32px rgba(0, 0, 0, 0.08)";
}

/* ========================================
 * NAVIGATION COMPONENT
 * Broken out for clarity
 * ======================================== */

function GlassNavbar({ 
  isOpen, 
  onToggle,
  navRef 
}: { 
  isOpen: boolean; 
  onToggle: () => void;
  navRef: React.RefObject<HTMLElement>;
}) {
  const navAnimation = {
    backgroundColor: getNavBackground(isOpen),
    borderRadius: getNavBorderRadius(isOpen),
    paddingBottom: getNavPadding(isOpen),
    boxShadow: getNavShadow(isOpen)
  };

  return (
    <motion.nav 
      ref={navRef}
      className={styles.navWrapper}
      layout
      initial={false}
      animate={navAnimation}
      transition={{ duration: NAV_ANIMATION.duration, ease: NAV_ANIMATION.ease }}
    >
      <div className={styles.nav}>
        <Link href="/" className={styles.navLogo}>LUMIX AI</Link>
        
        {/* Desktop Links */}
        <div className={styles.navLinks}>
          <Link href="#features">Tính năng</Link>
          <Link href="#philosophy">Tầm nhìn</Link>
          <Link href="/auth/login" className={styles.navCta}>Hội viên</Link>
        </div>

        {/* Mobile Toggle */}
        <div className={styles.navRight}>
          <button 
            className={styles.mobileToggle} 
            onClick={onToggle}
            aria-label="Toggle menu"
          >
            <motion.div
              animate={{ rotate: isOpen ? 90 : 0 }}
              transition={{ duration: ICON_ANIMATION.duration, ease: ICON_ANIMATION.ease }}
              style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
            >
              <AnimatePresence mode="wait">
                <motion.div
                  key={isOpen ? "close" : "menu"}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  transition={{ duration: 0.2 }}
                >
                  {isOpen ? <X size={24} /> : <Menu size={24} />}
                </motion.div>
              </AnimatePresence>
            </motion.div>
          </button>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div 
            className={styles.mobileMenu}
            initial="closed"
            animate="open"
            exit="closed"
            variants={{
              open: MOBILE_MENU_OPEN,
              closed: MOBILE_MENU_CLOSED
            }}
            style={{ overflow: "hidden" }}
          >
            <div className={styles.mobileLinks}>
              {[
                { href: "#features", label: "Tính năng" },
                { href: "#philosophy", label: "Tầm nhìn" },
                { href: "/auth/login", label: "Hội viên", isCta: true }
              ].map((link) => (
                <motion.div
                  key={link.href}
                  variants={{
                    open: { opacity: 1, y: 0 },
                    closed: { opacity: 0, y: -10 }
                  }}
                  transition={{ duration: 0.3, ease: [0.32, 0.72, 0, 1] }}
                >
                  <Link 
                    href={link.href} 
                    className={link.isCta ? styles.mobileCta : ""} 
                    onClick={() => onToggle()}
                  >
                    {link.label}
                  </Link>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className={styles.mobileBackdrop}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            onClick={() => onToggle()}
          />
        )}
      </AnimatePresence>
    </motion.nav>
  );
}

/* ========================================
 * MAIN PAGE COMPONENT
 * ======================================== */

export default function LandingPage() {
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);
  const navRef = React.useRef<HTMLElement>(null);

  // Close menu when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };
    if (isMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isMenuOpen]);

  // Prevent scroll when mobile menu is open
  React.useEffect(() => {
    if (isMenuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => { document.body.style.overflow = "unset"; };
  }, [isMenuOpen]);

  return (
    <div className={styles.pageRoot}>
      {/* Apple-style Glass Navbar */}
      <motion.nav 
        ref={navRef}
        className={styles.navWrapper}
        layout
        initial={false}
        animate={{
          backgroundColor: isMenuOpen ? "rgba(255, 255, 255, 1)" : "rgba(255, 255, 255, 0.8)",
          borderRadius: isMenuOpen ? "28px" : "980px",
          paddingBottom: isMenuOpen ? "20px" : "0px",
          boxShadow: isMenuOpen 
            ? "0 20px 40px rgba(0, 0, 0, 0.1)" 
            : "0 8px 32px rgba(0, 0, 0, 0.08)"
        }}
        transition={{ duration: 0.4, ease: [0.32, 0.72, 0, 1] }}
      >
        <div className={styles.nav}>
          <Link href="/" className={styles.navLogo}>LUMIX AI</Link>
          
          {/* Desktop Links */}
          <div className={styles.navLinks}>
            <Link href="#features">Tính năng</Link>
            <Link href="#philosophy">Tầm nhìn</Link>
            <Link href="/auth/login" className={styles.navCta}>Hội viên</Link>
          </div>

          {/* Mobile Toggle */}
          <div className={styles.navRight}>
            <button 
              className={styles.mobileToggle} 
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              aria-label="Toggle menu"
            >
              <motion.div
                animate={{ rotate: isMenuOpen ? 90 : 0 }}
                transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
              >
                <AnimatePresence mode="wait">
                  <motion.div
                    key={isMenuOpen ? "close" : "menu"}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    transition={{ duration: 0.2 }}
                  >
                    {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
                  </motion.div>
                </AnimatePresence>
              </motion.div>
            </button>
          </div>
        </div>

        {/* Mobile Menu Overlay */}
        <AnimatePresence>
          {isMenuOpen && (
            <motion.div 
              className={styles.mobileMenu}
              initial="closed"
              animate="open"
              exit="closed"
              variants={{
                open: { 
                  height: "auto",
                  opacity: 1, 
                  transition: { 
                    height: { duration: 0.5 },
                    staggerChildren: 0.08,
                    delayChildren: 0.1
                  } 
                },
                closed: { 
                  height: 0,
                  opacity: 0,
                  transition: { 
                    height: { duration: 0.4, ease: [0.32, 0.72, 0, 1] },
                    opacity: { duration: 0.3 },
                    staggerChildren: 0.03,
                    staggerDirection: -1
                  }
                }
              }}
              style={{ overflow: "hidden" }}
            >
              <div className={styles.mobileLinks}>
                {[
                  { href: "#features", label: "Tính năng" },
                  { href: "#philosophy", label: "Tầm nhìn" },
                  { href: "/auth/login", label: "Hội viên", isCta: true }
                ].map((link) => (
                  <motion.div
                    key={link.href}
                    variants={{
                      open: { opacity: 1, y: 0 },
                      closed: { opacity: 0, y: -10 }
                    }}
                    transition={{ duration: 0.3, ease: [0.32, 0.72, 0, 1] }}
                  >
                    <Link 
                      href={link.href} 
                      className={link.isCta ? styles.mobileCta : ""} 
                      onClick={() => setIsMenuOpen(false)}
                    >
                      {link.label}
                    </Link>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        {/* Backdrop */}
        <AnimatePresence>
          {isMenuOpen && (
            <motion.div
              className={styles.mobileBackdrop}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
              onClick={() => setIsMenuOpen(false)}
            />
          )}
        </AnimatePresence>
      </motion.nav>

      {/* Hero Section - Dark Immersive */}
      <div className={`${styles.sectionWrapper} ${styles.bgDark}`}>
        <section className={styles.heroSection}>
          <motion.div 
            className={styles.heroContent}
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
          >
            <h1 className={styles.heroTitle}>
              Recode your<br />future path
            </h1>
            <p className={styles.heroDescription}>
              Experience the next generation of AI-driven career intelligence and technical knowledge graph management.
            </p>
            <div className={styles.heroActions}>
              <Link href="/auth/register" className={styles.primaryBtn}>
                Learn more
              </Link>
              <Link href="/auth/login" className={styles.secondaryBtn}>
                Get started <ChevronRight size={18} />
              </Link>
            </div>
          </motion.div>
        </section>
      </div>

      {/* Philosophy Section - Light Informational */}
      <div className={`${styles.sectionWrapper} ${styles.bgLight}`}>
        <section id="philosophy" className={styles.section}>
          <motion.div
            className={styles.centeredText}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 1.5 }}
          >
            <h2 className={styles.sectionHeading}>
              Tầm nhìn & Sứ mệnh
            </h2>
            <p className={styles.sectionSubheading}>
              Chúng tôi tin rằng tương lai được xây dựng từ những kết nối thông minh. 
              Lumix AI không chỉ là công cụ, mà là một hệ sinh thái tri thức giúp bạn xóa bỏ mọi giới hạn.
            </p>
          </motion.div>
        </section>
      </div>

      {/* Feature Bento Grid - Dark Immersive */}
      <div className={`${styles.sectionWrapper} ${styles.bgDark}`}>
        <section id="features" className={styles.section}>
          <div className={styles.centeredText}>
            <h2 className={styles.sectionHeading}>The future of knowledge</h2>
          </div>
          
          <div className={styles.bentoContainer}>
            {/* Professionals Card - Large */}
            <motion.div 
              className={`${styles.bentoItem} ${styles.bentoLarge}`}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8 }}
            >
              <div>
                <Cpu className={styles.bentoIcon} />
                <h3 className={styles.bentoTitle}>Professionals</h3>
                <p className={styles.bentoDesc}>
                  Xây dựng và quản trị từ điển tri thức chuyên môn phức tạp thông qua kiến trúc Knowledge Graph tiên tiến. 
                  Tự động hóa phân tích kỹ năng và chuẩn hóa quy trình chuyên gia.
                </p>
              </div>
              <Link href="/auth/login" className={styles.secondaryBtn}>
                Learn more <ChevronRight size={16} />
              </Link>
            </motion.div>

            {/* Applicants Card */}
            <motion.div 
              className={styles.bentoItem}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8, delay: 0.1 }}
            >
              <div>
                <Target className={styles.bentoIcon} />
                <h3 className={styles.bentoTitle}>Applicants</h3>
                <p className={styles.bentoDesc}>
                  Giải mã khoảng trống kỹ năng (Skill Gap) và tối ưu hóa hồ sơ năng lực 
                  để dẫn đầu trong mọi cuộc săn tìm cơ hội.
                </p>
              </div>
              <Link href="/auth/login" className={styles.secondaryBtn}>
                Learn more <ChevronRight size={16} />
              </Link>
            </motion.div>

            {/* Students Card */}
            <motion.div 
              className={styles.bentoItem}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <div>
                <GraduationCap className={styles.bentoIcon} />
                <h3 className={styles.bentoTitle}>Students</h3>
                <p className={styles.bentoDesc}>
                  Lộ trình học tập cá nhân hóa được tinh chỉnh bởi AI, 
                  giúp bạn rút ngắn khoảng cách từ giảng đường đến thực tế doanh nghiệp.
                </p>
              </div>
              <Link href="/auth/login" className={styles.secondaryBtn}>
                Learn more <ChevronRight size={16} />
              </Link>
            </motion.div>
          </div>
        </section>
      </div>

      {/* Simple Footer */}
      <div className={`${styles.sectionWrapper} ${styles.bgDark}`}>
        <footer className={styles.section} style={{ padding: "60px 20px", textAlign: "center", borderTop: "1px solid rgba(255,255,255,0.1)" }}>
          <p style={{ opacity: 0.4, fontSize: "12px" }}>© 2026 Lumix AI. V6.0 Premium Experience.</p>
        </footer>
      </div>
    </div>
  );
}



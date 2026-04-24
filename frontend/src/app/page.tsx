"use client";

import React from "react";
import Link from "next/link";
import { 
  Target, 
  Cpu,
  GraduationCap,
  ChevronRight,
  Menu,
  X,
  Upload,
  Sparkles,
  TrendingUp,
  ArrowRight,
  Star,
  Mail
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
            <Link href="#stats">Thống kê / Stats</Link>
            <Link href="#how-it-works">Cách hoạt động / How it works</Link>
            <Link href="#features">Tính năng / Features</Link>
            <Link href="#testimonials">Đánh giá / Reviews</Link>
            <Link href="/auth/login" className={styles.navCta}>Đăng nhập / Login</Link>
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
                  { href: "#stats", label: "Thống kê / Stats" },
                  { href: "#how-it-works", label: "Cách hoạt động / How it works" },
                  { href: "#features", label: "Tính năng / Features" },
                  { href: "#testimonials", label: "Đánh giá / Reviews" },
                  { href: "/auth/login", label: "Đăng nhập / Login", isCta: true }
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

      {/* Hero Section - Dark Immersive with Animated Gradient */}
      <div className={`${styles.sectionWrapper} ${styles.bgDark}`}>
        <section className={styles.heroSection}>
          {/* Background Image with Blur */}
          <div className={styles.heroBackground} />
          
          {/* Animated Gradient Overlay */}
          <div className={styles.heroGradient} />
          
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
                Bắt đầu ngay / Get started
              </Link>
              <Link href="#how-it-works" className={styles.secondaryBtn}>
                Tìm hiểu thêm / Learn more <ChevronRight size={18} />
              </Link>
            </div>
          </motion.div>
        </section>
      </div>

      {/* Statistics Section - Social Proof */}
      <div id="stats" className={`${styles.sectionWrapper} ${styles.bgLight}`}>
        <section className={styles.statsSection}>
          <motion.div 
            className={styles.statsGrid}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, staggerChildren: 0.1 }}
          >
            {[
              { value: "10,000+", label: "CVs Analyzed" },
              { value: "95%", label: "Match Accuracy" },
              { value: "500+", label: "Companies" },
              { value: "24/7", label: "AI Support" }
            ].map((stat, idx) => (
              <motion.div 
                key={idx}
                className={styles.statItem}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
              >
                <h3 className={styles.statValue}>{stat.value}</h3>
                <p className={styles.statLabel}>{stat.label}</p>
              </motion.div>
            ))}
          </motion.div>
        </section>
      </div>

      {/* Philosophy Section - Light Informational */}
      <div id="philosophy" className={`${styles.sectionWrapper} ${styles.bgLight}`}>
        <section className={styles.section}>
          <motion.div
            className={styles.visionSection}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 1.5 }}
          >
            <div className={styles.visionContent}>
              <motion.div
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8 }}
              >
                <h2 className={styles.visionHeading}>
                  Tầm nhìn & Sứ mệnh
                </h2>
                <div className={styles.visionDivider} />
                <p className={styles.visionText}>
                  Chúng tôi tin rằng tương lai được xây dựng từ những kết nối thông minh. 
                  Lumix AI không chỉ là công cụ, mà là một hệ sinh thái tri thức giúp bạn xóa bỏ mọi giới hạn.
                </p>
                <p className={styles.visionSubtext}>
                  Với công nghệ AI tiên tiến và Knowledge Graph, chúng tôi tạo ra cầu nối giữa 
                  kỹ năng hiện tại và cơ hội tương lai của bạn.
                </p>
              </motion.div>
              
              <motion.div 
                className={styles.visionStats}
                initial={{ opacity: 0, x: 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: 0.2 }}
              >
                <div className={styles.visionStatItem}>
                  <div className={styles.visionStatIcon}>🎯</div>
                  <h4>Chính xác</h4>
                  <p>AI phân tích sâu để đưa ra đánh giá chính xác nhất</p>
                </div>
                <div className={styles.visionStatItem}>
                  <div className={styles.visionStatIcon}>⚡</div>
                  <h4>Nhanh chóng</h4>
                  <p>Kết quả trong vài phút, không phải vài ngày</p>
                </div>
                <div className={styles.visionStatItem}>
                  <div className={styles.visionStatIcon}>🚀</div>
                  <h4>Hiệu quả</h4>
                  <p>Lộ trình cá nhân hóa giúp bạn tiến nhanh hơn</p>
                </div>
              </motion.div>
            </div>
          </motion.div>
        </section>
      </div>

      {/* How It Works Section - Dark with Visual Flow */}
      <div id="how-it-works" className={`${styles.sectionWrapper} ${styles.bgDark}`}>
        <section className={styles.section}>
          <div className={styles.centeredText}>
            <h2 className={styles.sectionHeading}>How it works</h2>
            <p className={styles.sectionSubheading}>
              Three simple steps to unlock your career potential
            </p>
          </div>

          <div className={styles.howItWorksGrid}>
            {[
              {
                icon: Upload,
                step: "01",
                title: "Upload CV",
                description: "Upload your resume and let our AI analyze your skills, experience, and career trajectory."
              },
              {
                icon: Sparkles,
                step: "02",
                title: "AI Analysis",
                description: "Advanced algorithms identify skill gaps, match opportunities, and generate personalized recommendations."
              },
              {
                icon: TrendingUp,
                step: "03",
                title: "Get Results",
                description: "Receive actionable insights, course recommendations, and a clear roadmap to your dream job."
              }
            ].map((item, idx) => (
              <React.Fragment key={idx}>
                <motion.div
                  className={styles.howItWorksStep}
                  initial={{ opacity: 0, y: 40 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-100px" }}
                  transition={{ duration: 0.6, delay: idx * 0.2 }}
                >
                  <div className={styles.stepIconWrapper}>
                    <item.icon className={styles.stepIcon} />
                  </div>
                  <div className={styles.stepNumber}>{item.step}</div>
                  <h3 className={styles.stepTitle}>{item.title}</h3>
                  <p className={styles.stepDescription}>{item.description}</p>
                </motion.div>
                
                {idx < 2 && (
                  <motion.div 
                    className={styles.stepArrow}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6, delay: idx * 0.2 + 0.3 }}
                  >
                    <ArrowRight size={24} />
                  </motion.div>
                )}
              </React.Fragment>
            ))}
          </div>
        </section>
      </div>

      {/* Feature Bento Grid - Dark Immersive */}
      <div id="features" className={`${styles.sectionWrapper} ${styles.bgDark}`}>
        <section className={styles.section}>
          <div className={styles.featuresHeader}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <h2 className={styles.sectionHeading}>The future of knowledge</h2>
              <p className={styles.featuresSubheading}>
                Giải pháp toàn diện cho mọi đối tượng / Comprehensive solutions for everyone
              </p>
            </motion.div>
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

      {/* Testimonials Section - Light */}
      <div id="testimonials" className={`${styles.sectionWrapper} ${styles.bgLight}`}>
        <section className={styles.section}>
          <div className={styles.centeredText}>
            <h2 className={styles.sectionHeading}>Trusted by professionals</h2>
            <p className={styles.sectionSubheading}>
              See what our users have to say about their experience
            </p>
          </div>

          <div className={styles.testimonialsGrid}>
            {[
              {
                quote: "Lumix AI helped me identify skill gaps I didn't even know I had. Within 3 months, I landed my dream job at a top tech company.",
                author: "Nguyễn Văn A",
                role: "Software Engineer",
                company: "Tech Corp",
                rating: 5
              },
              {
                quote: "The AI-powered recommendations were spot-on. The personalized learning roadmap saved me months of trial and error.",
                author: "Trần Thị B",
                role: "Data Analyst",
                company: "Analytics Inc",
                rating: 5
              },
              {
                quote: "As a career switcher, Lumix AI gave me the confidence and direction I needed. The skill gap analysis was incredibly detailed.",
                author: "Lê Văn C",
                role: "Product Manager",
                company: "Startup XYZ",
                rating: 5
              }
            ].map((testimonial, idx) => (
              <motion.div
                key={idx}
                className={styles.testimonialCard}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.6, delay: idx * 0.15 }}
              >
                <div className={styles.testimonialRating}>
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} size={16} fill="#667eea" color="#667eea" />
                  ))}
                </div>
                <p className={styles.testimonialQuote}>"{testimonial.quote}"</p>
                <div className={styles.testimonialAuthor}>
                  <div className={styles.authorAvatar}>
                    {testimonial.author.charAt(0)}
                  </div>
                  <div>
                    <div className={styles.authorName}>{testimonial.author}</div>
                    <div className={styles.authorRole}>
                      {testimonial.role} at {testimonial.company}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </section>
      </div>

      {/* Enhanced Footer */}
      <div className={`${styles.sectionWrapper} ${styles.bgDark}`}>
        <footer className={styles.richFooter}>
          <div className={styles.footerContent}>
            <div className={styles.footerGrid}>
              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>Product</h4>
                <Link href="#features">Features</Link>
                <Link href="/auth/login">Pricing</Link>
                <Link href="#philosophy">About</Link>
                <Link href="/auth/register">Get Started</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>Company</h4>
                <Link href="/auth/login">Careers</Link>
                <Link href="/auth/login">Blog</Link>
                <Link href="/auth/login">Press</Link>
                <Link href="/auth/login">Contact</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>Resources</h4>
                <Link href="/auth/login">Documentation</Link>
                <Link href="/auth/login">Help Center</Link>
                <Link href="/auth/login">API</Link>
                <Link href="/auth/login">Community</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>Stay updated</h4>
                <p className={styles.footerNewsletter}>
                  Get the latest news and updates delivered to your inbox.
                </p>
                <div className={styles.newsletterForm}>
                  <input 
                    type="email" 
                    placeholder="Enter your email" 
                    className={styles.newsletterInput}
                  />
                  <button className={styles.newsletterButton}>
                    <Mail size={18} />
                  </button>
                </div>
              </div>
            </div>

            <div className={styles.footerBottom}>
              <p className={styles.footerCopyright}>
                © 2026 Lumix AI. All rights reserved.
              </p>
              <div className={styles.footerLinks}>
                <Link href="/auth/login">Privacy Policy</Link>
                <Link href="/auth/login">Terms of Service</Link>
                <Link href="/auth/login">Cookie Policy</Link>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}



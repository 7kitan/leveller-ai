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
  const [language, setLanguage] = React.useState<'vi' | 'en'>('vi');
  const navRef = React.useRef<HTMLElement>(null);

  // Toggle language
  const toggleLanguage = () => {
    setLanguage(prev => prev === 'vi' ? 'en' : 'vi');
  };

  // Translation object
  const t = {
    vi: {
      nav: {
        stats: "Thống kê",
        howItWorks: "Cách hoạt động",
        features: "Tính năng",
        testimonials: "Đánh giá",
        login: "Đăng nhập"
      },
      hero: {
        title: "Định hình lại\ncon đường tương lai",
        description: "Trải nghiệm thế hệ mới của trí tuệ nghề nghiệp được hỗ trợ bởi AI và quản lý đồ thị tri thức kỹ thuật.",
        getStarted: "Bắt đầu ngay",
        learnMore: "Tìm hiểu thêm"
      },
      stats: {
        cvs: "CV Đã Phân Tích",
        accuracy: "Độ Chính Xác",
        companies: "Công Ty",
        support: "Hỗ Trợ AI"
      },
      vision: {
        heading: "Tầm nhìn & Sứ mệnh",
        text: "Chúng tôi tin rằng tương lai được xây dựng từ những kết nối thông minh. Lumix AI không chỉ là công cụ, mà là một hệ sinh thái tri thức giúp bạn xóa bỏ mọi giới hạn.",
        subtext: "Với công nghệ AI tiên tiến và Knowledge Graph, chúng tôi tạo ra cầu nối giữa kỹ năng hiện tại và cơ hội tương lai của bạn.",
        accurate: "Chính xác",
        accurateDesc: "AI phân tích sâu để đưa ra đánh giá chính xác nhất",
        fast: "Nhanh chóng",
        fastDesc: "Kết quả trong vài phút, không phải vài ngày",
        effective: "Hiệu quả",
        effectiveDesc: "Lộ trình cá nhân hóa giúp bạn tiến nhanh hơn"
      },
      howItWorks: {
        heading: "Cách hoạt động",
        subheading: "Ba bước đơn giản để mở khóa tiềm năng nghề nghiệp của bạn",
        step1: "Tải CV lên",
        step1Desc: "Tải CV của bạn lên và để AI phân tích kỹ năng, kinh nghiệm và quỹ đạo nghề nghiệp.",
        step2: "Phân tích AI",
        step2Desc: "Thuật toán tiên tiến xác định khoảng trống kỹ năng, khớp cơ hội và tạo đề xuất cá nhân hóa.",
        step3: "Nhận kết quả",
        step3Desc: "Nhận thông tin chi tiết có thể hành động, đề xuất khóa học và lộ trình rõ ràng đến công việc mơ ước."
      },
      features: {
        heading: "Tương lai của tri thức",
        subheading: "Giải pháp toàn diện cho mọi đối tượng",
        professionals: "Chuyên gia",
        professionalsDesc: "Xây dựng và quản trị từ điển tri thức chuyên môn phức tạp thông qua kiến trúc Knowledge Graph tiên tiến. Tự động hóa phân tích kỹ năng và chuẩn hóa quy trình chuyên gia.",
        applicants: "Ứng viên",
        applicantsDesc: "Giải mã khoảng trống kỹ năng (Skill Gap) và tối ưu hóa hồ sơ năng lực để dẫn đầu trong mọi cuộc săn tìm cơ hội.",
        students: "Sinh viên",
        studentsDesc: "Lộ trình học tập cá nhân hóa được tinh chỉnh bởi AI, giúp bạn rút ngắn khoảng cách từ giảng đường đến thực tế doanh nghiệp.",
        learnMore: "Tìm hiểu thêm"
      },
      testimonials: {
        heading: "Được tin tưởng bởi các chuyên gia",
        subheading: "Xem những gì người dùng của chúng tôi nói về trải nghiệm của họ"
      },
      footer: {
        product: "Sản phẩm",
        company: "Công ty",
        resources: "Tài nguyên",
        stayUpdated: "Cập nhật tin tức",
        newsletter: "Nhận tin tức và cập nhật mới nhất được gửi đến hộp thư của bạn.",
        emailPlaceholder: "Nhập email của bạn",
        copyright: "© 2026 Lumix AI. Tất cả quyền được bảo lưu.",
        privacy: "Chính sách bảo mật",
        terms: "Điều khoản dịch vụ",
        cookies: "Chính sách Cookie"
      }
    },
    en: {
      nav: {
        stats: "Statistics",
        howItWorks: "How it works",
        features: "Features",
        testimonials: "Reviews",
        login: "Login"
      },
      hero: {
        title: "Recode your\nfuture path",
        description: "Experience the next generation of AI-driven career intelligence and technical knowledge graph management.",
        getStarted: "Get started",
        learnMore: "Learn more"
      },
      stats: {
        cvs: "CVs Analyzed",
        accuracy: "Match Accuracy",
        companies: "Companies",
        support: "AI Support"
      },
      vision: {
        heading: "Vision & Mission",
        text: "We believe the future is built from intelligent connections. Lumix AI is not just a tool, but a knowledge ecosystem that helps you break through all limitations.",
        subtext: "With advanced AI technology and Knowledge Graph, we create a bridge between your current skills and future opportunities.",
        accurate: "Accurate",
        accurateDesc: "Deep AI analysis for the most precise assessment",
        fast: "Fast",
        fastDesc: "Results in minutes, not days",
        effective: "Effective",
        effectiveDesc: "Personalized roadmap helps you progress faster"
      },
      howItWorks: {
        heading: "How it works",
        subheading: "Three simple steps to unlock your career potential",
        step1: "Upload CV",
        step1Desc: "Upload your resume and let our AI analyze your skills, experience, and career trajectory.",
        step2: "AI Analysis",
        step2Desc: "Advanced algorithms identify skill gaps, match opportunities, and generate personalized recommendations.",
        step3: "Get Results",
        step3Desc: "Receive actionable insights, course recommendations, and a clear roadmap to your dream job."
      },
      features: {
        heading: "The future of knowledge",
        subheading: "Comprehensive solutions for everyone",
        professionals: "Professionals",
        professionalsDesc: "Build and manage complex professional knowledge dictionaries through advanced Knowledge Graph architecture. Automate skill analysis and standardize expert processes.",
        applicants: "Applicants",
        applicantsDesc: "Decode skill gaps and optimize your competency profile to lead in every opportunity hunt.",
        students: "Students",
        studentsDesc: "AI-refined personalized learning roadmap helps you shorten the gap from classroom to business reality.",
        learnMore: "Learn more"
      },
      testimonials: {
        heading: "Trusted by professionals",
        subheading: "See what our users have to say about their experience"
      },
      footer: {
        product: "Product",
        company: "Company",
        resources: "Resources",
        stayUpdated: "Stay updated",
        newsletter: "Get the latest news and updates delivered to your inbox.",
        emailPlaceholder: "Enter your email",
        copyright: "© 2026 Lumix AI. All rights reserved.",
        privacy: "Privacy Policy",
        terms: "Terms of Service",
        cookies: "Cookie Policy"
      }
    }
  };

  const currentLang = t[language];

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
            <Link href="#stats">{currentLang.nav.stats}</Link>
            <Link href="#how-it-works">{currentLang.nav.howItWorks}</Link>
            <Link href="#features">{currentLang.nav.features}</Link>
            <Link href="#testimonials">{currentLang.nav.testimonials}</Link>
            <Link href="/auth/login" className={styles.navCta}>{currentLang.nav.login}</Link>
            <button onClick={toggleLanguage} className={styles.langToggle}>
              {language === 'vi' ? 'EN' : 'VI'}
            </button>
          </div>

          {/* Mobile Toggle */}
          <div className={styles.navRight}>
            <button onClick={toggleLanguage} className={styles.langToggleMobile}>
              {language === 'vi' ? 'EN' : 'VI'}
            </button>
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
                  { href: "#stats", label: currentLang.nav.stats },
                  { href: "#how-it-works", label: currentLang.nav.howItWorks },
                  { href: "#features", label: currentLang.nav.features },
                  { href: "#testimonials", label: currentLang.nav.testimonials },
                  { href: "/auth/login", label: currentLang.nav.login, isCta: true }
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
              {currentLang.hero.title.split('\n').map((line, i) => (
                <React.Fragment key={i}>
                  {line}
                  {i === 0 && <br />}
                </React.Fragment>
              ))}
            </h1>
            <p className={styles.heroDescription}>
              {currentLang.hero.description}
            </p>
            <div className={styles.heroActions}>
              <Link href="/auth/register" className={styles.primaryBtn}>
                {currentLang.hero.getStarted}
              </Link>
              <Link href="#how-it-works" className={styles.secondaryBtn}>
                {currentLang.hero.learnMore} <ChevronRight size={18} />
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
              { value: "10,000+", label: currentLang.stats.cvs },
              { value: "95%", label: currentLang.stats.accuracy },
              { value: "500+", label: currentLang.stats.companies },
              { value: "24/7", label: currentLang.stats.support }
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
                  {currentLang.vision.heading}
                </h2>
                <div className={styles.visionDivider} />
                <p className={styles.visionText}>
                  {currentLang.vision.text}
                </p>
                <p className={styles.visionSubtext}>
                  {currentLang.vision.subtext}
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
                  <h4>{currentLang.vision.accurate}</h4>
                  <p>{currentLang.vision.accurateDesc}</p>
                </div>
                <div className={styles.visionStatItem}>
                  <div className={styles.visionStatIcon}>⚡</div>
                  <h4>{currentLang.vision.fast}</h4>
                  <p>{currentLang.vision.fastDesc}</p>
                </div>
                <div className={styles.visionStatItem}>
                  <div className={styles.visionStatIcon}>🚀</div>
                  <h4>{currentLang.vision.effective}</h4>
                  <p>{currentLang.vision.effectiveDesc}</p>
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
            <h2 className={styles.sectionHeading}>{currentLang.howItWorks.heading}</h2>
            <p className={styles.sectionSubheading}>
              {currentLang.howItWorks.subheading}
            </p>
          </div>

          <div className={styles.howItWorksGrid}>
            {[
              {
                icon: Upload,
                step: "01",
                title: currentLang.howItWorks.step1,
                description: currentLang.howItWorks.step1Desc
              },
              {
                icon: Sparkles,
                step: "02",
                title: currentLang.howItWorks.step2,
                description: currentLang.howItWorks.step2Desc
              },
              {
                icon: TrendingUp,
                step: "03",
                title: currentLang.howItWorks.step3,
                description: currentLang.howItWorks.step3Desc
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
              <h2 className={styles.sectionHeading}>{currentLang.features.heading}</h2>
              <p className={styles.featuresSubheading}>
                {currentLang.features.subheading}
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
                <h3 className={styles.bentoTitle}>{currentLang.features.professionals}</h3>
                <p className={styles.bentoDesc}>
                  {currentLang.features.professionalsDesc}
                </p>
              </div>
              <Link href="/auth/login" className={styles.secondaryBtn}>
                {currentLang.features.learnMore} <ChevronRight size={16} />
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
                <h3 className={styles.bentoTitle}>{currentLang.features.applicants}</h3>
                <p className={styles.bentoDesc}>
                  {currentLang.features.applicantsDesc}
                </p>
              </div>
              <Link href="/auth/login" className={styles.secondaryBtn}>
                {currentLang.features.learnMore} <ChevronRight size={16} />
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
                <h3 className={styles.bentoTitle}>{currentLang.features.students}</h3>
                <p className={styles.bentoDesc}>
                  {currentLang.features.studentsDesc}
                </p>
              </div>
              <Link href="/auth/login" className={styles.secondaryBtn}>
                {currentLang.features.learnMore} <ChevronRight size={16} />
              </Link>
            </motion.div>
          </div>
        </section>
      </div>

      {/* Testimonials Section - Light */}
      <div id="testimonials" className={`${styles.sectionWrapper} ${styles.bgLight}`}>
        <section className={styles.section}>
          <div className={styles.centeredText}>
            <h2 className={styles.sectionHeading}>{currentLang.testimonials.heading}</h2>
            <p className={styles.sectionSubheading}>
              {currentLang.testimonials.subheading}
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
                <h4 className={styles.footerHeading}>{currentLang.footer.product}</h4>
                <Link href="#features">Features</Link>
                <Link href="/auth/login">Pricing</Link>
                <Link href="#philosophy">About</Link>
                <Link href="/auth/register">Get Started</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{currentLang.footer.company}</h4>
                <Link href="/auth/login">Careers</Link>
                <Link href="/auth/login">Blog</Link>
                <Link href="/auth/login">Press</Link>
                <Link href="/auth/login">Contact</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{currentLang.footer.resources}</h4>
                <Link href="/auth/login">Documentation</Link>
                <Link href="/auth/login">Help Center</Link>
                <Link href="/auth/login">API</Link>
                <Link href="/auth/login">Community</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{currentLang.footer.stayUpdated}</h4>
                <p className={styles.footerNewsletter}>
                  {currentLang.footer.newsletter}
                </p>
                <div className={styles.newsletterForm}>
                  <input 
                    type="email" 
                    placeholder={currentLang.footer.emailPlaceholder}
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
                {currentLang.footer.copyright}
              </p>
              <div className={styles.footerLinks}>
                <Link href="/auth/login">{currentLang.footer.privacy}</Link>
                <Link href="/auth/login">{currentLang.footer.terms}</Link>
                <Link href="/auth/login">{currentLang.footer.cookies}</Link>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}



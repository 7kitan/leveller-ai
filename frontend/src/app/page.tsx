"use client";

import React from "react";
import Link from "next/link";
import { 
  Target, 
  Cpu,
  GraduationCap,
  ChevronRight,
  Upload,
  Sparkles,
  TrendingUp,
  ArrowRight,
  Star,
  Mail
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";
import LandingNavbar from "@/components/landing/LandingNavbar";

import styles from "./landing.module.css";

/* ========================================
 * MAIN PAGE COMPONENT
 * ======================================== */

export default function LandingPage() {
  const { language } = useLanguage();

  // Translation object
  const t = {
    vi: {
      hero: {
        title: "Định hình lại con đường tương lai",
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
        cookies: "Chính sách Cookie",
        features: "Tính năng",
        pricing: "Bảng giá",
        about: "Về chúng tôi",
        getStarted: "Bắt đầu ngay",
        careers: "Tuyển dụng",
        blog: "Blog",
        press: "Báo chí",
        contact: "Liên hệ",
        docs: "Tài liệu",
        helpCenter: "Trung tâm trợ giúp",
        api: "API",
        community: "Cộng đồng"
      }
    },
    en: {
      hero: {
        title: "Recode your future path",
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
        cookies: "Cookie Policy",
        features: "Features",
        pricing: "Pricing",
        about: "About",
        getStarted: "Get Started",
        careers: "Careers",
        blog: "Blog",
        press: "Press",
        contact: "Contact",
        docs: "Documentation",
        helpCenter: "Help Center",
        api: "API",
        community: "Community"
      }
    }
  };

  const currentLang = t[language];

  return (
    <div className={styles.pageRoot}>
      {/* Apple-style Glass Navbar */}
      <LandingNavbar />

      {/* Hero Section - Dark Immersive with Animated Gradient */}
      <div className={styles.sectionWrapper}>
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
              {currentLang.hero.title}
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
      <div id="stats" className={styles.sectionWrapper}>
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
      <div id="philosophy" className={styles.sectionWrapper}>
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
      <div id="how-it-works" className={styles.sectionWrapper}>
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
      <div id="features" className={styles.sectionWrapper}>
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
      <div id="testimonials" className={styles.sectionWrapper}>
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
                    <Star key={i} size={16} fill="var(--color-secondary)" color="var(--color-secondary)" />
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
      <div className={styles.sectionWrapper}>
        <footer className={styles.richFooter}>
          <div className={styles.footerContent}>
            <div className={styles.footerGrid}>
              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{currentLang.footer.product}</h4>
                <Link href="#features">{currentLang.footer.features}</Link>
                <Link href="/auth/login">{currentLang.footer.pricing}</Link>
                <Link href="#philosophy">{currentLang.footer.about}</Link>
                <Link href="/auth/register">{currentLang.footer.getStarted}</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{currentLang.footer.company}</h4>
                <Link href="/auth/login">{currentLang.footer.careers}</Link>
                <Link href="/auth/login">{currentLang.footer.blog}</Link>
                <Link href="/auth/login">{currentLang.footer.press}</Link>
                <Link href="/auth/login">{currentLang.footer.contact}</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{currentLang.footer.resources}</h4>
                <Link href="/auth/login">{currentLang.footer.docs}</Link>
                <Link href="/auth/login">{currentLang.footer.helpCenter}</Link>
                <Link href="/auth/login">{currentLang.footer.api}</Link>
                <Link href="/auth/login">{currentLang.footer.community}</Link>
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



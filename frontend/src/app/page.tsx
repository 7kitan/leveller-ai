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
  const { t } = useLanguage();

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
            transition={{ duration: 1, delay: 0.2 }}
          >
            <h1 className={styles.heroTitle}>
              {t("landing_hero_title")}
            </h1>
            <p className={styles.heroDescription}>
              {t("landing_hero_description")}
            </p>
            <div className={styles.heroCTA}>
              <Link href="/auth/register" className={styles.primaryBtn}>
                {t("landing_hero_get_started")}
              </Link>
              <Link href="#how-it-works" className={styles.secondaryBtn}>
                {t("landing_hero_learn_more")} <ChevronRight size={18} />
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
              { value: "10,000+", label: t("landing_stats_cvs") },
              { value: "95%", label: t("landing_stats_accuracy") },
              { value: "500+", label: t("landing_stats_companies") },
              { value: "24/7", label: t("landing_stats_support") }
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
                <div className={styles.visionText}>
                  <h2 className={styles.visionHeading}>
                    {t("landing_vision_heading")}
                  </h2>
                  <p className={styles.visionParagraph}>
                    {t("landing_vision_text")}
                  </p>
                  <p className={styles.visionSubtext}>
                    {t("landing_vision_subtext")}
                  </p>
                </div>
              </motion.div>

              <motion.div
                className={styles.visionFeatures}
                initial={{ opacity: 0, x: 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: 0.2 }}
              >
                <div className={styles.visionFeature}>
                  <Sparkles className={styles.visionIcon} />
                  <h4>{t("landing_vision_accurate")}</h4>
                  <p>{t("landing_vision_accurate_desc")}</p>
                </div>
                <div className={styles.visionFeature}>
                  <TrendingUp className={styles.visionIcon} />
                  <h4>{t("landing_vision_fast")}</h4>
                  <p>{t("landing_vision_fast_desc")}</p>
                </div>
                <div className={styles.visionFeature}>
                  <Target className={styles.visionIcon} />
                  <h4>{t("landing_vision_effective")}</h4>
                  <p>{t("landing_vision_effective_desc")}</p>
                </div>
              </motion.div>
            </div>
          </motion.div>
        </section>
      </div>

      {/* Testimonials Section */}
      <div id="testimonials" className={styles.sectionWrapper}>
        <section className={styles.section}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className={styles.sectionHeading}>{t("landing_testimonials_heading")}</h2>
            <p className={styles.sectionSubheading}>
              {t("landing_testimonials_subheading")}
            </p>
          </motion.div>

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
                    <Star key={i} size={16} fill="#06B6D4" color="#06B6D4" />
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
                <h4 className={styles.footerHeading}>{t("landing_footer_product")}</h4>
                <Link href="#features">{t("nav_features")}</Link>
                <Link href="/auth/login">{t("footer_pricing")}</Link>
                <Link href="#philosophy">{t("footer_about")}</Link>
                <Link href="/auth/register">{t("landing_hero_get_started")}</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{t("landing_footer_company")}</h4>
                <Link href="/auth/login">{t("footer_careers")}</Link>
                <Link href="/auth/login">{t("footer_blog")}</Link>
                <Link href="/auth/login">{t("footer_press")}</Link>
                <Link href="/auth/login">{t("footer_contact")}</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{t("landing_footer_resources")}</h4>
                <Link href="/auth/login">{t("footer_docs")}</Link>
                <Link href="/auth/login">{t("footer_help")}</Link>
                <Link href="/auth/login">{t("footer_api")}</Link>
                <Link href="/auth/login">{t("footer_community")}</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{t("landing_footer_stay_updated")}</h4>
                <p className={styles.footerNewsletter}>
                  {t("landing_footer_newsletter")}
                </p>
                <div className={styles.newsletterForm}>
                  <input 
                    type="email" 
                    placeholder={t("landing_footer_email_placeholder")}
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
                {t("landing_footer_copyright")}
              </p>
              <div className={styles.footerLinks}>
                <Link href="/auth/login">{t("landing_footer_privacy")}</Link>
                <Link href="/auth/login">{t("landing_footer_terms")}</Link>
                <Link href="/auth/login">{t("landing_footer_cookies")}</Link>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}



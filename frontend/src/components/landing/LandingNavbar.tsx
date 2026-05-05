"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";
import Logo from "@/components/shared/Logo";
import styles from "./landing-navbar.module.css";

/* ========================================
 * ANIMATION CONFIGURATIONS
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

export default function LandingNavbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { language, setLanguage, t } = useLanguage();
  const pathname = usePathname();
  const navRef = useRef<HTMLElement>(null);

  const isHomePage = pathname === "/";

  const toggleLanguage = () => {
    setLanguage(language === "vi" ? "en" : "vi");
  };

  const onToggle = () => setIsMenuOpen(!isMenuOpen);

  // Close menu when clicking outside
  useEffect(() => {
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
  useEffect(() => {
    if (isMenuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => { document.body.style.overflow = "unset"; };
  }, [isMenuOpen]);

  const navLinks = [
    { href: isHomePage ? "#stats" : "/#stats", label: t("nav_stats") },
    { href: isHomePage ? "#how-it-works" : "/#how-it-works", label: t("nav_how_it_works") },
    { href: isHomePage ? "#features" : "/#features", label: t("nav_features") },
    { href: isHomePage ? "#testimonials" : "/#testimonials", label: t("nav_testimonials") },
    { href: "/auth/login", label: t("nav_login"), isCta: true }
  ];

  return (
    <motion.nav 
      ref={navRef}
      className={styles.navWrapper}
      layout
      initial={false}
      animate={{
        backgroundColor: "rgba(255, 255, 255, 1)",
        borderRadius: isMenuOpen ? "28px" : "980px",
        paddingBottom: isMenuOpen ? "20px" : "0px",
        boxShadow: isMenuOpen ? "0 20px 40px rgba(0, 0, 0, 0.1)" : "0 8px 32px rgba(0, 0, 0, 0.08)"
      }}
      transition={{ duration: NAV_ANIMATION.duration, ease: NAV_ANIMATION.ease }}
    >
      <div className={styles.nav}>
        <Link href="/" className={styles.navLogo}>
          <Logo size="sm" />
        </Link>
        
        {/* Desktop Links */}
        <div className={styles.navLinks}>
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link 
                key={link.href} 
                href={link.href} 
                className={`${link.isCta ? styles.navCta : ""} ${isActive ? styles.navActive : ""}`}
              >
                {link.label}
              </Link>
            );
          })}
          <button onClick={toggleLanguage} className={styles.langToggle}>
            {language === 'vi' ? 'VI' : 'EN'}
          </button>
        </div>

        {/* Mobile Toggle */}
        <div className={styles.navRight}>
          <button onClick={toggleLanguage} className={styles.langToggleMobile}>
            {language === 'vi' ? 'EN' : 'VI'}
          </button>
          <button 
            className={styles.mobileToggle} 
            onClick={onToggle}
            aria-label={t("aria_toggle_menu")}
          >
            <motion.div
              animate={{ rotate: isMenuOpen ? 90 : 0 }}
              transition={{ duration: ICON_ANIMATION.duration, ease: ICON_ANIMATION.ease }}
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
              open: MOBILE_MENU_OPEN,
              closed: MOBILE_MENU_CLOSED
            }}
            style={{ overflow: "hidden" }}
          >
            <div className={styles.mobileLinks}>
              {navLinks.map((link) => {
                const isActive = pathname === link.href;
                return (
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
                      className={`${link.isCta ? styles.mobileCta : ""} ${isActive ? styles.mobileActive : ""}`} 
                      onClick={() => setIsMenuOpen(false)}
                    >
                      {link.label}
                    </Link>
                  </motion.div>
                );
              })}
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
  );
}

"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  Users, 
  Database, 
  Network, 
  ShieldCheck,
  ChevronRight,
  TrendingUp,
  Settings
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./admin-layout.module.css";

const AdminLayout = ({ children }: { children: React.ReactNode }) => {
  const pathname = usePathname();

  const navItems = [
    { name: "Insight Market", href: "/admin", icon: TrendingUp },
    { name: "Người dùng", href: "/admin/users", icon: Users },
    { name: "Thực thể Graph", href: "/admin/taxonomy", icon: Database },
    { name: "Quan hệ Graph", href: "/admin/relations", icon: Network },
    { name: "Cấu hình", href: "/admin/settings", icon: Settings },
  ];

  return (
    <div className={styles.layoutRoot}>
      {/* Sidebar Navigation */}
      <aside className={styles.sidebar}>
        <div className={styles.logoArea}>
          <div className={styles.logoIconWrapper}>
            <ShieldCheck className={styles.logoIcon} />
          </div>
          <div className={styles.logoText}>
            CORE<span className={styles.nexus}>NEXUS</span>
          </div>
        </div>

        <nav className={styles.navSection}>
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  styles.navLink,
                  isActive && styles.navLinkActive
                )}
              >
                <item.icon className={styles.navIcon} />
                <span>{item.name}</span>
                <ChevronRight className={styles.chevron} />
              </Link>
            );
          })}
        </nav>

        <div className={styles.footer}>
          <p className={styles.footerText}>Admin System v1.2</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className={styles.mainContent}>
        {children}
      </main>
    </div>
  );
};

export default AdminLayout;

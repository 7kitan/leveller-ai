import type { Metadata } from "next";
import { Space_Grotesk } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";
import "../light-mode.css";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import LayoutWrapper from "@/components/shared/LayoutWrapper";
import { LanguageProvider } from "@/context/LanguageContext";
import { AlertProvider } from "@/context/AlertContext";

const tasaOrbiter = localFont({
  src: [
    {
      path: "../fonts/tasa-orbiter-400.ttf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../fonts/tasa-orbiter-500.ttf",
      weight: "500",
      style: "normal",
    },
    {
      path: "../fonts/tasa-orbiter-600.ttf",
      weight: "600",
      style: "normal",
    },
    {
      path: "../fonts/tasa-orbiter-700.ttf",
      weight: "700",
      style: "normal",
    },
    {
      path: "../fonts/tasa-orbiter-800.ttf",
      weight: "800",
      style: "normal",
    },
  ],
  variable: "--font-tasa-orbiter",
});

const spaceGrotesk = Space_Grotesk({ 
  subsets: ["latin"], 
  variable: "--font-space-grotesk" 
});

export const metadata: Metadata = {
  title: "Lumix AI | Career Nexus & Knowledge Graph",
  description: "Giải mã tương lai sự nghiệp với trí tuệ nhân tạo. Phân tích khoảng trống kỹ năng, gợi ý lộ trình học tập và quản trị tri thức kỹ thuật chuyên sâu.",
  keywords: ["AI Career", "Skill Gap Analysis", "Technical Taxonomy", "Career Roadmap", "Job Matching"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${tasaOrbiter.variable} ${spaceGrotesk.variable}`} suppressHydrationWarning>
      <body className="antialiased">
        <LanguageProvider>
          <ThemeProvider>
            <AlertProvider>
              <AuthProvider>
                <LayoutWrapper>
                  {children}
                </LayoutWrapper>
              </AuthProvider>
            </AlertProvider>
          </ThemeProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}

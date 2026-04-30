import type { Metadata } from "next";
import { Open_Sans } from "next/font/google";
import "./globals.css";
import "../light-mode.css";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import LayoutWrapper from "@/components/shared/LayoutWrapper";
import { LanguageProvider } from "@/context/LanguageContext";
import { AlertProvider } from "@/context/AlertContext";
import DynamicHtmlLang from "@/components/shared/DynamicHtmlLang";

const openSans = Open_Sans({ 
  subsets: ["latin", "vietnamese"], 
  variable: "--font-sans" 
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
    <html lang="en" className={`${openSans.variable}`} suppressHydrationWarning>
      <body className="antialiased">
        <LanguageProvider>
          <DynamicHtmlLang />
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

import type { Metadata } from "next";
import { Open_Sans, Bricolage_Grotesque } from "next/font/google";
import "./globals.css";
import "../light-mode.css";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import LayoutWrapper from "@/components/shared/LayoutWrapper";
import { LanguageProvider } from "@/context/LanguageContext";

const openSans = Open_Sans({ 
  subsets: ["latin", "vietnamese"], 
  variable: "--font-sans" 
});

const bricolage = Bricolage_Grotesque({ 
  subsets: ["latin", "vietnamese"], 
  variable: "--font-bricolage" 
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
    <html lang="en" className={`${openSans.variable} ${bricolage.variable}`} suppressHydrationWarning>
      <body className="antialiased">
        <LanguageProvider>
          <ThemeProvider>
            <AuthProvider>
              <LayoutWrapper>
                {children}
              </LayoutWrapper>
            </AuthProvider>
          </ThemeProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}

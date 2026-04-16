import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";
import "../light-mode.css";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import LayoutWrapper from "@/components/shared/LayoutWrapper";
import AuthGuard from "@/components/auth/AuthGuard";

const inter = Outfit({ subsets: ["latin"], variable: "--font-inter" });
const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit" });

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
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${outfit.variable} antialiased`}>
        <ThemeProvider>
          <AuthProvider>
            <LayoutWrapper>
              <AuthGuard>
                {children}
              </AuthGuard>
            </LayoutWrapper>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

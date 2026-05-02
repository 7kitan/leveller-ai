import type { Metadata } from "next";
import { Space_Grotesk, Lato } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import LayoutWrapper from "@/components/shared/LayoutWrapper";
import { LanguageProvider } from "@/context/LanguageContext";
import { AlertProvider } from "@/context/AlertContext";

const spaceGrotesk = Space_Grotesk({ 
  subsets: ["latin"], 
  variable: "--font-space-grotesk" 
});

const lato = Lato({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "700"],
  variable: "--font-lato",
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
    <html lang="en" className={`${spaceGrotesk.variable} ${lato.variable}`} suppressHydrationWarning>
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

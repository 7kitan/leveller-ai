import type { Metadata } from "next";
import { Space_Grotesk, Google_Sans_Flex, Google_Sans } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import LayoutWrapper from "@/components/shared/LayoutWrapper";
import { LanguageProvider } from "@/context/LanguageContext";
import { AlertProvider } from "@/context/AlertContext";
import DynamicHtmlLang from "@/components/shared/DynamicHtmlLang";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});

const googleSansFlex = Google_Sans_Flex({
  subsets: ["latin"],
  variable: "--font-google-sans-flex",
});

const googleSans = Google_Sans({
  subsets: ["latin"],
  variable: "--font-google-sans",
});

const product_sans = localFont({
  src: [
    {
      path: "../fonts/Product Sans Regular.otf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../fonts/Product Sans Bold.otf",
      weight: "700",
      style: "bold",
    },
  ],
  variable: "--font-product-sans",
});

export const metadata: Metadata = {
  title: "Lumix AI - Skill Mapping & Career Roadmaps",
  description: "Bridge the gap between your skills and your dream job with AI-powered career roadmaps.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${product_sans.variable} ${googleSansFlex.variable} ${googleSans.variable}`} suppressHydrationWarning>
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

"use client";

import React from "react";
import Sidebar from "./Sidebar";
import Navbar from "./Navbar";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

const LayoutWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname();
  const { user, loading } = useAuth();
  
  // Routes where sidebar/navbar should be hidden
  const isAuthPage = pathname.startsWith("/auth");
  const isAdminPage = pathname.startsWith("/admin");
  const isLandingPage = pathname === "/" && !user;
  const showChrome = !isAuthPage && !isAdminPage && !isLandingPage && user;

  return (
    <div className="min-h-screen relative overflow-x-hidden bg-[#030508] text-white">
      {/* Dynamic Ambient Glows */}
      <div className="fixed top-[-20%] left-[-10%] w-[50%] h-[50%] bg-violet-600/10 blur-[150px] rounded-full pointer-events-none"></div>
      <div className="fixed bottom-[-10%] right-[-5%] w-[40%] h-[40%] bg-cyan-500/10 blur-[150px] rounded-full pointer-events-none"></div>
      
      {showChrome && <Sidebar />}

      <div 
        className={`main-content transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)] ${
          showChrome ? "pl-[280px]" : "pl-0"
        }`}
      >
        {showChrome && <Navbar />}

        <main className={`relative z-10 ${showChrome ? "p-8 max-w-7xl mx-auto" : ""}`}>
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
            {children}
          </div>
        </main>
        
        {/* Futuristic subtle footer for dashboards */}
        {showChrome && (
          <footer className="mt-20 border-t border-white/5 py-8 text-center text-white/20 text-xs tracking-widest uppercase">
            &copy; 2026 Lumix AI &bull; Career Nexus Architecture &bull; V6.0
          </footer>
        )}
      </div>
    </div>
  );
};

export default LayoutWrapper;

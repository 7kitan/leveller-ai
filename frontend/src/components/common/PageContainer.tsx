"use client";

import React from "react";
import { cn } from "@/lib/utils";
import styles from "./PageContainer.module.css";

interface PageContainerProps {
  children: React.ReactNode;
  variant?: "default" | "fullWidth" | "center";
  className?: string;
}

const PageContainer: React.FC<PageContainerProps> = ({
  children,
  variant = "default",
  className,
}) => {
  return (
    <main className={cn(styles.pageContainer, styles[variant], className)}>
      {children}
    </main>
  );
};

export default PageContainer;

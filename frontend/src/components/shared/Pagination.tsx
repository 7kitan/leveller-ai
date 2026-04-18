"use client";

import React from "react";
import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  className?: string;
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  className,
}) => {
  if (totalPages <= 1) return null;

  const renderPageNumbers = () => {
    const pages = [];
    const maxVisiblePages = 5;

    if (totalPages <= maxVisiblePages) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Logic for ellipsis
      if (currentPage <= 3) {
        pages.push(1, 2, 3, 4, "...", totalPages);
      } else if (currentPage >= totalPages - 2) {
        pages.push(1, "...", totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
      } else {
        pages.push(1, "...", currentPage - 1, currentPage, currentPage + 1, "...", totalPages);
      }
    }

    return pages.map((page, idx) => {
      if (page === "...") {
        return (
          <span key={`ell-${idx}`} className="px-2 text-slate-400">
            <MoreHorizontal size={16} />
          </span>
        );
      }

      const isCurrent = page === currentPage;
      return (
        <button
          key={page}
          onClick={() => onPageChange(page as number)}
          className={cn(
            "min-w-[2.5rem] h-10 rounded-xl font-bold transition-all duration-300",
            isCurrent 
              ? "bg-[var(--color-accent-primary)] text-white shadow-lg shadow-indigo-200" 
              : "hover:bg-slate-100 text-slate-600"
          )}
        >
          {page}
        </button>
      );
    });
  };

  return (
    <div className={cn("flex items-center justify-center gap-2 mt-8", className)}>
      <button
        onClick={() => onPageChange(Math.max(1, currentPage - 1))}
        disabled={currentPage === 1}
        className={cn(
          "p-2 rounded-xl border border-slate-200 transition-all duration-300",
          currentPage === 1 ? "opacity-30 cursor-not-allowed" : "hover:bg-slate-50 hover:border-slate-300"
        )}
      >
        <ChevronLeft size={20} className="text-slate-600" />
      </button>

      <div className="flex items-center gap-1">{renderPageNumbers()}</div>

      <button
        onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
        disabled={currentPage === totalPages}
        className={cn(
          "p-2 rounded-xl border border-slate-200 transition-all duration-300",
          currentPage === totalPages ? "opacity-30 cursor-not-allowed" : "hover:bg-slate-50 hover:border-slate-300"
        )}
      >
        <ChevronRight size={20} className="text-slate-600" />
      </button>
    </div>
  );
};

export default Pagination;

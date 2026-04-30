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
          <span 
            key={`ell-${idx}`} 
            style={{
              padding: '0 0.5rem',
              color: 'var(--color-text-muted)',
              opacity: 0.5
            }}
          >
            <MoreHorizontal size={16} />
          </span>
        );
      }

      const isCurrent = page === currentPage;
      return (
        <button
          key={page}
          onClick={() => onPageChange(page as number)}
          style={{
            minWidth: '2.5rem',
            height: '2.5rem',
            borderRadius: 'var(--radius-md)',
            fontWeight: 700,
            fontSize: 'var(--font-size-base)',
            transition: 'all 0.3s ease',
            backgroundColor: isCurrent ? 'var(--color-bg-secondary)' : 'transparent',
            color: isCurrent ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
            border: isCurrent ? '2px solid var(--color-primary)' : '1px solid transparent',
            cursor: 'pointer',
          }}
          onMouseEnter={(e) => {
            if (!isCurrent) {
              e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)';
              e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
            }
          }}
          onMouseLeave={(e) => {
            if (!isCurrent) {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.borderColor = 'transparent';
            }
          }}
        >
          {page}
        </button>
      );
    });
  };

  return (
    <div 
      className={className}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.5rem',
        marginTop: '3rem'
      }}
    >
      <button
        onClick={() => onPageChange(Math.max(1, currentPage - 1))}
        disabled={currentPage === 1}
        style={{
          padding: '0.5rem',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-subtle)',
          backgroundColor: 'var(--color-bg-elevated)',
          transition: 'all 0.3s ease',
          opacity: currentPage === 1 ? 0.3 : 1,
          cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        onMouseEnter={(e) => {
          if (currentPage !== 1) {
            e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)';
            e.currentTarget.style.borderColor = 'var(--color-border-default)';
          }
        }}
        onMouseLeave={(e) => {
          if (currentPage !== 1) {
            e.currentTarget.style.backgroundColor = 'var(--color-bg-elevated)';
            e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
          }
        }}
      >
        <ChevronLeft size={20} style={{ color: 'var(--color-text-secondary)' }} />
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
        {renderPageNumbers()}
      </div>

      <button
        onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
        disabled={currentPage === totalPages}
        style={{
          padding: '0.5rem',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-subtle)',
          backgroundColor: 'var(--color-bg-elevated)',
          transition: 'all 0.3s ease',
          opacity: currentPage === totalPages ? 0.3 : 1,
          cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        onMouseEnter={(e) => {
          if (currentPage !== totalPages) {
            e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)';
            e.currentTarget.style.borderColor = 'var(--color-border-default)';
          }
        }}
        onMouseLeave={(e) => {
          if (currentPage !== totalPages) {
            e.currentTarget.style.backgroundColor = 'var(--color-bg-elevated)';
            e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
          }
        }}
      >
        <ChevronRight size={20} style={{ color: 'var(--color-text-secondary)' }} />
      </button>
    </div>
  );
};

export default Pagination;

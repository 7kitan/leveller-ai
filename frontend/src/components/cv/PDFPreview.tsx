"use client";

import { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import styles from './CVPreview.module.css';
import { useLanguage } from '@/context/LanguageContext';

// Worker URL - use unpkg CDN which mirrors npm packages directly
const WORKER_URL = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

// Set worker source globally
pdfjs.GlobalWorkerOptions.workerSrc = WORKER_URL;

interface PDFPreviewProps {
  file: File;
}

export function PDFPreview({ file }: PDFPreviewProps) {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error);
    setLoading(false);
  };

  return (
    <div className={styles.pdfPreview}>
      <Document
        file={file}
        onLoadSuccess={onDocumentLoadSuccess}
        onLoadError={onDocumentLoadError}
        loading={
          <div className={styles.previewLoading}>
            <div className={styles.spinner} />
            <p>{t("pdf_loading")}</p>
          </div>
        }
        error={
          <div className={styles.previewError}>
            <p>{t("pdf_error")}</p>
          </div>
        }
      >
        <Page 
          pageNumber={pageNumber}
          width={typeof window !== 'undefined' ? Math.min(window.innerWidth * 0.7, 700) : 700}
          renderTextLayer={false}
          renderAnnotationLayer={false}
          className={styles.pdfPage}
        />
      </Document>

      {numPages > 1 && (
        <div className={styles.pdfControls}>
          <button
            onClick={() => setPageNumber(Math.max(1, pageNumber - 1))}
            disabled={pageNumber <= 1}
            className={styles.pdfNavBtn}
          >
            <ChevronLeft size={18} />
            {t("pdf_prev")}
          </button>
          
          <span className={styles.pageInfo}>
            {t("pdf_page_of").replace('{pageNumber}', String(pageNumber)).replace('{numPages}', String(numPages))}
          </span>
          
          <button
            onClick={() => setPageNumber(Math.min(numPages, pageNumber + 1))}
            disabled={pageNumber >= numPages}
            className={styles.pdfNavBtn}
          >
            {t("pdf_next")}
            <ChevronRight size={18} />
          </button>
        </div>
      )}
    </div>
  );
}

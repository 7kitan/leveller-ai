"use client";

import { useState, useEffect } from 'react';
import mammoth from 'mammoth';
import styles from './CVPreview.module.css';
import { useLanguage } from '@/context/LanguageContext';

interface DOCXPreviewProps {
  file: File;
}

export function DOCXPreview({ file }: DOCXPreviewProps) {
  const { t } = useLanguage();
  const [htmlContent, setHtmlContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const loadDocx = async () => {
      try {
        setLoading(true);
        setError('');
        
        // Read file as ArrayBuffer
        const arrayBuffer = await file.arrayBuffer();
        
        // Convert DOCX to HTML
        const result = await mammoth.convertToHtml({ arrayBuffer });
        
        setHtmlContent(result.value);
        
        // Log warnings if any
        if (result.messages.length > 0) {
          console.warn('DOCX conversion warnings:', result.messages);
        }
      } catch (err) {
        console.error('DOCX preview error:', err);
        setError(t('docx_error'));
      } finally {
        setLoading(false);
      }
    };

    loadDocx();
  }, [file]);

  if (loading) {
    return (
      <div className={styles.previewLoading}>
        <div className={styles.spinner} />
        <p>{t("docx_loading")}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.previewError}>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div 
      className={styles.docxPreview}
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
}

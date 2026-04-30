"use client";

import { PDFPreview } from './PDFPreview';
import { ImagePreview } from './ImagePreview';
import { DOCXPreview } from './DOCXPreview';
import { X, Check, FileText } from 'lucide-react';
import styles from './CVPreview.module.css';
import { useLanguage } from '@/context/LanguageContext';
import { formatNumber } from '@/lib/utils';

interface CVPreviewProps {
  file: File;
  onConfirm: () => void;
  onCancel: () => void;
}

export function CVPreview({ file, onConfirm, onCancel }: CVPreviewProps) {
  const { t } = useLanguage();
  const fileExtension = file.name.split('.').pop()?.toLowerCase();
  const fileSizeKB = formatNumber(file.size / 1024, 2);
  const fileSizeMB = formatNumber(file.size / 1024 / 1024, 2);
  const displaySize = file.size > 1024 * 1024 ? `${fileSizeMB} MB` : `${fileSizeKB} KB`;

  const renderPreview = () => {
    switch (fileExtension) {
      case 'pdf':
        return <PDFPreview file={file} />;
      
      case 'png':
      case 'jpg':
      case 'jpeg':
        return <ImagePreview file={file} />;
      
      case 'doc':
      case 'docx':
        return <DOCXPreview file={file} />;
      
      default:
        return (
          <div className={styles.unsupportedPreview}>
            <FileText size={48} color="#9ca3af" />
            <p>{t("unsupported_preview")} .{fileExtension}</p>
            <p className={styles.fileName}>{file.name}</p>
            <p className={styles.fileSize}>{displaySize}</p>
          </div>
        );
    }
  };

  return (
    <div className={styles.cvPreviewWrapper}>
      <div className={styles.fileInfoBar}>
        <div>
          <span className={styles.fileName}>{file.name}</span>
        </div>
        <span className={styles.fileSize}>{displaySize}</span>
      </div>

      <div className={styles.previewContainer}>
        {renderPreview()}
      </div>

      <div className={styles.previewActions}>
        <button 
          className={`${styles.actionBtn} ${styles.cancelBtn}`}
          onClick={onCancel}
        >
          <X size={18} />
          {t("cv_browse_files")}
        </button>

        <button 
          className={`${styles.actionBtn} ${styles.confirmBtn}`}
          onClick={onConfirm}
        >
          <Check size={18} />
          {t("cv_start_extract")}
        </button>
      </div>
    </div>
  );
}

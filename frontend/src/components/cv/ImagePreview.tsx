"use client";

import { useState, useEffect } from 'react';
import styles from './CVPreview.module.css';
import { useLanguage } from '@/context/LanguageContext';

interface ImagePreviewProps {
  file: File;
}

export function ImagePreview({ file }: ImagePreviewProps) {
  const { t } = useLanguage();
  const [previewUrl, setPreviewUrl] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Create object URL for instant preview
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    setLoading(false);

    // Cleanup
    return () => {
      URL.revokeObjectURL(url);
    };
  }, [file]);

  if (loading) {
    return (
      <div className={styles.previewLoading}>
        <div className={styles.spinner} />
        <p>{t("image_loading")}</p>
      </div>
    );
  }

  return (
    <div className={styles.imagePreview}>
      <img 
        src={previewUrl} 
        alt={t("image_preview_alt")} 
        className={styles.previewImage}
        onLoad={() => setLoading(false)}
      />
    </div>
  );
}

'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from './ThemeContext';
import { useLanguage } from './LanguageContext';

type AlertType = 'success' | 'error' | 'warning' | 'info';

interface AlertOptions {
  type: AlertType;
  title?: string;
  message: string;
  duration?: number; // milliseconds, 0 = no auto-dismiss
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ConfirmOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'primary';
}

interface AlertContextType {
  showAlert: (options: AlertOptions) => void;
  showSuccess: (message: string, title?: string) => void;
  showError: (message: string, title?: string) => void;
  showWarning: (message: string, title?: string) => void;
  showInfo: (message: string, title?: string) => void;
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const AlertContext = createContext<AlertContextType | undefined>(undefined);

export const AlertProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { theme } = useTheme();
  const { t } = useLanguage();
  const [alerts, setAlerts] = useState<Array<AlertOptions & { id: string }>>([]);
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    options: ConfirmOptions;
    resolve: (value: boolean) => void;
  } | null>(null);

  const showAlert = useCallback((options: AlertOptions) => {
    const id = Math.random().toString(36).substring(7);
    const alert = { ...options, id };
    setAlerts((prev) => [...prev, alert]);

    if (options.duration !== 0) {
      setTimeout(() => {
        setAlerts((prev) => prev.filter((a) => a.id !== id));
      }, options.duration || 5000);
    }
  }, []);

  const showSuccess = useCallback((message: string, title?: string) => {
    showAlert({ type: 'success', message, title, duration: 4000 });
  }, [showAlert]);

  const showError = useCallback((message: string, title?: string) => {
    showAlert({ type: 'error', message, title, duration: 6000 });
  }, [showAlert]);

  const showWarning = useCallback((message: string, title?: string) => {
    showAlert({ type: 'warning', message, title, duration: 5000 });
  }, [showAlert]);

  const showInfo = useCallback((message: string, title?: string) => {
    showAlert({ type: 'info', message, title, duration: 4000 });
  }, [showAlert]);

  const confirm = useCallback((options: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setConfirmDialog({ isOpen: true, options, resolve });
    });
  }, []);

  const handleConfirm = (result: boolean) => {
    if (confirmDialog) {
      confirmDialog.resolve(result);
      setConfirmDialog(null);
    }
  };

  const removeAlert = (id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  };

  const getAlertIcon = (type: AlertType) => {
    switch (type) {
      case 'success': return <CheckCircle2 size={20} />;
      case 'error': return <XCircle size={20} />;
      case 'warning': return <AlertTriangle size={20} />;
      case 'info': return <Info size={20} />;
    }
  };

  const getAlertColors = (type: AlertType) => {
    const isDark = theme === 'dark';
    switch (type) {
      case 'success':
        return {
          bg: isDark ? 'rgba(34, 197, 94, 0.15)' : 'rgba(34, 197, 94, 0.1)',
          border: '#22c55e',
          text: isDark ? '#86efac' : '#16a34a',
          icon: '#22c55e'
        };
      case 'error':
        return {
          bg: isDark ? 'rgba(239, 68, 68, 0.15)' : 'rgba(239, 68, 68, 0.1)',
          border: '#ef4444',
          text: isDark ? '#fca5a5' : '#dc2626',
          icon: '#ef4444'
        };
      case 'warning':
        return {
          bg: isDark ? 'rgba(245, 158, 11, 0.15)' : 'rgba(245, 158, 11, 0.1)',
          border: '#f59e0b',
          text: isDark ? '#fcd34d' : '#d97706',
          icon: '#f59e0b'
        };
      case 'info':
        return {
          bg: isDark ? 'rgba(59, 130, 246, 0.15)' : 'rgba(59, 130, 246, 0.1)',
          border: '#3b82f6',
          text: isDark ? '#93c5fd' : '#2563eb',
          icon: '#3b82f6'
        };
    }
  };

  return (
    <AlertContext.Provider value={{ showAlert, showSuccess, showError, showWarning, showInfo, confirm }}>
      {children}

      {/* Toast Notifications */}
      <div style={{
        position: 'fixed',
        top: '20px',
        right: '20px',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        maxWidth: '420px',
        pointerEvents: 'none'
      }}>
        <AnimatePresence>
          {alerts.map((alert) => {
            const colors = getAlertColors(alert.type);
            return (
              <motion.div
                key={alert.id}
                initial={{ opacity: 0, x: 100, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 100, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                style={{
                  background: colors.bg,
                  border: `1px solid ${colors.border}`,
                  borderRadius: '12px',
                  padding: '16px',
                  boxShadow: theme === 'dark' 
                    ? '0 10px 40px rgba(0, 0, 0, 0.5)' 
                    : '0 10px 40px rgba(0, 0, 0, 0.15)',
                  backdropFilter: 'blur(10px)',
                  pointerEvents: 'auto',
                  minWidth: '320px'
                }}
              >
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <div style={{ color: colors.icon, flexShrink: 0, marginTop: '2px' }}>
                    {getAlertIcon(alert.type)}
                  </div>
                  <div style={{ flex: 1 }}>
                    {alert.title && (
                      <div style={{
                        fontWeight: 600,
                        fontSize: '14px',
                        marginBottom: '4px',
                        color: colors.text
                      }}>
                        {alert.title}
                      </div>
                    )}
                    <div style={{
                      fontSize: '13px',
                      color: theme === 'dark' ? 'rgba(255, 255, 255, 0.8)' : 'rgba(15, 23, 42, 0.8)',
                      lineHeight: '1.5'
                    }}>
                      {alert.message}
                    </div>
                    {alert.action && (
                      <button
                        onClick={alert.action.onClick}
                        style={{
                          marginTop: '12px',
                          padding: '6px 12px',
                          background: colors.border,
                          color: '#fff',
                          border: 'none',
                          borderRadius: '6px',
                          fontSize: '12px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          transition: 'opacity 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.opacity = '0.8'}
                        onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                      >
                        {alert.action.label}
                      </button>
                    )}
                  </div>
                  <button
                    onClick={() => removeAlert(alert.id)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: theme === 'dark' ? 'rgba(255, 255, 255, 0.5)' : 'rgba(15, 23, 42, 0.5)',
                      cursor: 'pointer',
                      padding: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '4px',
                      transition: 'background 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = theme === 'dark' 
                        ? 'rgba(255, 255, 255, 0.1)' 
                        : 'rgba(15, 23, 42, 0.1)';
                    }}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <X size={16} />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Confirm Dialog */}
      <AnimatePresence>
        {confirmDialog?.isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(0, 0, 0, 0.5)',
                backdropFilter: 'blur(4px)',
                zIndex: 10000,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px'
              }}
              onClick={() => handleConfirm(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.2 }}
              style={{
                position: 'fixed',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                zIndex: 10001,
                background: theme === 'dark' ? '#1e293b' : '#ffffff',
                borderRadius: '16px',
                padding: '24px',
                maxWidth: '440px',
                width: '100%',
                boxShadow: theme === 'dark'
                  ? '0 20px 60px rgba(0, 0, 0, 0.6)'
                  : '0 20px 60px rgba(0, 0, 0, 0.2)',
                border: theme === 'dark' ? '1px solid rgba(255, 255, 255, 0.1)' : '1px solid rgba(15, 23, 42, 0.1)'
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {confirmDialog.options.title && (
                <h3 style={{
                  margin: '0 0 12px 0',
                  fontSize: '18px',
                  fontWeight: 600,
                  color: theme === 'dark' ? '#fff' : '#0f172a'
                }}>
                  {confirmDialog.options.title}
                </h3>
              )}
              <p style={{
                margin: '0 0 24px 0',
                fontSize: '14px',
                lineHeight: '1.6',
                color: theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(15, 23, 42, 0.7)'
              }}>
                {confirmDialog.options.message}
              </p>
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button
                  onClick={() => handleConfirm(false)}
                  style={{
                    padding: '10px 20px',
                    background: theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(15, 23, 42, 0.05)',
                    color: theme === 'dark' ? '#fff' : '#0f172a',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'background 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = theme === 'dark' 
                      ? 'rgba(255, 255, 255, 0.15)' 
                      : 'rgba(15, 23, 42, 0.1)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = theme === 'dark' 
                      ? 'rgba(255, 255, 255, 0.1)' 
                      : 'rgba(15, 23, 42, 0.05)';
                  }}
                >
                  {confirmDialog.options.cancelText || t('cancel')}
                </button>
                <button
                  onClick={() => handleConfirm(true)}
                  style={{
                    padding: '10px 20px',
                    background: confirmDialog.options.variant === 'danger' ? '#ef4444' : '#3b82f6',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'opacity 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
                  onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                >
                  {confirmDialog.options.confirmText || t('confirm')}
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </AlertContext.Provider>
  );
};

export const useAlert = () => {
  const context = useContext(AlertContext);
  if (context === undefined) {
    throw new Error('useAlert must be used within an AlertProvider');
  }
  return context;
};

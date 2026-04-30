"use client";

import React, { useEffect, useState } from "react";
import { 
  Shield, 
  Search,
  RefreshCcw,
  Trash2,
  AlertTriangle,
  Clock,
  Ban
} from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthContext";
import { useLanguage } from "@/context/LanguageContext";
import AuthGuard from "@/components/auth/AuthGuard";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";
import Portal from "@/components/shared/Portal";
import Modal from "@/components/shared/Modal";
import api from "@/lib/api";
import { formatHours, formatNumber } from "@/lib/utils";
import styles from "./blocked-ips.module.css";

interface BlockedIP {
  ip_address: string;
  attempts: number | null;
  expires_in: string;
  ttl_hours: number;
}

const BlockedIPsPage = () => {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [blockedIPs, setBlockedIPs] = useState<BlockedIP[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  
  // Modals
  const [showUnblockModal, setShowUnblockModal] = useState(false);
  const [showClearAllModal, setShowClearAllModal] = useState(false);
  const [selectedIP, setSelectedIP] = useState<string | null>(null);
  const [confirmText, setConfirmText] = useState("");

  const fetchBlockedIPs = async () => {
    try {
      setLoading(true);
      const res = await api.get("/admin/blocked-ips");
      setBlockedIPs(res.data.blocked_ips || []);
    } catch (err: any) {
      console.error("Fetch blocked IPs error:", err);
      toast.error(err.response?.data?.detail || t("blocked_ips_load_error"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === "admin") {
      fetchBlockedIPs();
    }
  }, [user]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchBlockedIPs();
    setRefreshing(false);
    toast.success(t("blocked_ips_refreshed"));
  };

  const handleUnblock = async (ip: string) => {
    try {
      await api.post("/admin/unblock-ip", { ip_address: ip });
      toast.success(t("blocked_ips_unblocked").replace("{ip}", ip));
      setShowUnblockModal(false);
      setSelectedIP(null);
      fetchBlockedIPs();
    } catch (err: any) {
      console.error("Unblock error:", err);
      toast.error(err.response?.data?.detail || t("blocked_ips_unblock_error"));
    }
  };

  const handleClearAll = async () => {
    if (confirmText.toLowerCase() !== "clear all") {
      toast.error(t("blocked_ips_type_clear_all"));
      return;
    }

    try {
      const res = await api.delete("/admin/blocked-ips");
      toast.success(res.data.message || t("blocked_ips_cleared"));
      setShowClearAllModal(false);
      setConfirmText("");
      fetchBlockedIPs();
    } catch (err: any) {
      console.error("Clear all error:", err);
      toast.error(err.response?.data?.detail || t("blocked_ips_clear_error"));
    }
  };

  const filteredIPs = blockedIPs.filter(ip =>
    ip.ip_address.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getSeverityClass = (ttlHours: number): string => {
    if (ttlHours > 20) return styles.severityHigh;
    if (ttlHours > 10) return styles.severityMedium;
    return styles.severityLow;
  };

  const getAttemptsClass = (attempts: number | null): string => {
    if (!attempts) return "";
    if (attempts >= 10) return styles.attemptsCritical;
    if (attempts >= 5) return styles.attemptsHigh;
    return styles.attemptsNormal;
  };

  return (
    <AuthGuard requireAdmin>
      <PageContainer>
        <PageHeader
          title={<><Shield className={styles.headerIcon} /> {t("blocked_ips_title")}</>}
          subtitle={t("blocked_ips_subtitle")}
        />

        {/* Actions Bar */}
        <div className={styles.actionsBar}>
          <div className={styles.searchBox}>
            <Search className={styles.searchIcon} size={18} />
            <input
              type="text"
              placeholder={t("blocked_ips_search_placeholder")}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={styles.searchInput}
            />
          </div>

          <div className={styles.actionButtons}>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className={styles.btnSecondary}
            >
              <RefreshCcw size={16} className={refreshing ? styles.spinning : ""} />
              {t("blocked_ips_refresh")}
            </button>
            <button
              onClick={() => setShowClearAllModal(true)}
              disabled={blockedIPs.length === 0}
              className={styles.btnDanger}
            >
              <Trash2 size={16} />
              {t("blocked_ips_clear_all")}
            </button>
          </div>
        </div>

        {/* Stats Bar */}
        <div className={styles.statsBar}>
          <div className={styles.statItem}>
            <Ban size={18} />
            <span className={styles.statLabel}>{t("blocked_ips_total")}</span>
            <span className={styles.statValue}>{blockedIPs.length}</span>
          </div>
          <div className={styles.statItem}>
            <Search size={18} />
            <span className={styles.statLabel}>{t("blocked_ips_showing")}</span>
            <span className={styles.statValue}>{filteredIPs.length}</span>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className={styles.loadingState}>
            <div className={styles.spinner}></div>
            <p>{t("blocked_ips_loading")}</p>
          </div>
        ) : filteredIPs.length === 0 ? (
          <div className={styles.emptyState}>
            <Shield size={64} className={styles.emptyIcon} />
            <h3>{t("blocked_ips_no_blocked")}</h3>
            <p>
              {searchTerm
                ? t("blocked_ips_no_match")
                : t("blocked_ips_no_currently_blocked")}
            </p>
          </div>
        ) : (
          <>
            {/* Desktop Table */}
            <div className={styles.tableContainer}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>{t("blocked_ips_table_ip")}</th>
                    <th>{t("blocked_ips_table_attempts")}</th>
                    <th>{t("blocked_ips_table_remaining")}</th>
                    <th>{t("blocked_ips_table_ttl")}</th>
                    <th>{t("blocked_ips_table_actions")}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredIPs.map((ip) => (
                    <tr key={ip.ip_address} className={getSeverityClass(ip.ttl_hours)}>
                      <td>
                        <span className={styles.ipBadge}>{ip.ip_address}</span>
                      </td>
                      <td>
                        <span className={`${styles.attemptsBadge} ${getAttemptsClass(ip.attempts)}`}>
                          {ip.attempts || t("blocked_ips_na")}
                        </span>
                      </td>
                      <td>
                        <Clock size={14} className={styles.inlineIcon} />
                        {ip.expires_in}
                      </td>
                      <td>{formatHours(ip.ttl_hours)}</td>
                      <td>
                        <button
                          onClick={() => {
                            setSelectedIP(ip.ip_address);
                            setShowUnblockModal(true);
                          }}
                          className={styles.btnUnblock}
                        >
                          <Shield size={14} />
                          {t("blocked_ips_unblock")}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className={styles.mobileCards}>
              {filteredIPs.map((ip) => (
                <div key={ip.ip_address} className={`${styles.card} ${getSeverityClass(ip.ttl_hours)}`}>
                  <div className={styles.cardHeader}>
                    <span className={styles.ipBadge}>{ip.ip_address}</span>
                    <span className={`${styles.attemptsBadge} ${getAttemptsClass(ip.attempts)}`}>
                      {ip.attempts || t("blocked_ips_na")} {t("blocked_ips_attempts_suffix")}
                    </span>
                  </div>
                  <div className={styles.cardBody}>
                    <div className={styles.cardRow}>
                      <span className={styles.label}>{t("blocked_ips_expires_in")}</span>
                      <span className={styles.value}>{ip.expires_in}</span>
                    </div>
                    <div className={styles.cardRow}>
                      <span className={styles.label}>{t("blocked_ips_ttl_label")}</span>
                      <span className={styles.value}>{formatNumber(ip.ttl_hours)} {t("blocked_ips_hours")}</span>
                    </div>
                  </div>
                  <div className={styles.cardFooter}>
                    <button
                      onClick={() => {
                        setSelectedIP(ip.ip_address);
                        setShowUnblockModal(true);
                      }}
                      className={styles.btnUnblockFull}
                    >
                      <Shield size={14} />
                      {t("blocked_ips_unblock")}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Unblock Confirmation Modal */}
        {showUnblockModal && selectedIP && (
          <Portal>
            <Modal
              isOpen={showUnblockModal}
              onClose={() => {
                setShowUnblockModal(false);
                setSelectedIP(null);
              }}
              title={t("blocked_ips_confirm_unblock_title")}
            >
              <div className={styles.modalContent}>
                <div className={styles.warningIcon}>
                  <AlertTriangle size={48} />
                </div>
                <p className={styles.modalMessage}>
                  {t("blocked_ips_confirm_unblock_msg")}
                </p>
                <div className={styles.ipHighlight}>{selectedIP}</div>
                <p className={styles.modalNote}>
                  {t("blocked_ips_confirm_unblock_note")}
                </p>
                <div className={styles.modalActions}>
                  <button
                    onClick={() => {
                      setShowUnblockModal(false);
                      setSelectedIP(null);
                    }}
                    className={styles.btnSecondary}
                  >
                    {t("cancel")}
                  </button>
                  <button
                    onClick={() => handleUnblock(selectedIP)}
                    className={styles.btnPrimary}
                  >
                    {t("blocked_ips_yes_unblock")}
                  </button>
                </div>
              </div>
            </Modal>
          </Portal>
        )}

        {/* Clear All Confirmation Modal */}
        {showClearAllModal && (
          <Portal>
            <Modal
              isOpen={showClearAllModal}
              onClose={() => {
                setShowClearAllModal(false);
                setConfirmText("");
              }}
              title={t("blocked_ips_dangerous_action")}
            >
              <div className={styles.modalContent}>
                <div className={styles.dangerIcon}>
                  <AlertTriangle size={48} />
                </div>
                <p className={styles.modalMessage}>
                  {t("blocked_ips_clear_all_warning").replace("{count}", blockedIPs.length.toString())}
                </p>
                <p className={styles.modalWarning}>{t("blocked_ips_clear_all_consequences")}</p>
                <ul className={styles.warningList}>
                  <li>{t("blocked_ips_clear_all_item1")}</li>
                  <li>{t("blocked_ips_clear_all_item2")}</li>
                  <li>{t("blocked_ips_clear_all_item3")}</li>
                </ul>
                <p className={styles.modalNote}>
                  {t("blocked_ips_clear_all_caution")}
                </p>
                <div className={styles.confirmInputGroup}>
                  <label htmlFor="confirm-text">
                    {t("blocked_ips_type_to_confirm").replace("{text}", "CLEAR ALL")}
                  </label>
                  <input
                    id="confirm-text"
                    type="text"
                    value={confirmText}
                    onChange={(e) => setConfirmText(e.target.value)}
                    placeholder={t("blocked_ips_confirm_placeholder")}
                    className={styles.confirmInput}
                    autoFocus
                  />
                </div>
                <div className={styles.modalActions}>
                  <button
                    onClick={() => {
                      setShowClearAllModal(false);
                      setConfirmText("");
                    }}
                    className={styles.btnSecondary}
                  >
                    {t("cancel")}
                  </button>
                  <button
                    onClick={handleClearAll}
                    disabled={confirmText.toLowerCase() !== "clear all"}
                    className={styles.btnDanger}
                  >
                    {t("blocked_ips_clear_all")} {blockedIPs.length} IPs
                  </button>
                </div>
              </div>
            </Modal>
          </Portal>
        )}
      </PageContainer>
    </AuthGuard>
  );
};

export default BlockedIPsPage;

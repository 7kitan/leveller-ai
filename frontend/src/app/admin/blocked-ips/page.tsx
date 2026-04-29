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
      toast.error(err.response?.data?.detail || "Failed to load blocked IPs");
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
    toast.success("Refreshed successfully");
  };

  const handleUnblock = async (ip: string) => {
    try {
      await api.post("/admin/unblock-ip", { ip_address: ip });
      toast.success(`IP ${ip} has been unblocked`);
      setShowUnblockModal(false);
      setSelectedIP(null);
      fetchBlockedIPs();
    } catch (err: any) {
      console.error("Unblock error:", err);
      toast.error(err.response?.data?.detail || "Failed to unblock IP");
    }
  };

  const handleClearAll = async () => {
    if (confirmText.toLowerCase() !== "clear all") {
      toast.error("Please type 'CLEAR ALL' to confirm");
      return;
    }

    try {
      const res = await api.delete("/admin/blocked-ips");
      toast.success(res.data.message || "All IPs cleared");
      setShowClearAllModal(false);
      setConfirmText("");
      fetchBlockedIPs();
    } catch (err: any) {
      console.error("Clear all error:", err);
      toast.error(err.response?.data?.detail || "Failed to clear all IPs");
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
          title={<><Shield className={styles.headerIcon} /> Blocked IP Management</>}
          subtitle="Manage and monitor blocked IP addresses"
        />

        {/* Actions Bar */}
        <div className={styles.actionsBar}>
          <div className={styles.searchBox}>
            <Search className={styles.searchIcon} size={18} />
            <input
              type="text"
              placeholder="Search IP address..."
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
              Refresh
            </button>
            <button
              onClick={() => setShowClearAllModal(true)}
              disabled={blockedIPs.length === 0}
              className={styles.btnDanger}
            >
              <Trash2 size={16} />
              Clear All
            </button>
          </div>
        </div>

        {/* Stats Bar */}
        <div className={styles.statsBar}>
          <div className={styles.statItem}>
            <Ban size={18} />
            <span className={styles.statLabel}>Total Blocked:</span>
            <span className={styles.statValue}>{blockedIPs.length}</span>
          </div>
          <div className={styles.statItem}>
            <Search size={18} />
            <span className={styles.statLabel}>Showing:</span>
            <span className={styles.statValue}>{filteredIPs.length}</span>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className={styles.loadingState}>
            <div className={styles.spinner}></div>
            <p>Loading blocked IPs...</p>
          </div>
        ) : filteredIPs.length === 0 ? (
          <div className={styles.emptyState}>
            <Shield size={64} className={styles.emptyIcon} />
            <h3>No Blocked IPs</h3>
            <p>
              {searchTerm
                ? "No IPs match your search"
                : "No IP addresses are currently blocked"}
            </p>
          </div>
        ) : (
          <>
            {/* Desktop Table */}
            <div className={styles.tableContainer}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>IP Address</th>
                    <th>Failed Attempts</th>
                    <th>Time Remaining</th>
                    <th>TTL (Hours)</th>
                    <th>Actions</th>
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
                          {ip.attempts || "N/A"}
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
                          Unblock
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
                      {ip.attempts || "N/A"} attempts
                    </span>
                  </div>
                  <div className={styles.cardBody}>
                    <div className={styles.cardRow}>
                      <span className={styles.label}>Expires in:</span>
                      <span className={styles.value}>{ip.expires_in}</span>
                    </div>
                    <div className={styles.cardRow}>
                      <span className={styles.label}>TTL:</span>
                      <span className={styles.value}>{formatNumber(ip.ttl_hours)} hours</span>
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
                      Unblock
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
              title="Confirm Unblock"
            >
              <div className={styles.modalContent}>
                <div className={styles.warningIcon}>
                  <AlertTriangle size={48} />
                </div>
                <p className={styles.modalMessage}>
                  Are you sure you want to unblock this IP address?
                </p>
                <div className={styles.ipHighlight}>{selectedIP}</div>
                <p className={styles.modalNote}>
                  This will immediately allow login attempts from this IP address.
                </p>
                <div className={styles.modalActions}>
                  <button
                    onClick={() => {
                      setShowUnblockModal(false);
                      setSelectedIP(null);
                    }}
                    className={styles.btnSecondary}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleUnblock(selectedIP)}
                    className={styles.btnPrimary}
                  >
                    Yes, Unblock
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
              title="⚠️ Dangerous Action"
            >
              <div className={styles.modalContent}>
                <div className={styles.dangerIcon}>
                  <AlertTriangle size={48} />
                </div>
                <p className={styles.modalMessage}>
                  You are about to unblock <strong>{blockedIPs.length} IP addresses</strong>.
                </p>
                <p className={styles.modalWarning}>This action will:</p>
                <ul className={styles.warningList}>
                  <li>Remove all IP lockouts immediately</li>
                  <li>Clear all failed login attempt counters</li>
                  <li>Allow previously blocked IPs to attempt login again</li>
                </ul>
                <p className={styles.modalNote}>
                  This action cannot be undone. Use with extreme caution in production.
                </p>
                <div className={styles.confirmInputGroup}>
                  <label htmlFor="confirm-text">
                    Type <code>CLEAR ALL</code> to confirm:
                  </label>
                  <input
                    id="confirm-text"
                    type="text"
                    value={confirmText}
                    onChange={(e) => setConfirmText(e.target.value)}
                    placeholder="Type here..."
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
                    Cancel
                  </button>
                  <button
                    onClick={handleClearAll}
                    disabled={confirmText.toLowerCase() !== "clear all"}
                    className={styles.btnDanger}
                  >
                    Clear All {blockedIPs.length} IPs
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

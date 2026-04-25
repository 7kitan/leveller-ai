"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useLanguage } from "@/context/LanguageContext";
import api from "@/lib/api";
import {
  Zap,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ChevronLeft,
  Search,
  Briefcase,
  FileText,
  Loader2,
  Plus,
  X,
  Target,
} from "lucide-react";
import { cn } from "@/lib/utils";
import styles from "./user-analysis.module.css";
import { AnimatePresence, motion } from "framer-motion";
import Modal from "@/components/shared/Modal";
import PageHeader from "@/components/common/PageHeader";
import PageContainer from "@/components/common/PageContainer";

const POLLING_INTERVAL = 5000;

/* -- Types --------------------------------------------------------------- */
interface CVOption {
  id: string;
  full_name: string | null;
  status: string;
  created_at: string;
}

interface JobOption {
  id: string;
  title_raw: string;
  company_name: string | null;
  location: string | null;
  salary_min: number | null;
}

type Phase = "setup" | "processing" | "completed" | "failed";

/* -- Step labels -------------------------------------------------------- */
const PIPELINE_STEPS = [
  { label: "step_extract", key: "extract" },
  { label: "step_analyze", key: "analyze" },
  { label: "step_courses", key: "courses" },
  { label: "step_roadmap", key: "roadmap" },
];

function stepProgress(stepIdx: number): number {
  return Math.min(25 + stepIdx * 25, 100);
}

function detectStep(pct: number): number {
  if (pct < 25) return 0;
  if (pct < 50) return 1;
  if (pct < 75) return 2;
  return 3;
}

function AnalysisPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { token } = useAuth();
  const { language, t } = useLanguage();
  
  const initialJobId = searchParams.get("job_id");
  const initialJobTitle = searchParams.get("job_title");

  /* -- CV list -------------------------------------------------------- */
  const [cvs, setCvs] = useState<CVOption[]>([]);
  const [selectedCvId, setSelectedCvId] = useState<string>("");

  /* -- JD input mode -------------------------------------------------- */
  const [jdMode, setJdMode] = useState<"select" | "paste">("select");
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [selectedJob, setSelectedJob] = useState<JobOption | null>(null);
  const [pastedJdText, setPastedJdText] = useState<string>("");
  const [jobSearch, setJobSearch] = useState<string>("");
  const [jobResults, setJobResults] = useState<JobOption[]>([]);
  const [searchingJobs, setSearchingJobs] = useState(false);

  /* -- Validation & submission ---------------------------------------- */
  const [error, setError] = useState<string>("");

  /* -- Pipeline state --------------------------------------------------- */
  const [phase, setPhase] = useState<Phase>("setup");
  const [taskId, setTaskId] = useState<string>("");
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [processMessage, setProcessMessage] = useState<string>(t("init_message"));
  const [spamIndex, setSpamIndex] = useState(0);
  const [processingTime, setProcessingTime] = useState(0);
  const [showTimeoutOverlay, setShowTimeoutOverlay] = useState(false);

  const spamMessages = [
    t("analysis_msg_1"),
    t("analysis_msg_2"),
    t("analysis_msg_3"),
    t("analysis_msg_4"),
    t("analysis_msg_5"),
    t("analysis_msg_6"),
    t("analysis_msg_7"),
    t("analysis_msg_8"),
  ];

  /* -- Handle URL Params ---------------------------------------------- */
  useEffect(() => {
    if (initialJobId) {
      setSelectedJobId(initialJobId);
      setJdMode("select");

      if (initialJobTitle) {
        setSelectedJob({
          id: initialJobId,
          title_raw: initialJobTitle,
          company_name: null,
          location: null,
          salary_min: null
        });
      } else {
        // Fetch job info if title is missing
        api.get(`/jd/${initialJobId}`)
          .then(r => {
            setSelectedJob(r.data);
          })
          .catch(err => {
            console.error("[ANALYSIS] Failed to fetch job info from URL:", err);
            // Fallback: stay in select mode but empty
            setSelectedJobId("");
          });
      }
    }
  }, [initialJobId, initialJobTitle]);

  /* -- Auto Run Integration -- */
  useEffect(() => {
    const autoRun = searchParams.get("auto_run") === "true";
    if (autoRun && phase === "setup" && selectedCvId && selectedJobId) {
      console.log("[ANALYSIS] Auto-run triggered (forcing recompute)");
      startAnalysis(true);
    }
  }, [selectedCvId, selectedJobId, phase]);

  /* -- Load CVs ------------------------------------------------------- */
  useEffect(() => {
    if (!token) return;
    api
      .get("/cv/list")
      .then((r) => {
        const done = (r.data as CVOption[]).filter((c) => c.status === "completed");
        setCvs(done);
        if (done.length > 0) setSelectedCvId(done[0].id);
      })
      .catch((e) => console.error("[ANALYSIS] load CVs:", e));
  }, [token]);

  /* -- Search jobs when switching to select mode --------------------- */
  useEffect(() => {
    if (jdMode !== "select" || !token) return;
    const t = setTimeout(() => searchJobs(jobSearch), 400);
    return () => clearTimeout(t);
  }, [jobSearch, jdMode, token]);

  const searchJobs = (q: string) => {
    if (!token) return;
    setSearchingJobs(true);
    api
      .get("/jd/search", {
        params: { q: q || undefined, limit: 10 },
      })
      .then((r) => setJobResults(r.data.items as JobOption[]))
      .catch(() => setJobResults([]))
      .finally(() => setSearchingJobs(false));
  };

  const selectJob = (job: JobOption) => {
    setSelectedJob(job);
    setSelectedJobId(job.id);
    setJobSearch("");
    setJobResults([]);
  };

  const clearJob = () => {
    setSelectedJob(null);
    setSelectedJobId("");
  };

  /* -- Validate setup ------------------------------------------------ */
  const isValid =
    !!selectedCvId &&
    (jdMode === "paste" ? pastedJdText.trim().length > 20 : !!selectedJobId);

  /* -- Start analysis ------------------------------------------------ */
  const startAnalysis = async (force: boolean = false) => {
    setError("");
    if (!isValid) {
      setError(t("analysis_missing_inputs"));
      return;
    }

    setPhase("processing");
    setProgress(0);
    setCurrentStep(0);
    setProcessingTime(0);
    setShowTimeoutOverlay(false);
    setNotified(false);

    console.log(
      `[ANALYSIS] Starting — cv_id=${selectedCvId} | jd_mode=${jdMode} | force=${force} | ` +
        (jdMode === "paste"
          ? `jd_text length=${pastedJdText.length}`
          : `job_id=${selectedJobId}`)
    );

    try {
      const payload: Record<string, unknown> = { 
        cv_id: selectedCvId,
        lang: language,
        force: force
      };
      if (jdMode === "paste") {
        payload.jd_text = pastedJdText;
      } else {
        payload.job_id = selectedJobId;
      }

      const resp = await api.post("/analysis/gap", payload);

      const tid = resp.data.task_id as string;
      setTaskId(tid);
      console.log(`[ANALYSIS] Task dispatched — task_id=${tid}`);
      pollStatus(tid);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message;
      console.error(`[ANALYSIS] Start failed: ${detail}`);
      setError(String(detail));
      setPhase("failed");
    }
  };

  /* -- Poll Celery task ------------------------------------------- */
  const pollStatus = (tid: string) => {
    const interval = setInterval(async () => {
      try {
        const resp = await api.get(`/analysis/status/${tid}`);
        const { status, result } = resp.data as { status: string; result?: unknown };
        console.log(`[ANALYSIS] poll — status=${status}`);

        if (status === "completed") {
          clearInterval(interval);
          setProgress(100);
          setCurrentStep(3);
          try {
            sessionStorage.setItem("gap_analysis_result", JSON.stringify(result));
          } catch {}
          console.log(`[ANALYSIS] ✅ DONE — redirecting to /user/recommend`);
          setPhase("completed");
          setTimeout(() => router.push("/user/recommend"), 1200);
          return;
        }

        if (status === "failed") {
          clearInterval(interval);
          setError(String((result as { error?: string })?.error || t("analysis_failed")));
          setPhase("failed");
          return;
        }

        // Capture granular progress from API
        const { progress: apiProgress, message, partial_result } = resp.data as { 
          progress?: number; 
          message?: string; 
          partial_result?: any 
        };

        if (apiProgress !== undefined) {
          setProgress(apiProgress);
          setCurrentStep(detectStep(apiProgress));
        } else {
            // Fallback to simulation if no granular progress yet
            setProgress((p) => {
              const next = p + Math.floor(Math.random() * 3) + 1;
              const clamped = Math.min(next, 94);
              setCurrentStep(detectStep(clamped));
              return clamped;
            });
        }
        
        if (message) {
            setProcessMessage(message);
        }

        // --- PROGRESSIVE LOADING: Redirect early if gaps are ready ---
        if (partial_result && partial_result.node === "gap_analysis") {
            console.log("[ANALYSIS] Gaps are ready! Redirecting early to /user/recommend for progressive loading.");
            try {
              sessionStorage.setItem("gap_analysis_partial", JSON.stringify(partial_result));
            } catch {}
            
            clearInterval(interval);
            setPhase("completed");
            router.push(`/user/recommend?task_id=${tid}`);
            return;
        }
      } catch (err) {
        console.error(`[ANALYSIS] poll error:`, err);
      }
    }, POLLING_INTERVAL);

    // Dynamic Spam Message Loop
    const spamInterval = setInterval(() => {
      setSpamIndex(prev => (prev + 1) % spamMessages.length);
    }, 4500);

    // Timeout Tracker
    const timerInterval = setInterval(() => {
      setProcessingTime(prev => {
        const next = prev + 1;
        if (next >= 45 && !showTimeoutOverlay) {
          setShowTimeoutOverlay(true);
        }
        return next;
      });
    }, 1000);

    return () => {
      clearInterval(interval);
      clearInterval(spamInterval);
      clearInterval(timerInterval);
    };
  };

  /* -- Point 4: Graceful Cancellation ----------------------------- */
  const handleCancel = async () => {
    if (!taskId || !token) return;
    try {
      await api.delete(`/analysis/status/${taskId}`);
      console.log(`[ANALYSIS] Revoke request sent — task_id=${taskId}`);
      setError(t("analysis_cancelled"));
      setPhase("setup");
    } catch (err) {
      console.error("[ANALYSIS] Revoke failed:", err);
    }
  };

  /* -- Point 2: Leave & Return (Notification) --------------------- */
  const [notified, setNotified] = useState(false);
  const handleNotify = async () => {
    if (!taskId || !token) return;
    try {
      await api.post(`/analysis/notify/${taskId}`, {});
      setNotified(true);
    } catch (err) {
      console.error("[ANALYSIS] Notify failed:", err);
    }
  };

  /* -- Retry / back ------------------------------------------------ */
  const handleRetry = () => {
    setPhase("setup");
    setProgress(0);
    setTaskId("");
    setError("");
  };

  /* ===================================================================
     PHASE: SETUP - chọn JD + CV rồi bắt đầu
  =================================================================== */
  if (phase === "setup" || phase === "failed") {
    return (
      <PageContainer>
        <PageHeader
          title={t("analysis_title")}
          subtitle={t("analysis_subtitle")}
        >
          <div className={styles.badge}>
            <Sparkles size={12} />
            <span className={styles.badgeLabel}>{t("analysis_engine_badge")}</span>
          </div>
        </PageHeader>

        <div className={styles.setupCard}>
          {/* -- JD Section ---------------------------------------- */}
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <Target size={18} className={styles.sectionIcon} />
              <div>
                <div className={styles.sectionTitle}>{t("jd_section_title")}</div>
                <div className={styles.sectionSub}>{t("jd_section_sub")}</div>
              </div>
            </div>

            {/* JD Mode Tabs */}
            <div className={styles.jdModeTabs}>
              <button
                className={cn(styles.jdModeTab, jdMode === "select" && styles.jdModeTabActive)}
                onClick={() => { setJdMode("select"); clearJob(); setPastedJdText(""); }}
              >
                <Search size={14} />
                {t("jd_mode_select")}
              </button>
              <button
                className={cn(styles.jdModeTab, jdMode === "paste" && styles.jdModeTabActive)}
                onClick={() => { setJdMode("paste"); setSelectedJobId(""); setSelectedJob(null); setJobResults([]); }}
              >
                <FileText size={14} />
                {t("jd_mode_paste")}
              </button>
            </div>

            {/* -- Mode: Select from list ---------------------------- */}
            {jdMode === "select" && (
              <div className={styles.jdSelectSection}>
                {selectedJob ? (
                  <div className={styles.selectedJobCard}>
                    <div className={styles.selectedJobInfo}>
                      <div className={styles.selectedJobTitle}>{selectedJob.title_raw}</div>
                      <div className={styles.selectedJobMeta}>
                        {selectedJob.company_name && <span>{selectedJob.company_name}</span>}
                        {selectedJob.location && <span>· {selectedJob.location}</span>}
                        {selectedJob.salary_min && (
                          <span>· ${selectedJob.salary_min.toLocaleString()}{t("per_year")}</span>
                        )}
                      </div>
                    </div>
                    <button onClick={clearJob} className={styles.clearJobBtn}>
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div className={styles.jobSearchWrap}>
                    <div className={styles.jobSearchInput}>
                      <Search size={16} className={styles.jobSearchIcon} />
                        <input
                          type="text"
                          placeholder={t("jd_search_placeholder")}
                          value={jobSearch}
                          onChange={(e) => setJobSearch(e.target.value)}
                          className={styles.jobSearchField}
                        />
                    </div>

                    {jobResults.length > 0 && (
                      <div className={styles.jobDropdown}>
                        {jobResults.map((job) => (
                          <button
                            key={job.id}
                            onClick={() => selectJob(job)}
                            className={styles.jobDropdownItem}
                          >
                            <Briefcase size={14} className={styles.jobDropIcon} />
                            <div>
                              <div className={styles.jobDropTitle}>{job.title_raw}</div>
                              <div className={styles.jobDropMeta}>
                                {job.company_name || "—"}
                                {job.location ? ` · ${job.location}` : ""}
                              </div>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}

                    {searchingJobs && (
                      <div className={styles.jobSearching}>{t("loading")}</div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* -- Mode: Paste JD text ------------------------------ */}
            {jdMode === "paste" && (
              <div className={styles.jdPasteSection}>
                <textarea
                  rows={8}
                  placeholder={t("jd_paste_placeholder")}
                  value={pastedJdText}
                  onChange={(e) => setPastedJdText(e.target.value)}
                  className={styles.jdTextarea}
                  maxLength={50000}
                />
                <div className={styles.charCount}>
                  {pastedJdText.length} {t("char_count")}
                  {pastedJdText.length < 20 && pastedJdText.length > 0 && ` · ${t("min_char_required")}`}
                </div>
              </div>
            )}
          </div>

          {/* -- CV Section ---------------------------------------- */}
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <FileText size={18} className={styles.sectionIcon} />
              <div>
                <div className={styles.sectionTitle}>{t("cv_section_title")}</div>
                <div className={styles.sectionSub}>{t("cv_section_sub")}</div>
              </div>
            </div>

            {cvs.length === 0 ? (
              <div className={styles.noCvBox}>
                <AlertCircle size={16} />
                {t("no_cv_msg")}
                <a href="/user/cv" className={styles.uploadLink}>
                  {t("upload_cv_now")}
                </a>
              </div>
            ) : (
              <div className={styles.cvGrid}>
                {cvs.map((cv) => (
                  <button
                    key={cv.id}
                    onClick={() => setSelectedCvId(cv.id)}
                    className={cn(
                      styles.cvOption,
                      selectedCvId === cv.id && styles.cvOptionActive
                    )}
                  >
                    <div className={cn(styles.cvRadio, selectedCvId === cv.id && styles.cvRadioActive)} />
                    <div className={styles.cvInfo}>
                      <div className={styles.cvName}>
                        {cv.full_name || `CV ${cv.id.slice(0, 8)}`}
                      </div>
                      <div className={styles.cvDate}>
                        {t("uploaded_at")} {new Date(cv.created_at).toLocaleDateString(language === 'vi' ? "vi-VN" : "en-US")}
                      </div>
                    </div>
                    {selectedCvId === cv.id && (
                      <CheckCircle2 size={18} className={styles.cvCheck} />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* -- Error ---------------------------------------- */}
          {error && (
            <div className={styles.errorBox}>
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          {/* -- Actions ---------------------------------- */}
          <div className={styles.setupActions}>
            <button
              onClick={() => router.push("/user/jobs")}
              className={styles.backBtn}
            >
              <ChevronLeft size={16} />
              {t("back")}
            </button>
            <button
              onClick={() => startAnalysis(false)}
              disabled={!isValid}
              className={styles.startBtn}
            >
              <Zap size={16} />
              {t("start_analysis")}
            </button>
          </div>
        </div>
      </PageContainer>
    );
  }

  /* ===================================================================
     PHASE: PROCESSING
  =================================================================== */
  if (phase === "processing") {
    return (
      <PageContainer>
        <PageHeader 
          title="CAREER GENOME."
          subtitle={t("analysis_engine_badge")}
        />

        <div className={styles.processingCard}>
          <div className={styles.stepsList}>
            {PIPELINE_STEPS.map((s, i) => (
              <div
                key={s.key}
                className={cn(
                  styles.stepItem,
                  currentStep >= i && styles.stepItemActive,
                  currentStep > i && styles.stepItemDone
                )}
              >
                <div
                  className={cn(
                    styles.stepDot,
                    currentStep > i && styles.stepDotDone,
                    currentStep === i && styles.stepDotActive
                  )}
                />
                <span className={styles.stepLabel}>{t(s.label as any)}</span>
                {currentStep > i && (
                  <CheckCircle2 size={14} className={styles.stepCheck} />
                )}
              </div>
            ))}
          </div>

          <div className={styles.progressBarWrap}>
            <div
              className={styles.progressFill}
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className={styles.progressPct}>{progress}%</div>
          
          <div className={styles.granularMessage}>
            <Loader2 size={16} className={styles.spinIcon} />
            <AnimatePresence mode="wait">
              <motion.span
                key={spamIndex}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.5 }}
                className={styles.spamText}
              >
                {spamMessages[spamIndex]}
              </motion.span>
            </AnimatePresence>
          </div>
          
          <div className={styles.backendMessage}>
             {processMessage}
          </div>

          <p className={styles.processingSub}>
            {t("task_id_label")}: <code>{taskId}</code> | Time: {processingTime}s
          </p>

          {/* Timeout Overlay Dialog */}
          <Modal
            isOpen={showTimeoutOverlay && !notified}
            onClose={() => setShowTimeoutOverlay(false)}
            title={t("analysis_timeout_title")}
            maxWidth="550px"
          >
            <div className={styles.timeoutModalContent}>
              <div className={styles.timeoutIconBox}>
                <AlertCircle size={32} />
              </div>
              <p className={styles.timeoutDescription}>
                {t("analysis_timeout_desc")}
              </p>
              <div className={styles.timeoutActionsRow}>
                 <button onClick={handleNotify} className={styles.timeoutNotifyBtn}>
                   <Zap size={16} />
                   {t("analysis_notify_and_back")}
                 </button>
                 <button onClick={() => setShowTimeoutOverlay(false)} className={styles.timeoutContinueBtn}>
                   {t("analysis_continue_waiting")}
                 </button>
              </div>
            </div>
          </Modal>

          <div className={styles.asyncActions}>
            <button 
              onClick={handleNotify} 
              disabled={notified}
              className={cn(styles.notifyBtn, notified && styles.notifyBtnDone)}
            >
              {notified ? <CheckCircle2 size={16} /> : <Zap size={16} />}
              {notified ? t("will_notify") : t("notify_me")}
            </button>
            <button onClick={handleCancel} className={styles.cancelBtn}>
              <X size={16} />
              {t("stop_analysis")}
            </button>
          </div>

          <div className={styles.leaveHint}>
            <p>{t("processing_hint")}</p>
          </div>
        </div>
      </PageContainer>
    );
  }

  /* ===================================================================
     PHASE: COMPLETED
  =================================================================== */
  return (
    <PageContainer>
      <div className={styles.doneCard}>
        <CheckCircle2 size={56} className={styles.doneIcon} />
        <h1 className={styles.doneTitle}>
          {t("analysis_done")}
        </h1>
        <p className={styles.doneSub}>{t("redirecting_recommend")}</p>
      </div>
    </PageContainer>
  );
}

export default function AnalysisPage() {
  const { t } = useLanguage();
  return (
    <Suspense fallback={<div>{t("loading")}</div>}>
      <AnalysisPageContent />
    </Suspense>
  );
}



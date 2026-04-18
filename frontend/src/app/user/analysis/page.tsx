"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
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
  { label: "Bóc tách JD & CV", key: "extract" },
  { label: "Phân tích Gap", key: "analyze" },
  { label: "Tìm khóa học", key: "courses" },
  { label: "Xây lộ trình", key: "roadmap" },
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

  /* -- Handle URL Params ---------------------------------------------- */
  useEffect(() => {
    if (initialJobId && initialJobTitle) {
      setSelectedJobId(initialJobId);
      setSelectedJob({
        id: initialJobId,
        title_raw: initialJobTitle,
        company_name: null,
        location: null,
        salary_min: null
      });
      setJdMode("select");
    }
  }, [initialJobId, initialJobTitle]);

  /* -- Load CVs ------------------------------------------------------- */
  useEffect(() => {
    if (!token) return;
    axios
      .get("/api/cv/list", { headers: { Authorization: `Bearer ${token}` } })
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
    axios
      .get("/api/jd/search", {
        params: { q: q || undefined, limit: 10 },
        headers: { Authorization: `Bearer ${token}` },
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
  const startAnalysis = async () => {
    setError("");
    if (!isValid) {
      setError("Vui lòng chọn đủ CV và JD để phân tích.");
      return;
    }

    setPhase("processing");
    setProgress(0);
    setCurrentStep(0);

    console.log(
      `[ANALYSIS] Starting — cv_id=${selectedCvId} | jd_mode=${jdMode} | ` +
        (jdMode === "paste"
          ? `jd_text length=${pastedJdText.length}`
          : `job_id=${selectedJobId}`)
    );

    try {
      const payload: Record<string, unknown> = { cv_id: selectedCvId };
      if (jdMode === "paste") {
        payload.jd_text = pastedJdText;
      } else {
        payload.job_id = selectedJobId;
      }

      const resp = await axios.post("/api/analysis/gap", payload, {
        headers: { Authorization: `Bearer ${token}` },
      });

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
        const resp = await axios.get(`/api/analysis/status/${tid}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
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
          setError(String((result as { error?: string })?.error || "Phân tích thất bại."));
          setPhase("failed");
          return;
        }

        // Simulate step progression while processing
        setProgress((p) => {
          const next = p + Math.floor(Math.random() * 6) + 2;
          const clamped = Math.min(next, 94);
          setCurrentStep(detectStep(clamped));
          return clamped;
        });
      } catch (err) {
        console.error(`[ANALYSIS] poll error:`, err);
      }
    }, 2500);
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
      <div className={styles.pageRoot}>
        <div className={styles.glowTop} />
        <div className={styles.glowBottom} />
        <div className={styles.textureOverlay} />

        <div className={styles.setupCard}>
          {/* Header */}
          <div className={styles.setupHeader}>
            <div className={styles.badge}>
              <Sparkles size={12} />
              <span className={styles.badgeLabel}>Career Genome Engine v2</span>
            </div>
            <h1 className={styles.setupTitle}>
              GAP <span className={styles.gradientText}>ANALYSIS</span>
            </h1>
            <p className={styles.setupSub}>
              Chọn JD và CV để AI phân tích khoảng cách kỹ năng và đề xuất lộ trình học tập.
            </p>
          </div>

          {/* -- JD Section ---------------------------------------- */}
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <Target size={18} className={styles.sectionIcon} />
              <div>
                <div className={styles.sectionTitle}>Mô tả công việc (JD)</div>
                <div className={styles.sectionSub}>Chọn 1 trong 2 cách để xác định JD mục tiêu</div>
              </div>
            </div>

            {/* JD Mode Tabs */}
            <div className={styles.jdModeTabs}>
              <button
                className={cn(styles.jdModeTab, jdMode === "select" && styles.jdModeTabActive)}
                onClick={() => { setJdMode("select"); clearJob(); setPastedJdText(""); }}
              >
                <Search size={14} />
                Chọn từ danh sách JD
              </button>
              <button
                className={cn(styles.jdModeTab, jdMode === "paste" && styles.jdModeTabActive)}
                onClick={() => { setJdMode("paste"); setSelectedJobId(""); setSelectedJob(null); setJobResults([]); }}
              >
                <FileText size={14} />
                Dán JD trực tiếp
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
                          <span>· ${selectedJob.salary_min.toLocaleString()}/năm</span>
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
                        placeholder="Tìm kiếm vị trí JD..."
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
                      <div className={styles.jobSearching}>Đang tìm...</div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* -- Mode: Paste JD text ------------------------------ */}
            {jdMode === "paste" && (
              <div className={styles.jdPasteSection}>
                <textarea
                  className={styles.jdTextarea}
                  placeholder={"Dán mô tả công việc (JD) vào đây...\n\nVí dụ: We are hiring a Senior Python Engineer with 5+ years of experience in Django, PostgreSQL, Docker..."}
                  value={pastedJdText}
                  onChange={(e) => setPastedJdText(e.target.value)}
                  rows={8}
                />
                <div className={styles.charCount}>
                  {pastedJdText.length} ký tự
                  {pastedJdText.length < 20 && pastedJdText.length > 0 && " · Cần ít nhất 20 ký tự"}
                </div>
              </div>
            )}
          </div>

          {/* -- CV Section ---------------------------------------- */}
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <FileText size={18} className={styles.sectionIcon} />
              <div>
                <div className={styles.sectionTitle}>Hồ sơ CV của bạn</div>
                <div className={styles.sectionSub}>Chọn CV đã phân tích để so sánh với JD</div>
              </div>
            </div>

            {cvs.length === 0 ? (
              <div className={styles.noCvBox}>
                <AlertCircle size={16} />
                Bạn chưa có CV nào đã phân tích.
                <a href="/user/cv" className={styles.uploadLink}>
                  Upload CV ngay
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
                        Uploaded {new Date(cv.created_at).toLocaleDateString("vi-VN")}
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
              Quay lại
            </button>
            <button
              onClick={startAnalysis}
              disabled={!isValid}
              className={styles.startBtn}
            >
              <Zap size={16} />
              BẮT ĐẦU PHÂN TÍCH GAP
            </button>
          </div>
        </div>
      </div>
    );
  }

  /* ===================================================================
     PHASE: PROCESSING
  =================================================================== */
  if (phase === "processing") {
    return (
      <div className={styles.pageRoot}>
        <div className={styles.glowTop} />
        <div className={styles.glowBottom} />
        <div className={styles.textureOverlay} />

        <div className={styles.processingCard}>
          <div className={styles.processingBadge}>
            <Sparkles size={12} />
            <span>Career Genome Engine v2</span>
          </div>
          <h1 className={styles.processingTitle}>
            CAREER <span className={styles.gradientText}>GENOME.</span>
          </h1>

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
                <span className={styles.stepLabel}>{s.label}</span>
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

          <p className={styles.processingSub}>
            Task ID: <code>{taskId}</code>
          </p>
        </div>
      </div>
    );
  }

  /* ===================================================================
     PHASE: COMPLETED
  =================================================================== */
  return (
    <div className={styles.pageRoot}>
      <div className={styles.glowTop} />
      <div className={styles.glowBottom} />
      <div className={styles.doneCard}>
        <CheckCircle2 size={56} className={styles.doneIcon} />
        <h1 className={styles.doneTitle}>
          PHÂN TÍCH{" "}
          <span className={styles.gradientText}>HOÀN TẤT!</span>
        </h1>
        <p className={styles.doneSub}>Đang chuyển sang trang đề xuất...</p>
      </div>
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<div>Đang tải trình điều khiển phân tích...</div>}>
      <AnalysisPageContent />
    </Suspense>
  );
}

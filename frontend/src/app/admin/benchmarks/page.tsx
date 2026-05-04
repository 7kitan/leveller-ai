"use client";

import { useState, useEffect } from "react";
import { useAlert } from "@/context/AlertContext";
import Modal from "@/components/shared/Modal";
import api from "@/lib/api";
import styles from "./benchmarks.module.css";
import { 
  Settings, 
  BarChart3, 
  Play, 
  Clock, 
  Info, 
  Plus, 
  Trash2, 
  Eye, 
  Download, 
  ChevronRight, 
  ChevronDown,
  Activity,
  Edit,
  Zap,
  Layers,
  Search,
  Upload,
  FileText,
  X,
  CheckCircle2,
  AlertCircle,
  FileUp,
  Database
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface TestSet {
  id: string;
  name: string;
  description: string;
  flow_type: string;
  is_active: boolean;
  created_at: string;
}

interface BenchmarkSession {
  id: string;
  test_set_id: string;
  model_config: any;
  status: string;
  overall_score: number | null;
  total_latency_ms: number | null;
  total_tokens: number | null;
  created_at: string;
  completed_at: string | null;
}

interface BenchmarkResult {
  id: string;
  test_case_id: string;
  score: number;
  metrics: any;
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  status: string;
  error_message: string | null;
}

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
}

interface CV {
  id: string;
  full_name: string;
  user_email: string;
  status: string;
  created_at: string;
  file_url: string;
}

interface Job {
  id: string;
  title_raw: string;
  company_name: string;
  status: string;
  created_at: string;
}

interface EnsembleJudge {
  model: string;
  weight: number;
}

const FLOW_TYPES = [
  { key: "cv_parsing_v3", label: "CV Parsing v3" },
  { key: "jd_parsing", label: "JD Parsing" },
  { key: "gap_analysis_from_requirements", label: "Gap Analysis (from Requirements)" },
  { key: "gap_analysis_merged", label: "Gap Analysis (Merged)" },
  { key: "course_recommendation", label: "Course Recommendation" },
  { key: "full_cv_to_gap", label: "Full CV → Gap Analysis" },
];

const getFlowTypeLabel = (key: string) => {
  return FLOW_TYPES.find(f => f.key === key)?.label || key;
};

export default function BenchmarksPage() {
  const { showAlert, showSuccess, showError, confirm } = useAlert();
  
  // Tab state
  const [activeTab, setActiveTab] = useState<"run" | "quick" | "testsets" | "results">("run");
  
  // Data state
  const [testSets, setTestSets] = useState<TestSet[]>([]);
  const [sessions, setSessions] = useState<BenchmarkSession[]>([]);
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
  const [availableCVs, setAvailableCVs] = useState<CV[]>([]);
  const [availableJobs, setAvailableJobs] = useState<Job[]>([]);
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [sessionDetails, setSessionDetails] = useState<any>(null);
  
  // Helper function to extract error message
  const extractErrorMessage = (err: any): string => {
    if (typeof err === 'string') return err;
    
    // Handle FastAPI validation errors
    if (err.response?.data?.detail) {
      const detail = err.response.data.detail;
      if (Array.isArray(detail)) {
        return detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
      }
      if (typeof detail === 'string') return detail;
      return JSON.stringify(detail);
    }
    
    return err.message || 'An unknown error occurred';
  };
  
  // Run Benchmark Configuration
  const [selectedTestSet, setSelectedTestSet] = useState<string>("");
  const [parsingModel, setParsingModel] = useState("gpt-4o-mini");
  const [evaluationStrategy, setEvaluationStrategy] = useState("dual_judge");
  const [judgePrimary, setJudgePrimary] = useState("gpt-4o");
  const [judgeSecondary, setJudgeSecondary] = useState("claude-3-5-sonnet-20241022");
  const [aggregation, setAggregation] = useState("average");
  
  // Quick Benchmark Configuration
  const [quickCvId, setQuickCvId] = useState<string>("");
  const [quickJobId, setQuickJobId] = useState<string>("");
  const [quickFlowType, setQuickFlowType] = useState<string>("full_cv_to_gap");
  
  // Ensemble Configuration
  const [ensembleJudges, setEnsembleJudges] = useState<EnsembleJudge[]>([
    { model: "gpt-4o", weight: 0.5 },
    { model: "claude-3-5-sonnet-20241022", weight: 0.5 }
  ]);
  
  // Advanced Options
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [temperature, setTemperature] = useState(0.0);
  const [maxTokens, setMaxTokens] = useState(2000);

  // Test Set Management
  const [showCreateTestSet, setShowCreateTestSet] = useState(false);
  const [newTestSetName, setNewTestSetName] = useState("");
  const [newTestSetDescription, setNewTestSetDescription] = useState("");
  const [newTestSetFlowType, setNewTestSetFlowType] = useState("full_cv_to_gap");
  const [selectedTestSetForManagement, setSelectedTestSetForManagement] = useState<string | null>(null);
  const [testCases, setTestCases] = useState<any[]>([]);
  const [showAddTestCases, setShowAddTestCases] = useState(false);
  
  // Edit Test Case
  const [editingTestCase, setEditingTestCase] = useState<any>(null);
  const [showEditTestCase, setShowEditTestCase] = useState(false);
  const [editCvId, setEditCvId] = useState("");
  const [editJobId, setEditJobId] = useState("");
  const [editReferenceOutput, setEditReferenceOutput] = useState("");
  const [editMetadata, setEditMetadata] = useState("");
  
  // Edit Test Set
  const [showEditTestSet, setShowEditTestSet] = useState(false);
  const [editingTestSet, setEditingTestSet] = useState<any>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editFlowType, setEditFlowType] = useState("");
  const [editIsActive, setEditIsActive] = useState(true);
  
  // Test Case Management
  const [selectedCVsForBatch, setSelectedCVsForBatch] = useState<string[]>([]);
  const [selectedJobsForBatch, setSelectedJobsForBatch] = useState<string[]>([]);
  const [batchMode, setBatchMode] = useState<"all_combinations" | "paired">("all_combinations");
  
  // CV Upload
  const [uploadedCVFiles, setUploadedCVFiles] = useState<File[]>([]);
  const [uploadedCVIds, setUploadedCVIds] = useState<string[]>([]);
  const [cvSourceMode, setCvSourceMode] = useState<"existing" | "upload">("existing");
  
  // JD Management
  const [jdSourceMode, setJdSourceMode] = useState<"existing" | "paste">("existing");
  const [pastedJDText, setPastedJDText] = useState("");
  const [pastedJDTitle, setPastedJDTitle] = useState("");
  const [pastedJDId, setPastedJDId] = useState<string | null>(null);
  
  // Job Search & Pagination
  const [jobSearch, setJobSearch] = useState("");
  const [jobOffset, setJobOffset] = useState(0);
  const [jobTotal, setJobTotal] = useState(0);
  const [jobLimit] = useState(20);

  useEffect(() => {
    fetchTestSets();
    fetchSessions();
    fetchAvailableModels();
    fetchAvailableCVs();
    fetchAvailableJobs();
  }, []);

  const fetchTestSets = async () => {
    try {
      const response = await api.get("admin/benchmarks/test-sets");
      setTestSets(response.data);
    } catch (err: any) {
      setError(extractErrorMessage(err));
    }
  };

  const fetchSessions = async () => {
    try {
      const response = await api.get("admin/benchmarks/sessions");
      setSessions(response.data);
    } catch (err: any) {
      console.error("Failed to fetch sessions:", err);
    }
  };

  const fetchAvailableCVs = async () => {
    try {
      const response = await api.get("analysis/admin/cvs?limit=100");
      setAvailableCVs(response.data.items || []);
    } catch (err: any) {
      console.error("Failed to fetch CVs:", err);
    }
  };

  // Helper to group models by provider
  const getGroupedModels = () => {
    return availableModels.reduce((acc: any, model: any) => {
      const provider = model.provider.toUpperCase();
      if (!acc[provider]) acc[provider] = [];
      acc[provider].push(model);
      return acc;
    }, {});
  };

  const renderModelOptions = () => {
    if (availableModels.length === 0) {
      return (
        <>
          <optgroup label="OPENAI">
            <option value="gpt-4o">GPT-4o</option>
            <option value="gpt-4o-mini">GPT-4o Mini</option>
          </optgroup>
          <optgroup label="ANTHROPIC">
            <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
          </optgroup>
        </>
      );
    }

    const grouped = getGroupedModels();
    return Object.keys(grouped).map(provider => (
      <optgroup key={provider} label={provider}>
        {grouped[provider].map((model: any) => (
          <option key={model.id} value={model.id}>
            {model.name}
          </option>
        ))}
      </optgroup>
    ));
  };

  const fetchAvailableModels = async () => {
    try {
      const response = await api.get("admin/ai-models");
      const chatModels = (response.data || []).filter((model: any) => model.type === 'chat');
      setAvailableModels(chatModels);
    } catch (err: any) {
      console.error("Failed to fetch models:", err);
    }
  };

  const fetchAvailableJobs = async (search = "", offset = 0) => {
    try {
      const params = new URLSearchParams({
        limit: jobLimit.toString(),
        offset: offset.toString()
      });
      if (search) {
        params.append('q', search);
      }
      const response = await api.get(`jd/admin/list?${params.toString()}`);
      
      // Response format: { items: [...], total, limit, offset, page, pages }
      if (response.data && response.data.items) {
        if (offset === 0) {
          setAvailableJobs(response.data.items);
        } else {
          setAvailableJobs(prev => [...prev, ...response.data.items]);
        }
        setJobTotal(response.data.total || 0);
        setJobOffset(offset);
      }
    } catch (err: any) {
      console.error("Failed to fetch jobs:", err);
    }
  };
  
  const handleJobSearch = (searchTerm: string) => {
    setJobSearch(searchTerm);
    setJobOffset(0);
    fetchAvailableJobs(searchTerm, 0);
  };
  
  const handleJobLoadMore = () => {
    const newOffset = jobOffset + jobLimit;
    fetchAvailableJobs(jobSearch, newOffset);
  };

  const handleRunBenchmark = async () => {
    if (!selectedTestSet) {
      setError("Vui lòng chọn một bộ kiểm thử");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const config: any = {
        parsing_model: parsingModel,
        evaluation_strategy: evaluationStrategy,
        temperature: temperature,
        max_tokens: maxTokens
      };

      if (evaluationStrategy === "single_judge") {
        config.judge_model = judgePrimary;
      } else if (evaluationStrategy === "dual_judge") {
        config.judge_model_primary = judgePrimary;
        config.judge_model_secondary = judgeSecondary;
        config.aggregation = aggregation;
      } else if (evaluationStrategy === "ensemble") {
        // Normalize weights to sum to 1.0
        const totalWeight = ensembleJudges.reduce((sum, j) => sum + j.weight, 0);
        config.judge_models = ensembleJudges.map(j => ({
          model: j.model,
          weight: j.weight / totalWeight
        }));
      }

      const response = await api.post("admin/benchmarks/run", {
        test_set_id: selectedTestSet,
        llm_config: config
      });

      showSuccess(`Đã bắt đầu Benchmark! Session ID: ${response.data.session_id}`);
      
      // Refresh sessions list
      fetchSessions();
      
      // Auto-select the new session and switch to results tab
      setSelectedSession(response.data.session_id);
      setActiveTab("results");
      
      // Poll for completion
      pollSessionStatus(response.data.session_id);
      
    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleQuickBenchmark = async () => {
    if (!quickCvId || !quickJobId) {
      setError("Vui lòng chọn cả CV và Công việc");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const config: any = {
        parsing_model: parsingModel,
        evaluation_strategy: evaluationStrategy,
        temperature: temperature,
        max_tokens: maxTokens
      };

      if (evaluationStrategy === "single_judge") {
        config.judge_model = judgePrimary;
      } else if (evaluationStrategy === "dual_judge") {
        config.judge_model_primary = judgePrimary;
        config.judge_model_secondary = judgeSecondary;
        config.aggregation = aggregation;
      } else if (evaluationStrategy === "ensemble") {
        const totalWeight = ensembleJudges.reduce((sum, j) => sum + j.weight, 0);
        config.judge_models = ensembleJudges.map(j => ({
          model: j.model,
          weight: j.weight / totalWeight
        }));
      }

      const response = await api.post("admin/benchmarks/quick-run", {
        flow_type: quickFlowType,
        cv_id: quickCvId,
        job_id: quickJobId,
        llm_config: config
      });

      showSuccess(`Benchmark nhanh hoàn tất! Điểm: ${(response.data.score * 100).toFixed(1)}% | Độ trễ: ${response.data.latency_ms}ms`);
      
    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const addEnsembleJudge = () => {
    setEnsembleJudges([...ensembleJudges, { model: "gpt-4o-mini", weight: 0.5 }]);
  };

  const removeEnsembleJudge = (index: number) => {
    setEnsembleJudges(ensembleJudges.filter((_, i) => i !== index));
  };

  const updateEnsembleJudge = (index: number, field: "model" | "weight", value: string | number) => {
    const updated = [...ensembleJudges];
    if (field === "model") {
      updated[index].model = value as string;
    } else {
      updated[index].weight = parseFloat(value as string) || 0;
    }
    setEnsembleJudges(updated);
  };

  // ========================================================================
  // TEST SET MANAGEMENT
  // ========================================================================

  const handleCreateTestSet = async () => {
    if (!newTestSetName || !newTestSetFlowType) {
      setError("Vui lòng cung cấp tên bộ kiểm thử và loại quy trình");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.post("admin/benchmarks/test-sets", {
        name: newTestSetName,
        description: newTestSetDescription,
        flow_type: newTestSetFlowType,
        is_active: true
      });

      showSuccess(`Đã tạo bộ kiểm thử! ID: ${response.data.id}`);
      
      // Reset form
      setNewTestSetName("");
      setNewTestSetDescription("");
      setNewTestSetFlowType("full_cv_to_gap");
      setShowCreateTestSet(false);
      fetchTestSets();
      
    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleEditTestSet = (testSet: any) => {
    setEditingTestSet(testSet);
    setEditName(testSet.name);
    setEditDescription(testSet.description || "");
    setEditFlowType(testSet.flow_type);
    setEditIsActive(testSet.is_active);
    setShowEditTestSet(true);
  };

  const handleUpdateTestSet = async () => {
    if (!editingTestSet || !editName) return;
    
    setLoading(true);
    try {
      await api.patch(`admin/benchmarks/test-sets/${editingTestSet.id}`, {
        name: editName,
        description: editDescription,
        flow_type: editFlowType,
        is_active: editIsActive
      });
      
      setShowEditTestSet(false);
      setEditingTestSet(null);
      showSuccess("Đã cập nhật bộ kiểm thử!");
      fetchTestSets();
    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTestSet = async (id: string) => {
    const confirmed = await confirm({
      message: "Bạn có chắc chắn muốn xóa bộ kiểm thử này không? Tất cả các trường hợp kiểm thử bên trong cũng sẽ bị xóa.",
      variant: 'danger'
    });
    
    if (!confirmed) {
      return;
    }
    
    setLoading(true);
    try {
      await api.delete(`admin/benchmarks/test-sets/${id}`);
      showSuccess("Đã xóa bộ kiểm thử!");
      fetchTestSets();
    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const fetchTestCases = async (testSetId: string) => {
    try {
      const response = await api.get(`admin/benchmarks/test-sets/${testSetId}/cases`);
      // Backend returns {test_set: {...}, cases: [...]}
      setTestCases(response.data.cases || []);
      setSelectedTestSetForManagement(testSetId);
    } catch (err: any) {
      setError(extractErrorMessage(err));
    }
  };

  const handleBatchAddTestCases = async () => {
    if (!selectedTestSetForManagement) {
      setError("Chưa chọn bộ kiểm thử nào");
      return;
    }

    // Determine CV IDs to use
    let cvIds: string[] = [];
    if (cvSourceMode === "existing") {
      cvIds = selectedCVsForBatch;
    } else {
      // Upload CVs first if not already uploaded
      if (uploadedCVIds.length === 0 && uploadedCVFiles.length > 0) {
        const ids = await uploadCVFiles();
        cvIds = ids;
      } else {
        cvIds = uploadedCVIds;
      }
    }

    // Determine Job IDs to use
    let jobIds: string[] = [];
    if (jdSourceMode === "existing") {
      jobIds = selectedJobsForBatch;
    } else {
      // Create pasted JD first if not already created
      if (!pastedJDId && pastedJDText) {
        const jobId = await handleCreatePastedJD();
        jobIds = jobId ? [jobId] : [];
      } else if (pastedJDId) {
        jobIds = [pastedJDId];
      }
    }

    if (cvIds.length === 0 || jobIds.length === 0) {
      setError("Vui lòng cung cấp ít nhất một CV và một Công việc");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.post(
        `admin/benchmarks/test-sets/${selectedTestSetForManagement}/batch-add`,
        {
          cv_ids: cvIds,
          job_ids: jobIds,
          mode: batchMode
        }
      );

      showSuccess(`Đã thêm ${response.data.count} trường hợp kiểm thử!`);
      
      // Reset all selections
      setSelectedCVsForBatch([]);
      setSelectedJobsForBatch([]);
      setUploadedCVFiles([]);
      setUploadedCVIds([]);
      resetPastedJD();
      setShowAddTestCases(false);
      if (selectedTestSetForManagement) {
        fetchTestCases(selectedTestSetForManagement);
      }

    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTestCase = async (caseId: string) => {
    const confirmed = await confirm({
      message: "Bạn có chắc chắn muốn xóa trường hợp kiểm thử này không?",
      variant: 'danger'
    });
    
    if (!confirmed) return;

    setLoading(true);
    try {
      await api.delete(`admin/benchmarks/test-cases/${caseId}`);
      showSuccess('Đã xóa trường hợp kiểm thử!');
      
      // Refresh test cases
      if (selectedTestSetForManagement) {
        await fetchTestCases(selectedTestSetForManagement);
      }
    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleEditTestCase = (testCase: any) => {
    setEditingTestCase(testCase);
    setEditCvId(testCase.input_data?.cv_id || "");
    setEditJobId(testCase.input_data?.job_id || "");
    setEditReferenceOutput(testCase.reference_output ? JSON.stringify(testCase.reference_output, null, 2) : "");
    setEditMetadata(testCase.test_metadata ? JSON.stringify(testCase.test_metadata, null, 2) : "");
    setShowEditTestCase(true);
  };

  const handleUpdateTestCase = async () => {
    if (!editingTestCase) return;
    
    setLoading(true);
    try {
      const payload: any = {
        input_data: {
          cv_id: editCvId,
          job_id: editJobId
        }
      };

      // Parse JSON fields if provided
      if (editReferenceOutput.trim()) {
        try {
          payload.reference_output = JSON.parse(editReferenceOutput);
        } catch (e) {
          setError("Reference Output phải là JSON hợp lệ");
          setLoading(false);
          return;
        }
      }

      if (editMetadata.trim()) {
        try {
          payload.test_metadata = JSON.parse(editMetadata);
        } catch (e) {
          setError("Metadata phải là JSON hợp lệ");
          setLoading(false);
          return;
        }
      }

      await api.patch(`admin/benchmarks/test-cases/${editingTestCase.id}`, payload);
      
      setShowEditTestCase(false);
      setEditingTestCase(null);
      showSuccess('Đã cập nhật trường hợp kiểm thử!');
      
      // Refresh test cases
      if (selectedTestSetForManagement) {
        fetchTestCases(selectedTestSetForManagement);
      }
    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const toggleCVSelection = (cvId: string) => {
    setSelectedCVsForBatch(prev => 
      prev.includes(cvId) 
        ? prev.filter(id => id !== cvId)
        : [...prev, cvId]
    );
  };

  const toggleJobSelection = (jobId: string) => {
    setSelectedJobsForBatch(prev => 
      prev.includes(jobId) 
        ? prev.filter(id => id !== jobId)
        : [...prev, jobId]
    );
  };

  // ========================================================================
  // CV UPLOAD HANDLERS
  // ========================================================================

  const handleCVFilesChange = (files: FileList | null) => {
    if (!files) return;
    
    const fileArray = Array.from(files);
    setUploadedCVFiles(prev => [...prev, ...fileArray]);
  };

  const handleCVDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    handleCVFilesChange(files);
  };

  const handleCVDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const removeUploadedCV = (index: number) => {
    setUploadedCVFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadCVFiles = async (): Promise<string[]> => {
    if (uploadedCVFiles.length === 0) return [];

    setLoading(true);
    setError(null);

    try {
      const uploadedIds: string[] = [];

      for (const file of uploadedCVFiles) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await api.post('cv/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });

        uploadedIds.push(response.data.cv_id);
      }

      setUploadedCVIds(uploadedIds);
      showSuccess(`Tải lên ${uploadedIds.length} CV thành công!`);
      
      // Refresh available CVs
      fetchAvailableCVs();
      
      return uploadedIds; // Return the IDs directly

    } catch (err: any) {
      setError(extractErrorMessage(err));
      return [];
    } finally {
      setLoading(false);
    }
  };

  // ========================================================================
  // JD PASTE HANDLERS
  // ========================================================================

  const handleCreatePastedJD = async (): Promise<string | null> => {
    if (!pastedJDText || !pastedJDTitle) {
      setError("Vui lòng cung cấp cả tiêu đề và mô tả JD");
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.post('jobs', {
        title: pastedJDTitle,
        description: pastedJDText,
        company: "Benchmark Test",
        location: "N/A",
        salary_range: "N/A",
        is_active: false // Mark as test JD
      });

      const jobId = response.data.id;
      setPastedJDId(jobId);
      showSuccess(`Đã tạo JD! ID: ${jobId}`);
      
      // Refresh available jobs
      fetchAvailableJobs();
      
      return jobId; // Return the ID directly

    } catch (err: any) {
      setError(extractErrorMessage(err));
      return null;
    } finally {
      setLoading(false);
    }
  };

  const resetPastedJD = () => {
    setPastedJDText("");
    setPastedJDTitle("");
    setPastedJDId(null);
  };

  const pollSessionStatus = async (sessionId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await api.get(`admin/benchmarks/sessions/${sessionId}`);
        const session = response.data.session;
        
        if (session.status === "completed" || session.status === "failed") {
          clearInterval(interval);
          fetchSessions();
          fetchSessionDetails(sessionId);
        }
      } catch (err) {
        clearInterval(interval);
      }
    }, 5000); // Poll every 5 seconds
  };

  const fetchSessionDetails = async (sessionId: string) => {
    try {
      const response = await api.get(`admin/benchmarks/sessions/${sessionId}`);
      setSessionDetails(response.data);
    } catch (err: any) {
      console.error("Failed to fetch session details:", err);
    }
  };

  const handleViewSession = (sessionId: string) => {
    setSelectedSession(sessionId);
    fetchSessionDetails(sessionId);
  };

  const handleExport = async (sessionId: string, format: string) => {
    try {
      const response = await api.get(
        `admin/benchmarks/sessions/${sessionId}/export?format=${format}`,
        { responseType: 'blob' }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `benchmark_${sessionId}.${format}`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err: any) {
      setError(extractErrorMessage(err));
    }
  };

  // ========================================================================
  // TAB RENDERERS
  // ========================================================================

  function renderRunBenchmarkTab() {
    return (
      <div className={styles.content}>
        {/* Configuration Panel */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className={styles.configPanel}
        >
          <h2><Settings size={24} /> Cấu hình</h2>
          
          <div className={styles.formGroup}>
            <label>Bộ kiểm thử:</label>
            <select 
              value={selectedTestSet} 
              onChange={(e) => setSelectedTestSet(e.target.value)}
              className={styles.select}
            >
              <option value="">Chọn một bộ kiểm thử...</option>
              {testSets.map((ts) => (
                <option key={ts.id} value={ts.id}>
                  {ts.name} ({ts.flow_type})
                </option>
              ))}
            </select>
          </div>

          <div className={styles.formGroup}>
            <label>Mô hình xử lý (Parsing):</label>
            <select 
              value={parsingModel} 
              onChange={(e) => setParsingModel(e.target.value)}
              className={styles.select}
            >
              {renderModelOptions()}
            </select>
          </div>

          <div className={styles.formGroup}>
            <label>Chiến lược đánh giá:</label>
            <select 
              value={evaluationStrategy} 
              onChange={(e) => setEvaluationStrategy(e.target.value)}
              className={styles.select}
            >
              <option value="single_judge">Single Judge</option>
              <option value="dual_judge">Dual Judge (Recommended)</option>
              <option value="ensemble">Ensemble (Advanced)</option>
            </select>
          </div>

          {renderJudgeConfiguration()}

          {/* Advanced Options */}
          <div className={styles.formGroup}>
            <button 
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={styles.btnToggle}
            >
              {showAdvanced ? <ChevronDown size={18} /> : <ChevronRight size={18} />} Tùy chọn nâng cao
            </button>
          </div>

          {showAdvanced && (
            <>
              <div className={styles.formGroup}>
                <label>Temperature: {temperature}</label>
                <input 
                  type="range" 
                  min="0" 
                  max="1" 
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className={styles.slider}
                />
              </div>

              <div className={styles.formGroup}>
                <label>Max Tokens:</label>
                <input 
                  type="number" 
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                  className={styles.input}
                  min="100"
                  max="8000"
                />
              </div>
            </>
          )}

          <button 
            onClick={handleRunBenchmark} 
            disabled={loading || !selectedTestSet}
            className={styles.btnRun}
          >
            {loading ? <Clock className="animate-spin" size={20} /> : <Play size={20} />} 
            {loading ? " Đang chạy..." : " Chạy Benchmark"}
          </button>
        </motion.div>

        {/* Recent Sessions Preview */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className={styles.sessionsPanel}
        >
          <h2><BarChart3 size={24} /> Phiên gần đây</h2>
          
          {sessions.length === 0 ? (
            <p className={styles.empty}>Chưa có phiên benchmark nào. Hãy chạy benchmark đầu tiên của bạn!</p>
          ) : (
            <div className={styles.sessionsList}>
              {sessions.slice(0, 5).map((session) => (
                <div 
                  key={session.id} 
                  className={styles.sessionCard}
                  onClick={() => {
                    setSelectedSession(session.id);
                    setActiveTab("results");
                  }}
                >
                  <div className={styles.sessionHeader}>
                    <span className={`${styles.status} ${styles[session.status]}`}>
                      {session.status}
                    </span>
                    <span className={styles.date}>
                      {new Date(session.created_at).toLocaleString()}
                    </span>
                  </div>
                  
                  {session.overall_score !== null && (
                    <div className={styles.score}>
                      <strong>Điểm:</strong> {(session.overall_score * 100).toFixed(1)}%
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          
          <button 
            onClick={() => setActiveTab("results")}
            className={styles.btnViewAll}
          >
            View All Sessions →
          </button>
        </motion.div>
      </div>
    );
  }
  function renderJudgeConfiguration() {
    if (evaluationStrategy === "single_judge") {
      return (
        <div className={styles.formGroup}>
          <label>Mô hình đánh giá (Judge):</label>
          <select 
            value={judgePrimary} 
            onChange={(e) => setJudgePrimary(e.target.value)}
            className={styles.select}
          >
            {renderModelOptions()}
          </select>
        </div>
      );
    }

    if (evaluationStrategy === "dual_judge") {
      return (
        <>
          <div className={styles.formGroup}>
            <label>Mô hình đánh giá chính:</label>
            <select 
              value={judgePrimary} 
              onChange={(e) => setJudgePrimary(e.target.value)}
              className={styles.select}
            >
              {renderModelOptions()}
            </select>
          </div>

          <div className={styles.formGroup}>
            <label>Mô hình đánh giá phụ:</label>
            <select 
              value={judgeSecondary} 
              onChange={(e) => setJudgeSecondary(e.target.value)}
              className={styles.select}
            >
              {renderModelOptions()}
            </select>
          </div>

          <div className={styles.formGroup}>
            <label>Phương pháp tổng hợp:</label>
            <select 
              value={aggregation} 
              onChange={(e) => setAggregation(e.target.value)}
              className={styles.select}
            >
              <option value="average">Trung bình (Cân bằng)</option>
              <option value="max">Lớn nhất (Lạc quan)</option>
              <option value="min">Nhỏ nhất (Thận trọng)</option>
              <option value="weighted">Trọng số (60/40)</option>
            </select>
          </div>
        </>
      );
    }

    if (evaluationStrategy === "ensemble") {
      return (
        <div className={styles.ensembleConfig}>
          <label>Nhóm mô hình đánh giá (Ensemble):</label>
          {ensembleJudges.map((judge, index) => (
            <div key={index} className={styles.ensembleJudge}>
              <select 
                value={judge.model}
                onChange={(e) => updateEnsembleJudge(index, "model", e.target.value)}
                className={styles.selectSmall}
              >
                {renderModelOptions()}
              </select>
              
              <input 
                type="number"
                value={judge.weight}
                onChange={(e) => updateEnsembleJudge(index, "weight", e.target.value)}
                className={styles.inputSmall}
                min="0"
                max="1"
                step="0.1"
                placeholder="Trọng số"
              />
              
              {ensembleJudges.length > 2 && (
                <button 
                  onClick={() => removeEnsembleJudge(index)}
                  className={styles.btnRemove}
                >
                  ✕
                </button>
              )}
            </div>
          ))}
          
          <button 
            onClick={addEnsembleJudge}
            className={styles.btnAdd}
          >
            + Thêm mô hình
          </button>
          
          <div className={styles.ensembleInfo}>
            Tổng trọng số: {ensembleJudges.reduce((sum, j) => sum + j.weight, 0).toFixed(2)}
            {ensembleJudges.reduce((sum, j) => sum + j.weight, 0) !== 1.0 && (
              <span className={styles.warning}> (sẽ được chuẩn hóa về 1.0)</span>
            )}
          </div>
        </div>
      );
    }

    return null;
  }

  function renderQuickTestTab() {
    return (
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={styles.content}
      >
        <div className={styles.configPanel}>
          <h2><Zap size={24} /> Kiểm tra nhanh</h2>
          <p className={styles.description}>
            Chạy benchmark nhanh cho một cặp CV/Job mà không cần lưu vào bộ kiểm thử.
          </p>
          
          <div className={styles.formGroup}>
            <label>Loại quy trình (Flow Type):</label>
            <select 
              value={quickFlowType} 
              onChange={(e) => setQuickFlowType(e.target.value)}
              className={styles.select}
            >
              <option value="cv_parsing_v3">Chỉ xử lý CV (Parsing)</option>
              <option value="full_cv_to_gap">Từ CV → Phân tích Gap</option>
            </select>
          </div>

          <div className={styles.formGroup}>
            <label>Chọn CV:</label>
            <select 
              value={quickCvId} 
              onChange={(e) => setQuickCvId(e.target.value)}
              className={styles.select}
            >
              <option value="">Chọn một CV...</option>
              {availableCVs.map((cv) => (
                <option key={cv.id} value={cv.id}>
                  {cv.full_name || cv.user_email}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.formGroup}>
            <label>Chọn công việc:</label>
            <select 
              value={quickJobId} 
              onChange={(e) => setQuickJobId(e.target.value)}
              className={styles.select}
            >
              <option value="">Chọn một công việc...</option>
              {availableJobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title_raw}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.formGroup}>
            <label>Mô hình xử lý (Parsing):</label>
            <select 
              value={parsingModel} 
              onChange={(e) => setParsingModel(e.target.value)}
              className={styles.select}
            >
              {availableModels.length > 0 ? (
                availableModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} ({model.provider})
                  </option>
                ))
              ) : (
                <>
                  <option value="gpt-4o-mini">GPT-4o Mini</option>
                  <option value="gpt-4o">GPT-4o</option>
                  <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
                </>
              )}
            </select>
          </div>

          <div className={styles.formGroup}>
            <label>Chiến lược đánh giá:</label>
            <select 
              value={evaluationStrategy} 
              onChange={(e) => setEvaluationStrategy(e.target.value)}
              className={styles.select}
            >
              <option value="single_judge">Single Judge</option>
              <option value="dual_judge">Dual Judge (Recommended)</option>
              <option value="ensemble">Ensemble (Advanced)</option>
            </select>
          </div>

          {renderJudgeConfiguration()}

          <button 
            onClick={handleQuickBenchmark} 
            disabled={loading || !quickCvId || !quickJobId}
            className={styles.btnRun}
          >
            {loading ? "⏳ Đang chạy..." : "⚡ Chạy Kiểm tra nhanh"}
          </button>
        </div>

        <div className={styles.infoPanel}>
          <h3><Info size={20} /> Về Kiểm tra nhanh</h3>
          <ul>
            <li>Chạy benchmark trên một cặp CV/Job duy nhất</li>
            <li>KHÔNG lưu vào bộ kiểm thử</li>
            <li>Kết quả tức thì (không theo dõi phiên)</li>
            <li>Hữu ích cho việc xác thực nhanh</li>
            <li>Sử dụng cùng đánh giá mô hình như benchmark đầy đủ</li>
          </ul>
        </div>
      </motion.div>
    );
  }

  function renderTestSetsTab() {
    return (
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={styles.content}
      >
        <div className={styles.testSetsPanel}>
          <div className={styles.testSetsHeader}>
            <h2><Layers size={24} /> Bộ kiểm thử</h2>
            <button 
              onClick={() => setShowCreateTestSet(true)}
              className={styles.btnCreate}
            >
              <Plus size={18} /> Tạo bộ kiểm thử
            </button>
          </div>

          {/* Create Test Set Modal */}
          <Modal
            isOpen={showCreateTestSet}
            onClose={() => setShowCreateTestSet(false)}
            title="Create New Test Set"
            maxWidth="600px"
          >
            <div className={styles.modalForm}>
              <div className={styles.formGroup}>
                <label>Tên:</label>
                <input 
                  type="text"
                  value={newTestSetName}
                  onChange={(e) => setNewTestSetName(e.target.value)}
                  placeholder="VD: CV Parsing Benchmark v2"
                  className={styles.input}
                />
              </div>

              <div className={styles.formGroup}>
                <label>Mô tả:</label>
                <textarea 
                  value={newTestSetDescription}
                  onChange={(e) => setNewTestSetDescription(e.target.value)}
                  placeholder="Mô tả mục đích của bộ kiểm thử này..."
                  className={styles.textarea}
                  rows={3}
                />
              </div>

              <div className={styles.formGroup}>
                <label>Flow Type:</label>
                  <select 
                    value={newTestSetFlowType}
                    onChange={(e) => setNewTestSetFlowType(e.target.value)}
                    className={styles.select}
                  >
                    {FLOW_TYPES.map(flow => (
                      <option key={flow.key} value={flow.key}>{flow.label}</option>
                    ))}
                  </select>
              </div>

              <div className={styles.modalActions}>
                <button 
                  onClick={() => setShowCreateTestSet(false)}
                  className={styles.btnCancel}
                  disabled={loading}
                >
                  Hủy
                </button>
                <button 
                  onClick={handleCreateTestSet}
                  disabled={loading || !newTestSetName}
                  className={styles.btnPrimary}
                >
                  {loading ? "Đang tạo..." : "Tạo bộ kiểm thử"}
                </button>
              </div>
            </div>
          </Modal>
          
          {/* Test Sets List */}
          {testSets.length === 0 ? (
            <p className={styles.empty}>Chưa có bộ kiểm thử nào. Hãy tạo bộ đầu tiên!</p>
          ) : (
            <div className={styles.testSetsList}>
              {testSets.map((testSet) => (
                <div key={testSet.id} className={styles.testSetCard}>
                  <div className={styles.testSetHeader}>
                    <h3>{testSet.name}</h3>
                    <span className={`${styles.badge} ${testSet.is_active ? styles.active : styles.inactive}`}>
                      {testSet.is_active ? "Đang hoạt động" : "Ngừng hoạt động"}
                    </span>
                  </div>
                  
                  <p className={styles.description}>{testSet.description}</p>
                  
                  <div className={styles.testSetInfo}>
                    <div><strong>Loại quy trình:</strong> {getFlowTypeLabel(testSet.flow_type)}</div>
                    <div><strong>Ngày tạo:</strong> {new Date(testSet.created_at).toLocaleDateString()}</div>
                  </div>

                  <div className={styles.testSetActions}>
                    <button 
                      onClick={() => {
                        setSelectedTestSet(testSet.id);
                        setActiveTab("run");
                      }}
                      className={styles.btnSelect}
                      title="Chạy Benchmark"
                    >
                      <Play size={16} />
                    </button>
                    
                    <button 
                      onClick={() => {
                        setSelectedTestSetForManagement(testSet.id);
                        fetchTestCases(testSet.id);
                      }}
                      className={styles.btnManage}
                      title="Quản lý Test Cases"
                    >
                      <Settings size={16} />
                    </button>

                    <button 
                      onClick={() => handleEditTestSet(testSet)}
                      className={styles.btnEdit}
                      title="Chỉnh sửa"
                    >
                      <Edit size={16} />
                    </button>

                    <button 
                      onClick={() => handleDeleteTestSet(testSet.id)}
                      className={styles.btnDeleteAction}
                      title="Xóa"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  </div>
                ))}
              </div>
            )}

          {/* Edit Test Set Modal */}
          <Modal
            isOpen={showEditTestSet}
            onClose={() => setShowEditTestSet(false)}
            title="Chỉnh sửa bộ kiểm thử"
            maxWidth="600px"
          >
            <div className={styles.modalForm}>
              <div className={styles.formGroup}>
                <label>Tên:</label>
                <input 
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className={styles.input}
                />
              </div>

              <div className={styles.formGroup}>
                <label>Mô tả:</label>
                <textarea 
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className={styles.textarea}
                  rows={3}
                />
              </div>

              <div className={styles.formGroup}>
                <label>Loại quy trình (Flow Type):</label>
                <select 
                  value={editFlowType} 
                  onChange={(e) => setEditFlowType(e.target.value)}
                  className={styles.select}
                >
                  {FLOW_TYPES.map(flow => (
                    <option key={flow.key} value={flow.key}>{flow.label}</option>
                  ))}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label className={styles.checkboxLabel}>
                  <input 
                    type="checkbox"
                    checked={editIsActive}
                    onChange={(e) => setEditIsActive(e.target.checked)}
                  />
                  <span>Đang hoạt động</span>
                </label>
              </div>

              <div className={styles.modalActions}>
                <button 
                  onClick={() => setShowEditTestSet(false)}
                  className={styles.btnCancel}
                >
                  Hủy
                </button>
                <button 
                  onClick={handleUpdateTestSet}
                  disabled={loading || !editName}
                  className={styles.btnPrimary}
                >
                  {loading ? "Đang lưu..." : "Cập nhật"}
                </button>
              </div>
            </div>
          </Modal>
          {/* Test Case Management Modal */}
          <Modal
            isOpen={!!selectedTestSetForManagement}
            onClose={() => setSelectedTestSetForManagement(null)}
            title="Quản lý Trường hợp kiểm thử"
            maxWidth="1000px"
          >
            <div className={styles.modalForm}>
              <div className={styles.testCasePanelHeader}>
                <div className={styles.testSetTitle}>
                  <h3>{testSets.find(ts => ts.id === selectedTestSetForManagement)?.name}</h3>
                </div>
                <div className={styles.modalActions}>
                  <button 
                    onClick={() => setShowAddTestCases(true)}
                    className={styles.btnAdd}
                  >
                    <Plus size={18} /> Thêm Test Cases
                  </button>
                </div>
              </div>

              {/* Batch Add Test Cases Modal */}
              <Modal
                isOpen={showAddTestCases}
                onClose={() => setShowAddTestCases(false)}
                title="Thêm hàng loạt trường hợp kiểm thử"
                maxWidth="900px"
              >
                <div className={styles.modalForm}>
                  <div className={styles.formGroup}>
                    <label>Chế độ:</label>
                    <select 
                      value={batchMode}
                      onChange={(e) => setBatchMode(e.target.value as "all_combinations" | "paired")}
                      className={styles.select}
                    >
                      <option value="all_combinations">Tất cả tổ hợp (CV × Job)</option>
                      <option value="paired">Theo cặp (CV[i] + Job[i])</option>
                    </select>
                  </div>

                  <div className={styles.selectionGrid}>
                    {/* CV Selection/Upload */}
                    <div className={styles.selectionColumn}>
                      <div className={styles.sourceToggle}>
                        <button 
                          className={`${styles.toggleBtn} ${cvSourceMode === "existing" ? styles.active : ""}`}
                          onClick={() => setCvSourceMode("existing")}
                        >
                          <Database size={16} /> Sử dụng CV hiện có
                        </button>
                        <button 
                          className={`${styles.toggleBtn} ${cvSourceMode === "upload" ? styles.active : ""}`}
                          onClick={() => setCvSourceMode("upload")}
                        >
                          <FileUp size={16} /> Tải lên CV mới
                        </button>
                      </div>

                      {cvSourceMode === "existing" ? (
                        <>
                          <h5>Chọn CV ({selectedCVsForBatch.length} đã chọn)</h5>
                          <div className={styles.checkboxList}>
                            {availableCVs.map((cv) => (
                              <label key={cv.id} className={styles.checkboxItem}>
                                <input 
                                  type="checkbox"
                                  checked={selectedCVsForBatch.includes(cv.id)}
                                  onChange={() => toggleCVSelection(cv.id)}
                                />
                                <span>{cv.full_name || cv.user_email}</span>
                              </label>
                            ))}
                          </div>
                        </>
                      ) : (
                        <>
                          <h5>Tải lên CV ({uploadedCVFiles.length} tệp)</h5>
                          <div 
                            className={styles.dropZone}
                            onDrop={handleCVDrop}
                            onDragOver={handleCVDragOver}
                          >
                            <input 
                              type="file"
                              multiple
                              accept=".pdf,.doc,.docx"
                              onChange={(e) => handleCVFilesChange(e.target.files)}
                              className={styles.fileInput}
                              id="cv-upload-modal"
                            />
                            <label htmlFor="cv-upload-modal" className={styles.dropZoneLabel}>
                              <div className={styles.dropZoneIcon}><Upload size={48} /></div>
                              <div>Kéo & thả CV vào đây</div>
                              <div className={styles.dropZoneHint}>hoặc click để chọn tệp</div>
                              <div className={styles.dropZoneFormats}>PDF, DOC, DOCX</div>
                            </label>
                          </div>
                          
                          {uploadedCVFiles.length > 0 && (
                            <div className={styles.uploadedFilesList}>
                              {uploadedCVFiles.map((file, index) => (
                                <div key={index} className={styles.uploadedFile}>
                                  <span><FileText size={16} /> {file.name}</span>
                                  <button 
                                    onClick={() => removeUploadedCV(index)}
                                    className={styles.btnRemoveFile}
                                  >
                                    <X size={14} />
                                  </button>
                                </div>
                              ))}
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    {/* Job Selection/Paste */}
                    <div className={styles.selectionColumn}>
                      <div className={styles.sourceToggle}>
                        <button 
                          className={`${styles.toggleBtn} ${jdSourceMode === "existing" ? styles.active : ""}`}
                          onClick={() => setJdSourceMode("existing")}
                        >
                          <Database size={16} /> Sử dụng Job hiện có
                        </button>
                        <button 
                          className={`${styles.toggleBtn} ${jdSourceMode === "paste" ? styles.active : ""}`}
                          onClick={() => setJdSourceMode("paste")}
                        >
                          <FileText size={16} /> Dán JD mới
                        </button>
                      </div>

                      {jdSourceMode === "existing" ? (
                        <>
                          <h5>Chọn Job ({selectedJobsForBatch.length} đã chọn)</h5>
                          <div className={styles.searchBox}>
                            <input 
                              type="text"
                              value={jobSearch}
                              onChange={(e) => handleJobSearch(e.target.value)}
                              placeholder="Tìm kiếm công việc..."
                              className={styles.searchInput}
                            />
                          </div>
                          <div className={styles.checkboxList}>
                            {availableJobs.map((job) => (
                              <label key={job.id} className={styles.checkboxItem}>
                                <input 
                                  type="checkbox"
                                  checked={selectedJobsForBatch.includes(job.id)}
                                  onChange={() => toggleJobSelection(job.id)}
                                />
                                <span>{job.title_raw}</span>
                              </label>
                            ))}
                          </div>
                          {availableJobs.length < jobTotal && (
                            <button 
                              onClick={handleJobLoadMore}
                              className={styles.btnLoadMore}
                            >
                              Tải thêm ({availableJobs.length}/{jobTotal})
                            </button>
                          )}
                        </>
                      ) : (
                        <>
                          <h5>Dán mô tả công việc (JD)</h5>
                          <div className={styles.pasteJDForm}>
                            <input 
                              type="text"
                              value={pastedJDTitle}
                              onChange={(e) => setPastedJDTitle(e.target.value)}
                              placeholder="Tiêu đề công việc"
                              className={styles.input}
                            />
                            <textarea 
                              value={pastedJDText}
                              onChange={(e) => setPastedJDText(e.target.value)}
                              placeholder="Dán mô tả công việc vào đây..."
                              className={styles.textarea}
                              rows={8}
                            />
                            {pastedJDId ? (
                              <div className={styles.successMessage}>
                                <CheckCircle2 size={18} /> Đã tạo JD!
                                <button onClick={resetPastedJD} className={styles.btnReset}>
                                  Đặt lại
                                </button>
                              </div>
                            ) : (
                              <button 
                                onClick={handleCreatePastedJD}
                                disabled={loading || !pastedJDText || !pastedJDTitle}
                                className={styles.btnSecondary}
                              >
                                {loading ? "Đang tạo..." : "Tạo JD"}
                              </button>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  <div className={styles.batchSummary}>
                    <strong>Tổng quan:</strong> {batchMode === "all_combinations" ? "Tất cả tổ hợp" : "Theo cặp"}
                    {" | "}
                    {(cvSourceMode === "existing" ? selectedCVsForBatch.length : uploadedCVFiles.length)} CV × 
                    {(jdSourceMode === "existing" ? selectedJobsForBatch.length : (pastedJDId ? 1 : 0))} Job
                    {" = "}
                    {batchMode === "all_combinations" 
                      ? (cvSourceMode === "existing" ? selectedCVsForBatch.length : uploadedCVFiles.length) * 
                        (jdSourceMode === "existing" ? selectedJobsForBatch.length : (pastedJDId ? 1 : 0))
                      : Math.min(
                          cvSourceMode === "existing" ? selectedCVsForBatch.length : uploadedCVFiles.length,
                          jdSourceMode === "existing" ? selectedJobsForBatch.length : (pastedJDId ? 1 : 0)
                        )
                    } trường hợp kiểm thử
                  </div>

                  <div className={styles.modalActions}>
                    <button 
                      onClick={() => setShowAddTestCases(false)}
                      className={styles.btnCancel}
                      disabled={loading}
                    >
                      Hủy
                    </button>
                    <button 
                      onClick={handleBatchAddTestCases}
                      disabled={loading || 
                        (cvSourceMode === "existing" ? selectedCVsForBatch.length === 0 : uploadedCVFiles.length === 0) ||
                        (jdSourceMode === "existing" ? selectedJobsForBatch.length === 0 : !pastedJDText && !pastedJDId)
                      }
                      className={styles.btnPrimary}
                    >
                      {loading ? "Đang thêm..." : "Thêm Test Cases"}
                    </button>
                  </div>
                </div>
              </Modal>

              {/* Test Cases List */}
              <div className={styles.testCasesListModal}>
                {testCases.length === 0 ? (
                  <p className={styles.empty}>Chưa có trường hợp kiểm thử nào.</p>
                ) : (
                  <div className={styles.tableWrapper}>
                    <table className={styles.testCasesTable}>
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>CV ID</th>
                          <th>Job ID</th>
                          <th>Ngày tạo</th>
                          <th>Hành động</th>
                        </tr>
                      </thead>
                      <tbody>
                        {testCases.map((testCase) => (
                          <tr key={testCase.id}>
                            <td className={styles.idCol}>{testCase.id.substring(0, 8)}...</td>
                            <td>{testCase.input_data?.cv_id?.substring(0, 8) || 'N/A'}...</td>
                            <td>{testCase.input_data?.job_id?.substring(0, 8) || 'N/A'}...</td>
                            <td>{new Date(testCase.created_at).toLocaleDateString()}</td>
                            <td>
                              <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button 
                                  onClick={() => handleEditTestCase(testCase)}
                                  className={styles.btnEditTable}
                                  title="Sửa"
                                >
                                  <Edit size={16} />
                                </button>
                                <button 
                                  onClick={() => handleDeleteTestCase(testCase.id)}
                                  className={styles.btnRemoveTable}
                                  title="Xóa"
                                >
                                  <Trash2 size={16} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Edit Test Case Modal */}
              <Modal
                isOpen={showEditTestCase}
                onClose={() => setShowEditTestCase(false)}
                title="Chỉnh sửa trường hợp kiểm thử"
                maxWidth="600px"
              >
                <div className={styles.modalForm}>
                  <div className={styles.formGroup}>
                    <label>CV ID:</label>
                    <input 
                      type="text"
                      value={editCvId}
                      onChange={(e) => setEditCvId(e.target.value)}
                      placeholder="CV ID"
                      className={styles.input}
                    />
                  </div>

                  <div className={styles.formGroup}>
                    <label>Job ID:</label>
                    <input 
                      type="text"
                      value={editJobId}
                      onChange={(e) => setEditJobId(e.target.value)}
                      placeholder="Job ID"
                      className={styles.input}
                    />
                  </div>

                  <div className={styles.formGroup}>
                    <label>Reference Output (JSON - Optional):</label>
                    <textarea 
                      value={editReferenceOutput}
                      onChange={(e) => setEditReferenceOutput(e.target.value)}
                      placeholder='{"expected": "output"}'
                      className={styles.textarea}
                      rows={5}
                    />
                  </div>

                  <div className={styles.formGroup}>
                    <label>Metadata (JSON - Optional):</label>
                    <textarea 
                      value={editMetadata}
                      onChange={(e) => setEditMetadata(e.target.value)}
                      placeholder='{"note": "test case note"}'
                      className={styles.textarea}
                      rows={3}
                    />
                  </div>

                  <div className={styles.modalActions}>
                    <button 
                      onClick={() => setShowEditTestCase(false)}
                      className={styles.btnCancel}
                      disabled={loading}
                    >
                      Hủy
                    </button>
                    <button 
                      onClick={handleUpdateTestCase}
                      disabled={loading || !editCvId || !editJobId}
                      className={styles.btnPrimary}
                    >
                      {loading ? "Đang cập nhật..." : "Cập nhật"}
                    </button>
                  </div>
                </div>
              </Modal>
            </div>
          </Modal>
        </div>
      </motion.div>
    );
  }

  function renderResultsTab() {
    return (
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={styles.content}
      >
        {/* Sessions List */}
        <div className={styles.sessionsPanel}>
          <h2><BarChart3 size={24} /> Tất cả các phiên</h2>
          
          {sessions.length === 0 ? (
            <p className={styles.empty}>Chưa có phiên benchmark nào. Hãy chạy benchmark đầu tiên của bạn!</p>
          ) : (
            <div className={styles.sessionsList}>
              {sessions.map((session) => (
                <div 
                  key={session.id} 
                  className={`${styles.sessionCard} ${selectedSession === session.id ? styles.selected : ''}`}
                  onClick={() => handleViewSession(session.id)}
                >
                  <div className={styles.sessionHeader}>
                    <span className={`${styles.status} ${styles[session.status]}`}>
                      {session.status === 'completed' ? 'Hoàn tất' : 
                       session.status === 'failed' ? 'Thất bại' : 
                       session.status === 'running' ? 'Đang chạy' : session.status}
                    </span>
                    <span className={styles.date}>
                      {new Date(session.created_at).toLocaleString()}
                    </span>
                  </div>
                  
                  <div className={styles.sessionInfo}>
                    <div>
                      <strong>Xử lý:</strong> {session.model_config?.parsing_model || 'N/A'}
                    </div>
                    <div>
                      <strong>Chiến lược:</strong> {session.model_config?.evaluation_strategy || 'N/A'}
                    </div>
                    {session.overall_score !== null && (
                      <div className={styles.score}>
                        <strong>Điểm:</strong> {(session.overall_score * 100).toFixed(1)}%
                      </div>
                    )}
                  </div>

                  {session.status === "completed" && (
                    <div className={styles.sessionActions}>
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleExport(session.id, 'csv'); }}
                        className={styles.btnExport}
                      >
                        <Download size={14} /> CSV
                      </button>
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleExport(session.id, 'json'); }}
                        className={styles.btnExport}
                      >
                        <Download size={14} /> JSON
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Session Details Modal */}
        <Modal
          isOpen={!!sessionDetails}
          onClose={() => setSessionDetails(null)}
          title={`Chi tiết phiên: ${sessionDetails?.session?.id?.substring(0, 8)}...`}
          maxWidth="1100px"
        >
          <div className={styles.modalScrollContent}>
            <div className={styles.summary}>
              <div className={styles.summaryCard}>
                <h3>Điểm tổng quan</h3>
                <div className={styles.bigScore}>
                  {sessionDetails?.session.overall_score 
                    ? (sessionDetails?.session.overall_score * 100).toFixed(1) + '%'
                    : 'N/A'}
                </div>
              </div>
              
              <div className={styles.summaryCard}>
                <h3>Tổng độ trễ</h3>
                <div className={styles.bigNumber}>
                  {sessionDetails?.session.total_latency_ms 
                    ? (sessionDetails?.session.total_latency_ms / 1000).toFixed(1) + 's'
                    : 'N/A'}
                </div>
              </div>
              
              <div className={styles.summaryCard}>
                <h3>Tổng Token</h3>
                <div className={styles.bigNumber}>
                  {sessionDetails?.session.total_tokens?.toLocaleString() || 'N/A'}
                </div>
              </div>
            </div>

            <div className={styles.sectionHeader}>
              <h3><Activity size={20} /> Kết quả từng trường hợp</h3>
            </div>
            
            <div className={styles.tableWrapper}>
              <table className={styles.testCasesTable}>
                <thead>
                  <tr>
                    <th>Test Case</th>
                    <th>Điểm</th>
                    <th>Trung thực</th>
                    <th>Liên quan</th>
                    <th>Đầy đủ</th>
                    <th>Độ trễ</th>
                    <th>Tokens</th>
                    <th>Trạng thái</th>
                  </tr>
                </thead>
                <tbody>
                  {sessionDetails?.results.map((result: BenchmarkResult) => {
                    const metrics = result.metrics?.aggregated || result.metrics || {};
                    
                    return (
                      <tr key={result.id}>
                        <td className={styles.idCol}>{result.test_case_id ? result.test_case_id.substring(0, 8) : 'N/A'}...</td>
                        <td className={styles.scoreCell}>
                          {(result.score * 100).toFixed(1)}%
                        </td>
                        <td>{(metrics.faithfulness * 100).toFixed(0)}%</td>
                        <td>{(metrics.relevancy * 100).toFixed(0)}%</td>
                        <td>{(metrics.completeness * 100).toFixed(0)}%</td>
                        <td>{result.latency_ms}ms</td>
                        <td>{(result.prompt_tokens + result.completion_tokens).toLocaleString()}</td>
                        <td>
                          <span className={`${styles.statusBadge} ${styles[result.status]}`}>
                            {result.status === 'success' ? 'Thành công' : 
                             result.status === 'failed' ? 'Thất bại' : result.status}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Judge Breakdown for Dual Judge */}
            {sessionDetails?.session.model_config?.evaluation_strategy === "dual_judge" && (
              <div className={styles.judgeBreakdownSection}>
                <div className={styles.sectionHeader}>
                  <h3>👥 So sánh mô hình đánh giá</h3>
                </div>
                <div className={styles.judgeGrid}>
                  {sessionDetails?.results.map((result: BenchmarkResult) => {
                    const primary = result.metrics?.judge_primary;
                    const secondary = result.metrics?.judge_secondary;
                    
                    if (!primary || !secondary) return null;
                    
                    return (
                      <div key={result.id} className={styles.judgeCard}>
                        <div className={styles.judgeCardHeader}>
                          <h4>Case ID: {result.test_case_id.substring(0, 8)}...</h4>
                          <span className={styles.aggMethod}>{result.metrics.aggregation_method}</span>
                        </div>
                        <div className={styles.judgeComparison}>
                          <div className={styles.judgeColumn}>
                            <h5>Chính: {sessionDetails?.session.model_config.judge_model_primary}</h5>
                            <div className={styles.judgeMetric}><span>Faith:</span> {(primary.faithfulness * 100).toFixed(0)}%</div>
                            <div className={styles.judgeMetric}><span>Rel:</span> {(primary.relevancy * 100).toFixed(0)}%</div>
                            <div className={styles.judgeMetric}><span>Comp:</span> {(primary.completeness * 100).toFixed(0)}%</div>
                          </div>
                          
                          <div className={styles.judgeColumn}>
                            <h5>Phụ: {sessionDetails?.session.model_config.judge_model_secondary}</h5>
                            <div className={styles.judgeMetric}><span>Faith:</span> {(secondary.faithfulness * 100).toFixed(0)}%</div>
                            <div className={styles.judgeMetric}><span>Rel:</span> {(secondary.relevancy * 100).toFixed(0)}%</div>
                            <div className={styles.judgeMetric}><span>Comp:</span> {(secondary.completeness * 100).toFixed(0)}%</div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </Modal>
      </motion.div>
    );
  }

  // ========================================================================
  // MAIN RENDER
  // ========================================================================

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <motion.h1 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Activity size={40} className="text-primary" /> Hệ thống Benchmark LLM
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          Chạy benchmark với đánh giá dual judge và lựa chọn mô hình linh hoạt
        </motion.p>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {/* Tab Navigation */}
      <div className={styles.tabs}>
        <button 
          className={`${styles.tab} ${activeTab === "run" ? styles.active : ""}`}
          onClick={() => setActiveTab("run")}
        >
          <Play size={18} /> Chạy Benchmark
        </button>
        <button 
          className={`${styles.tab} ${activeTab === "quick" ? styles.active : ""}`}
          onClick={() => setActiveTab("quick")}
        >
          <Zap size={18} /> Kiểm tra nhanh
        </button>
        <button 
          className={`${styles.tab} ${activeTab === "testsets" ? styles.active : ""}`}
          onClick={() => setActiveTab("testsets")}
        >
          <Layers size={18} /> Bộ kiểm thử
        </button>
        <button 
          className={`${styles.tab} ${activeTab === "results" ? styles.active : ""}`}
          onClick={() => setActiveTab("results")}
        >
          <BarChart3 size={18} /> Kết quả
        </button>
      </div>

      {/* Tab Content */}
      <div className={styles.tabContent}>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {activeTab === "run" && renderRunBenchmarkTab()}
            {activeTab === "quick" && renderQuickTestTab()}
            {activeTab === "testsets" && renderTestSetsTab()}
            {activeTab === "results" && renderResultsTab()}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

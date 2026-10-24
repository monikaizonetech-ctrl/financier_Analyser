import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api, { apiErrorMessage } from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";
import { Badge, ConfirmDialog } from "../components/Common.jsx";
import ReportResultModal from "./ReportResultModal.jsx";

const TYPE_CONFIG = {
  BSA: {
    label: "Bank Statement Analysis",
    shortLabel: "BSA",
    icon: "🏦",
    desc: "Analyze bank transactions, cashflows, and banking health metrics",
    bgGradient: "from-blue-600 via-brand-600 to-indigo-700",
  },
  GST: {
    label: "GST Return Analysis",
    shortLabel: "GST",
    icon: "🧾",
    desc: "Analyze GST filings, GSTR-3B vs 2A/2B reconciliations, and tax compliance",
    bgGradient: "from-emerald-600 via-teal-600 to-slate-800",
  },
  ITR: {
    label: "ITR Computation Analysis",
    shortLabel: "ITR",
    icon: "📑",
    desc: "Analyze Income Tax Returns, balance sheets, and financial disclosures",
    bgGradient: "from-violet-600 via-purple-600 to-slate-800",
  },
};

export default function UploadReport() {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotification();
  const fileInputRef = useRef(null);

  const [report, setReport] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analysing, setAnalysing] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [selectedFileForResult, setSelectedFileForResult] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);
  const [analysisProgress, setAnalysisProgress] = useState({
    current: 0,
    total: 0,
    percent: 0,
    message: "",
    stage: "idle",
  });

  // Password Unlock & Authenticity Modal States
  const [unlockModalFile, setUnlockModalFile] = useState(null);
  const [passwordInput, setPasswordInput] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [unlockError, setUnlockError] = useState("");
  const [unlocking, setUnlocking] = useState(false);
  const [attempts, setAttempts] = useState({});
  const [lockouts, setLockouts] = useState({});
  const [reasonsPopoverFile, setReasonsPopoverFile] = useState(null);

  // 60-second lockout timer countdown
  useEffect(() => {
    const timer = setInterval(() => {
      setLockouts((prev) => {
        let changed = false;
        const next = { ...prev };
        for (const [id, sec] of Object.entries(next)) {
          if (sec > 1) {
            next[id] = sec - 1;
            changed = true;
          } else if (sec === 1) {
            delete next[id];
            changed = true;
          }
        }
        return changed ? next : prev;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const fetchReport = async () => {
    try {
      const res = await api.get(`/reports/${reportId}`);
      setReport(res.data);
    } catch (err) {
      notify(apiErrorMessage(err, "Could not load report details"), "error");
    }
  };

  useEffect(() => {
    fetchReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId]);

  useEffect(() => {
    if (report?.status === "Processing" && !analysing) {
      setAnalysing(true);
      const pollInterval = setInterval(async () => {
        try {
          const pRes = await api.get(`/reports/${reportId}/progress`);
          if (pRes?.data) {
            setAnalysisProgress(pRes.data);
            if (pRes.data.status !== "Processing") {
              clearInterval(pollInterval);
              setAnalysing(false);
              fetchReport();
            }
          }
        } catch {
          // ignore
        }
      }, 400);
      return () => clearInterval(pollInterval);
    }
  }, [report?.status, analysing, reportId]);

  const processUploadFiles = async (files) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
        await api.post(`/reports/${reportId}/files`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }
      notify(`${files.length} file(s) uploaded successfully`);
      await fetchReport();
    } catch (err) {
      notify(apiErrorMessage(err, "Upload failed"), "error");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    processUploadFiles(files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) {
      processUploadFiles(files);
    }
  };

  const hasLockedFiles = report?.files?.some((f) => 
    f.file_status === "Password required" || 
    (f.password_protected && f.file_status !== "Processed" && f.file_status !== "Unlocked")
  );
  const allProcessed = (report?.files?.length || 0) > 0 && report.files.every((f) => f.file_status === "Processed");

  const handleUnlockSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!unlockModalFile || !passwordInput) return;
    const fId = unlockModalFile.id;
    if (lockouts[fId] > 0) return;

    setUnlocking(true);
    setUnlockError("");
    try {
      await api.post(`/reports/${reportId}/files/${fId}/unlock`, {
        password: passwordInput,
      });
      notify("Statement unlocked successfully");
      setAttempts((prev) => ({ ...prev, [fId]: 0 }));
      setPasswordInput("");
      setUnlockModalFile(null);
      await fetchReport();
    } catch (err) {
      const currentAttempts = (attempts[fId] || 0) + 1;
      setAttempts((prev) => ({ ...prev, [fId]: currentAttempts }));
      if (currentAttempts >= 5) {
        setLockouts((prev) => ({ ...prev, [fId]: 60 }));
        setUnlockError("Incorrect password. 5 attempts reached. Row locked for 60 seconds.");
        setTimeout(() => {
          setUnlockModalFile(null);
          setPasswordInput("");
        }, 1800);
      } else {
        setUnlockError(`Incorrect password, try again (${5 - currentAttempts} attempts remaining)`);
      }
    } finally {
      setUnlocking(false);
    }
  };

  const handleAnalyse = async () => {
    if (!report?.files?.length) {
      notify("Please upload at least one statement file before analysing", "warning");
      return;
    }
    if (hasLockedFiles) {
      notify("Please unlock all password-protected files before starting analysis", "warning");
      return;
    }
    setAnalysing(true);
    setAnalysisProgress({
      current: 0,
      total: 0,
      percent: 0,
      message: "Initializing analysis...",
      stage: "starting",
    });

    const pollInterval = setInterval(async () => {
      try {
        const pRes = await api.get(`/reports/${reportId}/progress`);
        if (pRes?.data) {
          setAnalysisProgress(pRes.data);
        }
      } catch {
        // silent polling error
      }
    }, 350);

    try {
      const res = await api.post(`/reports/${reportId}/analyse`, {});
      setAnalysisProgress({
        current: 100,
        total: 100,
        percent: 100,
        message: "Analysis complete. Your report is ready!",
        stage: "completed",
      });
      // Brief pause to allow the user to view 100% completion
      await new Promise((resolve) => setTimeout(resolve, 500));
      setReport(res.data);
      notify("Analysis complete. Your report is ready.");
      setShowResult(true);
    } catch (err) {
      notify(apiErrorMessage(err, "Analysis failed"), "error");
    } finally {
      clearInterval(pollInterval);
      setAnalysing(false);
    }
  };

  const confirmDeleteFile = async () => {
    if (!fileToDelete) return;
    try {
      await api.delete(`/reports/${reportId}/files/${fileToDelete.id}`);
      notify("File removed");
      await fetchReport();
    } catch (err) {
      notify(apiErrorMessage(err, "Could not remove file"), "error");
    } finally {
      setFileToDelete(null);
    }
  };

  if (!report) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="flex items-center gap-3 text-gray-500 text-sm font-medium">
          <svg className="animate-spin h-5 w-5 text-brand-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          Loading workspace details...
        </div>
      </div>
    );
  }

  const typeMeta = TYPE_CONFIG[report.report_type] || {
    label: `${report.report_type} Analysis`,
    shortLabel: report.report_type,
    icon: "📊",
    desc: "Financial data statement analysis",
    bgGradient: "from-slate-800 to-slate-900",
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800 pb-16">
      {/* Top Header Workspace Navbar */}
      <header className={`bg-gradient-to-r ${typeMeta.bgGradient} text-white shadow-md`}>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <button
            onClick={() => navigate("/my-reports")}
            className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-3 py-2 rounded-lg backdrop-blur-sm transition-all self-start sm:self-auto"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Reports
          </button>

          <div className="text-center">
            <div className="flex items-center justify-center gap-2 flex-wrap">
              <span className="text-xl">{typeMeta.icon}</span>
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-white">{report.name}</h1>
              <Badge label={report.status} />
            </div>
            <p className="text-xs text-white/70 mt-0.5">{typeMeta.label}</p>
          </div>

          <div className="flex items-center gap-2">
            {report.status === "Ready to use" && allProcessed && (
              <button
                onClick={() => setShowResult(true)}
                className="inline-flex items-center gap-1.5 bg-white text-brand-700 hover:bg-brand-50 text-xs font-semibold px-3 py-2 rounded-lg shadow-sm transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                View Result
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-3 sm:px-6 mt-6 sm:mt-8 space-y-5 sm:space-y-6">
        {/* Metadata Summary Banner */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/80 p-4 sm:p-5 grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 md:divide-x divide-gray-100">
          <div className="md:pr-4">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">Applicant / Entity</span>
            <span className="text-xs sm:text-sm font-semibold text-gray-900 truncate block mt-0.5">{report.name}</span>
          </div>
          <div className="md:px-4">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">Reference ID</span>
            <span className="text-xs sm:text-sm font-mono text-gray-700 truncate block mt-0.5">{report.reference_id || "N/A"}</span>
          </div>
          <div className="md:px-4">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">Module Type</span>
            <span className="text-xs sm:text-sm font-semibold text-brand-600 truncate block mt-0.5">{typeMeta.shortLabel}</span>
          </div>
          <div className="md:pl-4">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">Statements Uploaded</span>
            <span className="text-xs sm:text-sm font-semibold text-gray-900 truncate block mt-0.5">
              {report.files.length} {report.files.length === 1 ? "File" : "Files"}
            </span>
          </div>
        </div>

        {/* Drag & Drop File Upload Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
            isDragging
              ? "border-brand-500 bg-brand-50/70 scale-[1.005]"
              : "border-gray-300 hover:border-brand-400 bg-white hover:bg-gray-50/60 shadow-sm"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            hidden
            disabled={uploading}
            onChange={handleFileChange}
          />
          <div className="flex flex-col items-center justify-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-brand-50 text-brand-600 flex items-center justify-center text-xl shadow-inner">
              {uploading ? (
                <svg className="animate-spin h-6 w-6 text-brand-600" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              )}
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-800">
                {uploading ? "Uploading files..." : "Click to upload or drag & drop statements here"}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Supported formats: <span className="font-medium text-gray-700">PDF, CSV, XLS, XLSX</span> (Max 50MB per file)
              </p>
            </div>
            <button
              type="button"
              disabled={uploading}
              className="mt-2 text-xs font-semibold text-brand-600 bg-brand-50 hover:bg-brand-100 border border-brand-200 px-3.5 py-1.5 rounded-md transition-colors"
            >
              Browse Files
            </button>
          </div>
        </div>

        {/* Uploaded Documents Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/80 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h2 className="font-bold text-gray-900 text-sm sm:text-base flex items-center gap-2">
                <span>📄</span> Uploaded Statement Files
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Review uploaded files before starting AI verification and automated financial analysis
              </p>
            </div>
            {report.files.length > 0 && (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="text-xs font-medium text-brand-600 hover:text-brand-700 bg-brand-50 hover:bg-brand-100 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                </svg>
                Add More
              </button>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 text-gray-500 text-xs font-semibold uppercase tracking-wider border-b border-gray-100">
                <tr>
                  <th className="px-6 py-3.5 w-16 text-center">S.No</th>
                  <th className="px-6 py-3.5">File Name</th>
                  <th className="px-6 py-3.5">Type</th>
                  <th className="px-6 py-3.5">Year / Period</th>
                  <th className="px-6 py-3.5">File Status</th>
                  <th className="px-6 py-3.5">Authenticity</th>
                  <th className="px-6 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {report.files.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center">
                      <div className="flex flex-col items-center justify-center space-y-2">
                        <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-gray-400 text-lg">
                          📁
                        </div>
                        <p className="text-sm font-medium text-gray-500">No statements uploaded yet</p>
                        <p className="text-xs text-gray-400">
                          Use the upload box above to add bank statements, GST, or ITR files.
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  report.files.map((f, idx) => (
                    <tr key={f.id} className="hover:bg-gray-50/70 transition-colors">
                      <td className="px-6 py-4 text-center font-medium text-gray-400 text-xs">{f.s_no || idx + 1}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <span className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-xs font-semibold flex-shrink-0">
                            {f.file_name.endsWith(".pdf")
                              ? "PDF"
                              : f.file_name.endsWith(".xlsx") || f.file_name.endsWith(".csv")
                              ? "XLS"
                              : "DOC"}
                          </span>
                          <span className="font-semibold text-gray-800 text-sm truncate max-w-xs" title={f.file_name}>
                            {f.file_name}
                          </span>
                          {f.bank_name && f.bank_name !== "-" && (
                            <span className="text-[11px] text-gray-500 font-normal">
                              • {f.bank_name}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-gray-600 text-xs font-medium">{f.sub_type || "-"}</td>
                      <td className="px-6 py-4 text-gray-600 text-xs font-medium">{f.year || "-"}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <Badge label={f.file_status} />
                          {(f.file_status === "Password required" || (f.password_protected && f.file_status !== "Processed" && f.file_status !== "Unlocked")) && (
                            lockouts[f.id] > 0 ? (
                              <span className="text-[11px] font-semibold text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded">
                                Locked ({lockouts[f.id]}s)
                              </span>
                            ) : (
                              <button
                                type="button"
                                onClick={() => {
                                  setUnlockModalFile(f);
                                  setPasswordInput("");
                                  setUnlockError("");
                                  setShowPassword(false);
                                }}
                                className="text-[11px] font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-300 px-2.5 py-1 rounded-md transition-colors shadow-2xs inline-flex items-center gap-1 cursor-pointer hover:shadow-xs active:scale-95"
                              >
                                🔑 Enter password
                              </button>
                            )
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <Badge label={f.authenticity} />
                          {f.password_protected && (
                            <span title="Original file was encrypted/password-protected" className="text-sm">
                              🔒
                            </span>
                          )}
                          {f.owner_restricted && (
                            <span className="text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-slate-200" title="Restricted PDF opened with reader permissions">
                              Restricted PDF (opened)
                            </span>
                          )}
                          {f.authenticity_reasons && f.authenticity_reasons.length > 0 && (
                            <button
                              type="button"
                              onClick={() => setReasonsPopoverFile(f)}
                              className="text-gray-400 hover:text-brand-600 text-xs p-1 rounded-full hover:bg-gray-100 transition-colors"
                              title="View authenticity checks & details"
                            >
                              ℹ️
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {report.status === "Ready to use" && (
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedFileForResult(f.file_name);
                                setShowResult(true);
                              }}
                              className="text-brand-600 hover:text-brand-800 p-1.5 rounded-md hover:bg-brand-50 transition-colors cursor-pointer"
                              title={`View report for ${f.file_name}`}
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                            </button>
                          )}
                          <button
                            type="button"
                            className="text-gray-400 hover:text-red-600 p-1.5 rounded-md hover:bg-red-50 transition-colors cursor-pointer"
                            title="Remove file"
                            onClick={() => setFileToDelete(f)}
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </td>

                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Real-time Analysis Progress Card */}
        {analysing && (
          <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/60 border border-slate-200/80 p-5 sm:p-6 overflow-hidden relative transition-all duration-300">
            {/* Top Accent Bar */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 via-indigo-600 to-emerald-500"></div>
            
            {/* Ambient Background Light */}
            <div className="absolute -top-12 -right-12 w-48 h-48 bg-blue-400/10 rounded-full blur-3xl pointer-events-none"></div>

            {/* Header: Title, Live Tag and Stats */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-3">
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-600"></span>
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-bold text-slate-900 tracking-tight">
                      Live Statement Analysis Progress
                    </h4>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-200/80 shadow-2xs">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse"></span>
                      LIVE STREAM
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 font-normal">
                    Real-time document parser, OCR &amp; transactional classification active
                  </p>
                </div>
              </div>

              {/* Progress Count Badge */}
              <div className="flex items-center gap-3 self-start sm:self-center bg-slate-50/90 px-3.5 py-1.5 rounded-xl border border-slate-200/80 shadow-xs">
                {analysisProgress.total > 0 && (
                  <span className="text-xs font-medium text-slate-600">
                    Page <strong className="text-slate-900 font-bold">{analysisProgress.current}</strong> of{" "}
                    <strong className="text-slate-700 font-semibold">{analysisProgress.total}</strong>
                  </span>
                )}
                <span className="text-xs font-mono font-extrabold text-white bg-gradient-to-r from-blue-600 to-indigo-600 px-2.5 py-0.5 rounded-md shadow-xs shadow-blue-500/20">
                  {analysisProgress.percent}%
                </span>
              </div>
            </div>

            {/* Vibrant High-Contrast Progress Bar Track */}
            <div className="relative my-2">
              <div className="h-4 bg-slate-100 rounded-full overflow-hidden p-0.5 border border-slate-200/90 shadow-inner relative">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-500 relative transition-all duration-300 ease-out flex items-center justify-end shadow-xs overflow-hidden"
                  style={{
                    width: `${Math.min(Math.max(analysisProgress.percent || 0, 3), 100)}%`,
                  }}
                >
                  {/* Smooth Shimmer Glow passing through */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/35 to-transparent animate-shimmer pointer-events-none rounded-full"></div>

                  {/* Leading Spark Tip */}
                  <div className="relative z-10 h-full w-2.5 bg-white rounded-full shadow-[0_0_8px_rgba(255,255,255,0.9)] flex items-center justify-center mr-0.5">
                    <div className="w-0.5 h-2 bg-blue-500 rounded-full"></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Current Status Message and Feed Indicator */}
            <div className="mt-2.5 mb-4 flex flex-col sm:flex-row sm:items-center justify-between text-xs gap-1.5">
              <div className="flex items-center gap-2 text-slate-800">
                <svg className="w-4 h-4 text-blue-600 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span className="font-semibold text-slate-900">
                  {analysisProgress.message || "Processing statement data..."}
                </span>
              </div>
              <span className="text-slate-500 font-medium text-[11px] sm:text-right flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                {analysisProgress.percent >= 100 ? "Reconciliation complete" : "Extracting financial data in real time..."}
              </span>
            </div>

            {/* Multi-stage Milestones Stepper */}
            <div className="pt-3 border-t border-slate-100 grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {/* Step 1: Ingestion & Reading */}
              {(() => {
                const done = analysisProgress.percent >= 15;
                const active = analysisProgress.percent > 0 && analysisProgress.percent < 15;
                return (
                  <div
                    className={`flex items-center gap-2.5 p-2 rounded-xl border text-xs transition-all ${
                      done
                        ? "bg-emerald-50/70 border-emerald-200/80 text-emerald-900"
                        : active
                        ? "bg-blue-50/90 border-blue-400 text-blue-950 shadow-xs ring-2 ring-blue-500/20"
                        : "bg-slate-50/60 border-slate-200/60 text-slate-400"
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${
                        done
                          ? "bg-emerald-600 text-white shadow-2xs"
                          : active
                          ? "bg-blue-600 text-white animate-pulse"
                          : "bg-slate-200 text-slate-500"
                      }`}
                    >
                      {done ? "✓" : active ? "1" : "1"}
                    </div>
                    <div className="truncate">
                      <p className="font-semibold text-[11px] truncate">Ingestion</p>
                      <p className="text-[10px] text-slate-500 truncate">
                        {done ? "Verified" : active ? "Reading..." : "Queued"}
                      </p>
                    </div>
                  </div>
                );
              })()}

              {/* Step 2: Page Extraction */}
              {(() => {
                const done = analysisProgress.percent >= 85;
                const active = analysisProgress.percent >= 15 && analysisProgress.percent < 85;
                return (
                  <div
                    className={`flex items-center gap-2.5 p-2 rounded-xl border text-xs transition-all ${
                      done
                        ? "bg-emerald-50/70 border-emerald-200/80 text-emerald-900"
                        : active
                        ? "bg-blue-50/90 border-blue-400 text-blue-950 shadow-xs ring-2 ring-blue-500/20"
                        : "bg-slate-50/60 border-slate-200/60 text-slate-400"
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${
                        done
                          ? "bg-emerald-600 text-white shadow-2xs"
                          : active
                          ? "bg-blue-600 text-white animate-pulse"
                          : "bg-slate-200 text-slate-500"
                      }`}
                    >
                      {done ? "✓" : active ? "2" : "2"}
                    </div>
                    <div className="truncate">
                      <p className="font-semibold text-[11px] truncate">Page OCR</p>
                      <p className="text-[10px] text-slate-500 truncate">
                        {done
                          ? "Complete"
                          : active
                          ? `Extracting ${analysisProgress.total ? `${analysisProgress.current}/${analysisProgress.total}` : "..."}`
                          : "Queued"}
                      </p>
                    </div>
                  </div>
                );
              })()}

              {/* Step 3: Categorization */}
              {(() => {
                const done = analysisProgress.percent >= 98;
                const active = analysisProgress.percent >= 85 && analysisProgress.percent < 98;
                return (
                  <div
                    className={`flex items-center gap-2.5 p-2 rounded-xl border text-xs transition-all ${
                      done
                        ? "bg-emerald-50/70 border-emerald-200/80 text-emerald-900"
                        : active
                        ? "bg-blue-50/90 border-blue-400 text-blue-950 shadow-xs ring-2 ring-blue-500/20"
                        : "bg-slate-50/60 border-slate-200/60 text-slate-400"
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${
                        done
                          ? "bg-emerald-600 text-white shadow-2xs"
                          : active
                          ? "bg-blue-600 text-white animate-pulse"
                          : "bg-slate-200 text-slate-500"
                      }`}
                    >
                      {done ? "✓" : active ? "3" : "3"}
                    </div>
                    <div className="truncate">
                      <p className="font-semibold text-[11px] truncate">Taxonomy</p>
                      <p className="text-[10px] text-slate-500 truncate">
                        {done ? "Categorized" : active ? "Classifying..." : "Queued"}
                      </p>
                    </div>
                  </div>
                );
              })()}

              {/* Step 4: Reconciliation */}
              {(() => {
                const done = analysisProgress.percent >= 100;
                const active = analysisProgress.percent >= 98 && analysisProgress.percent < 100;
                return (
                  <div
                    className={`flex items-center gap-2.5 p-2 rounded-xl border text-xs transition-all ${
                      done
                        ? "bg-emerald-50/70 border-emerald-200/80 text-emerald-900"
                        : active
                        ? "bg-blue-50/90 border-blue-400 text-blue-950 shadow-xs ring-2 ring-blue-500/20"
                        : "bg-slate-50/60 border-slate-200/60 text-slate-400"
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${
                        done
                          ? "bg-emerald-600 text-white shadow-2xs"
                          : active
                          ? "bg-blue-600 text-white animate-pulse"
                          : "bg-slate-200 text-slate-500"
                      }`}
                    >
                      {done ? "✓" : active ? "4" : "4"}
                    </div>
                    <div className="truncate">
                      <p className="font-semibold text-[11px] truncate">Reconciliation</p>
                      <p className="text-[10px] text-slate-500 truncate">
                        {done ? "Integrity OK" : active ? "Verifying..." : "Queued"}
                      </p>
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>
        )}

        {/* Bottom Actions Card */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/80 p-5 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-xs text-gray-500 text-center sm:text-left">
            {report.files.length > 0 ? (
              <span className="text-emerald-700 font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                Ready for analysis with {report.files.length} statement file(s)
              </span>
            ) : (
              <span>Upload statement files above to enable analysis</span>
            )}
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <button
              className="btn-secondary flex-1 sm:flex-none text-xs"
              onClick={() => navigate("/my-reports")}
            >
              Cancel
            </button>

            <button
              className={`btn-primary flex-1 sm:flex-none text-xs font-semibold py-2.5 px-6 shadow-sm inline-flex items-center justify-center gap-2 ${
                (analysing || report.files.length === 0 || hasLockedFiles) ? "opacity-60 cursor-not-allowed" : ""
              }`}
              disabled={analysing || report.files.length === 0 || hasLockedFiles}
              title={hasLockedFiles ? "Unlock password-protected files before starting analysis" : ""}
              onClick={handleAnalyse}
            >
              {analysing ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <span>
                    {analysisProgress.total > 0
                      ? `${analysisProgress.percent}% (Page ${analysisProgress.current}/${analysisProgress.total})`
                      : `${analysisProgress.percent ? `${analysisProgress.percent}%` : "Processing..."}`}
                  </span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Analyse Statements
                </>
              )}
            </button>

            {report.status === "Ready to use" && (
              <button
                className={`text-xs font-medium px-4 py-2.5 rounded-md transition-colors shadow-sm inline-flex items-center gap-1.5 ${
                  allProcessed
                    ? "bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer"
                    : "bg-gray-200 text-gray-400 cursor-not-allowed"
                }`}
                disabled={!allProcessed}
                title={!allProcessed ? "Every file must be Unlocked and Processed before viewing report" : ""}
                onClick={() => setShowResult(true)}
              >
                View Report Output
              </button>
            )}
          </div>
        </div>
      </main>

      {/* Enter Password Modal */}
      {unlockModalFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-md bg-white rounded-xl shadow-2xl border border-gray-200 p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <span>🔒</span> Enter PDF Password
              </h3>
              <button
                onClick={() => setUnlockModalFile(null)}
                className="text-gray-400 hover:text-gray-600 text-xl font-bold leading-none"
              >
                &times;
              </button>
            </div>

            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">File Name</p>
              <p className="text-sm font-semibold text-gray-900 truncate mt-0.5">{unlockModalFile.file_name}</p>
            </div>

            <form onSubmit={handleUnlockSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Document Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={passwordInput}
                    onChange={(e) => setPasswordInput(e.target.value)}
                    disabled={unlocking || (lockouts[unlockModalFile.id] > 0)}
                    placeholder="Enter password to unlock..."
                    autoFocus
                    className="w-full text-sm px-3.5 py-2.5 pr-16 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-600 hover:text-gray-900 font-medium px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
                {unlockError && (
                  <p className="text-xs text-red-600 mt-1.5 font-medium flex items-center gap-1">
                    <span>⚠️</span> {unlockError}
                  </p>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  className="btn-secondary text-xs"
                  onClick={() => setUnlockModalFile(null)}
                  disabled={unlocking}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={unlocking || !passwordInput.trim() || (lockouts[unlockModalFile.id] > 0)}
                  className="btn-primary text-xs font-semibold px-4 py-2 inline-flex items-center gap-2"
                >
                  {unlocking ? "Decrypting..." : "Unlock"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Authenticity Findings Modal / Popover */}
      {reasonsPopoverFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-lg bg-white rounded-xl shadow-2xl border border-gray-200 p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <span>🛡️</span> Authenticity Inspection Findings
              </h3>
              <button
                onClick={() => setReasonsPopoverFile(null)}
                className="text-gray-400 hover:text-gray-600 text-xl font-bold leading-none"
              >
                &times;
              </button>
            </div>

            <div>
              <p className="text-xs text-gray-500 font-medium">File: <span className="text-gray-800 font-semibold">{reasonsPopoverFile.file_name}</span></p>
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs text-gray-500">Evaluation:</span>
                <Badge label={reasonsPopoverFile.authenticity} />
                {reasonsPopoverFile.password_protected && (
                  <span className="text-xs text-gray-600 flex items-center gap-1">
                    🔒 Password Protected
                  </span>
                )}
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-3.5 border border-gray-200 max-h-60 overflow-y-auto">
              <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Detailed Forensic Checks</h4>
              <ul className="text-xs space-y-1.5 text-gray-700 list-disc list-inside">
                {(reasonsPopoverFile.authenticity_reasons || ["No specific forensic anomalies found"]).map((r, i) => (
                  <li key={i} className="leading-relaxed">{r}</li>
                ))}
              </ul>
            </div>

            <div className="flex justify-end pt-1">
              <button
                className="btn-secondary text-xs"
                onClick={() => setReasonsPopoverFile(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal on File Deletion */}
      {fileToDelete && (
        <ConfirmDialog
          title="Remove File"
          message={`Are you sure you want to remove "${fileToDelete.file_name}" from this analysis report?`}
          confirmLabel="Remove File"
          danger={true}
          onConfirm={confirmDeleteFile}
          onCancel={() => setFileToDelete(null)}
        />
      )}

      {/* Results Modal */}
      {showResult && (
        <ReportResultModal
          report={report}
          activeFile={selectedFileForResult}
          onClose={() => {
            setShowResult(false);
            setSelectedFileForResult(null);
          }}
        />
      )}
    </div>
  );
}


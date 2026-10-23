import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api, { apiErrorMessage } from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";
import { Badge, ConfirmDialog } from "../components/Common.jsx";
import GSTResultModal from "./GSTResultModal.jsx";

const GSTR_SUBTYPES = [
  {
    value: "AUTO",
    label: "Auto-Detect",
    desc: "Auto Content-Based Detection",
    icon: "✨",
    color: "from-amber-500 to-orange-600",
    accepted: ".json,.csv,.xlsx,.xls,.pdf",
  },
  {
    value: "GSTR-1",
    label: "GSTR-1",
    desc: "Outward Supplies (Sales)",
    icon: "📤",
    color: "from-emerald-500 to-teal-600",
    accepted: ".json,.csv,.xlsx,.xls,.pdf",
  },
  {
    value: "GSTR-2B",
    label: "GSTR-2B",
    desc: "Auto-Drafted ITC Statement",
    icon: "📥",
    color: "from-blue-500 to-indigo-600",
    accepted: ".json,.csv,.xlsx,.xls,.pdf",
  },
  {
    value: "GSTR-3B",
    label: "GSTR-3B",
    desc: "Monthly Summary Return",
    icon: "📊",
    color: "from-violet-500 to-purple-600",
    accepted: ".json,.csv,.xlsx,.xls,.pdf",
  },
];

const subtype_meta = Object.fromEntries(GSTR_SUBTYPES.map((s) => [s.value, s]));

function SubtypePill({ value }) {
  const meta = subtype_meta[value] || { label: value, color: "from-gray-400 to-gray-600", icon: "📄" };
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] font-bold text-white bg-gradient-to-r ${meta.color} px-2 py-0.5 rounded-full shadow-sm`}>
      {meta.icon} {meta.label}
    </span>
  );
}

function fmt(n) {
  if (n === undefined || n === null || n === "-") return "—";
  const num = parseFloat(n);
  if (isNaN(num)) return String(n);
  return new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);
}

export default function GSTUploadReport() {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotification();
  const fileInputRef = useRef(null);

  const [report, setReport] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analysing, setAnalysing] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);
  const [selectedSubtype, setSelectedSubtype] = useState("AUTO");
  const [analysisProgress, setAnalysisProgress] = useState({
    current: 0,
    total: 0,
    percent: 0,
    message: "",
    stage: "idle",
  });

  const [unlockModalFile, setUnlockModalFile] = useState(null);
  const [passwordInput, setPasswordInput] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [unlockError, setUnlockError] = useState("");
  const [unlocking, setUnlocking] = useState(false);
  const [attempts, setAttempts] = useState({});
  const [lockouts, setLockouts] = useState({});
  const [reasonsPopoverFile, setReasonsPopoverFile] = useState(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setLockouts((prev) => {
        let changed = false;
        const next = { ...prev };
        for (const [id, sec] of Object.entries(next)) {
          if (sec > 1) { next[id] = sec - 1; changed = true; }
          else if (sec === 1) { delete next[id]; changed = true; }
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

  useEffect(() => { fetchReport(); }, [reportId]);

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
        } catch { }
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
        // Pass selected subtype if not AUTO so user override is respected
        const params = new URLSearchParams(
          selectedSubtype && selectedSubtype !== "AUTO" ? { sub_type: selectedSubtype } : {}
        );
        await api.post(`/reports/${reportId}/files?${params}`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }
      notify(
        selectedSubtype === "AUTO"
          ? `${files.length} file(s) uploaded (auto-identifying return types)`
          : `${files.length} file(s) uploaded as ${selectedSubtype}`
      );
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
  const handleDragOver = (e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); };
  const handleDragLeave = (e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); };
  const handleDrop = (e) => {
    e.preventDefault(); e.stopPropagation(); setIsDragging(false);
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) processUploadFiles(files);
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
    setUnlocking(true); setUnlockError("");
    try {
      await api.post(`/reports/${reportId}/files/${fId}/unlock`, { password: passwordInput });
      notify("File unlocked successfully");
      setAttempts((prev) => ({ ...prev, [fId]: 0 }));
      setPasswordInput(""); setUnlockModalFile(null);
      await fetchReport();
    } catch (err) {
      const ca = (attempts[fId] || 0) + 1;
      setAttempts((prev) => ({ ...prev, [fId]: ca }));
      if (ca >= 5) {
        setLockouts((prev) => ({ ...prev, [fId]: 60 }));
        setUnlockError("Incorrect password. 5 attempts reached. Row locked for 60 seconds.");
        setTimeout(() => { setUnlockModalFile(null); setPasswordInput(""); }, 1800);
      } else {
        setUnlockError(`Incorrect password, try again (${5 - ca} attempts remaining)`);
      }
    } finally { setUnlocking(false); }
  };

  const handleAnalyse = async () => {
    if (!report?.files?.length) { notify("Upload at least one GST return file before analysing", "warning"); return; }
    if (hasLockedFiles) { notify("Please unlock all password-protected files first", "warning"); return; }
    setAnalysing(true);
    setAnalysisProgress({ current: 0, total: 0, percent: 0, message: "Initializing GST analysis...", stage: "starting" });
    const pollInterval = setInterval(async () => {
      try {
        const pRes = await api.get(`/reports/${reportId}/progress`);
        if (pRes?.data) setAnalysisProgress(pRes.data);
      } catch { }
    }, 350);
    try {
      const res = await api.post(`/reports/${reportId}/analyse`, {});
      setAnalysisProgress({ current: 100, total: 100, percent: 100, message: "GST analysis complete!", stage: "completed" });
      await new Promise((r) => setTimeout(r, 500));
      setReport(res.data);
      notify("GST analysis complete. Report is ready.");
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
    } finally { setFileToDelete(null); }
  };

  if (!report) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-slate-100 flex items-center justify-center p-6">
        <div className="flex items-center gap-3 text-gray-500 text-sm font-medium">
          <svg className="animate-spin h-5 w-5 text-emerald-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          Loading GST workspace...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-emerald-50/30 to-teal-50/20 text-gray-800 pb-16">
      {/* Header */}
      <header className="bg-gradient-to-r from-emerald-700 via-teal-700 to-slate-800 text-white shadow-lg">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate("/my-reports")}
            className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-3 py-2 rounded-lg backdrop-blur-sm transition-all"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Reports
          </button>

          <div className="text-center">
            <div className="flex items-center justify-center gap-2">
              <span className="text-xl">🧾</span>
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-white">{report.name}</h1>
              <Badge label={report.status} />
            </div>
            <p className="text-xs text-white/70 mt-0.5">GST Return Analysis Workspace</p>
          </div>

          <div className="flex items-center gap-2">
            {report.status === "Ready to use" && allProcessed && (
              <button
                onClick={() => setShowResult(true)}
                className="inline-flex items-center gap-1.5 bg-white text-emerald-700 hover:bg-emerald-50 text-xs font-semibold px-3 py-2 rounded-lg shadow-sm transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                View GST Report
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 mt-8 space-y-6">

        {/* Metadata Banner */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/80 p-5 grid grid-cols-2 md:grid-cols-4 gap-4 divide-x divide-gray-100">
          <div className="pr-4">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">Entity / Applicant</span>
            <span className="text-sm font-semibold text-gray-900 truncate block mt-0.5">{report.name}</span>
          </div>
          <div className="px-4">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">Reference ID</span>
            <span className="text-sm font-mono text-gray-700 truncate block mt-0.5">{report.reference_id || "N/A"}</span>
          </div>
          <div className="px-4">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">Module</span>
            <span className="text-sm font-semibold text-emerald-600 truncate block mt-0.5">GST Analysis</span>
          </div>
          <div className="pl-4">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">Files Uploaded</span>
            <span className="text-sm font-semibold text-gray-900 truncate block mt-0.5">
              {report.files.length} {report.files.length === 1 ? "File" : "Files"}
            </span>
          </div>
        </div>

        {/* GSTR Subtype Selector Cards */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/80 p-5">
          <h2 className="text-sm font-bold text-gray-800 mb-1 flex items-center gap-2">
            <span>📋</span> Select Return Type Before Upload
          </h2>
          <p className="text-xs text-gray-500 mb-4">Choose the GSTR type for the files you're about to upload. Each file is tagged with the selected type.</p>
          <div className="grid grid-cols-3 gap-3">
            {GSTR_SUBTYPES.map((s) => (
              <button
                key={s.value}
                onClick={() => setSelectedSubtype(s.value)}
                className={`relative p-4 rounded-xl border-2 text-left transition-all duration-200 ${
                  selectedSubtype === s.value
                    ? "border-emerald-500 bg-emerald-50/60 shadow-md shadow-emerald-100/60 scale-[1.02]"
                    : "border-gray-200 bg-white hover:border-emerald-300 hover:bg-emerald-50/30"
                }`}
              >
                {selectedSubtype === s.value && (
                  <span className="absolute top-2 right-2 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                    </svg>
                  </span>
                )}
                <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${s.color} flex items-center justify-center text-lg mb-2 shadow-sm`}>
                  {s.icon}
                </div>
                <p className="text-sm font-bold text-gray-900">{s.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{s.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Drag & Drop Upload Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
            isDragging
              ? "border-emerald-500 bg-emerald-50/70 scale-[1.005]"
              : "border-gray-300 hover:border-emerald-400 bg-white hover:bg-gray-50/60 shadow-sm"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            hidden
            disabled={uploading}
            onChange={handleFileChange}
            accept=".json,.csv,.xlsx,.xls,.pdf"
          />
          <div className="flex flex-col items-center justify-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center text-xl shadow-inner">
              {uploading ? (
                <svg className="animate-spin h-6 w-6 text-emerald-600" fill="none" viewBox="0 0 24 24">
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
                {uploading ? "Uploading..." : (
                  <>Upload <SubtypePill value={selectedSubtype} /> return files here</>
                )}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Supported: <span className="font-medium text-gray-700">JSON (GSTN Portal), CSV, XLSX, PDF</span> (Max 50MB)
              </p>
            </div>
            <button
              type="button"
              disabled={uploading}
              className="mt-2 text-xs font-semibold text-emerald-600 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-3.5 py-1.5 rounded-md transition-colors"
            >
              Browse Files
            </button>
          </div>
        </div>

        {/* Uploaded Files Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/80 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h2 className="font-bold text-gray-900 text-sm sm:text-base flex items-center gap-2">
                <span>📁</span> Uploaded GST Return Files
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Review uploaded returns before starting automated tax extraction and reconciliation
              </p>
            </div>
            {report.files.length > 0 && (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="text-xs font-medium text-emerald-600 hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
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
                  <th className="px-6 py-3.5">GSTR Type</th>
                  <th className="px-6 py-3.5">Period / Year</th>
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
                        <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center text-2xl">🧾</div>
                        <p className="text-sm font-medium text-gray-500">No GST return files uploaded yet</p>
                        <p className="text-xs text-gray-400">
                          Upload GSTR-1, GSTR-2B or GSTR-3B files (JSON, CSV, XLSX, PDF) above
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
                          <span className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center text-xs font-semibold flex-shrink-0">
                            {f.file_name.endsWith(".json") ? "JSON" : f.file_name.endsWith(".pdf") ? "PDF" : "XLS"}
                          </span>
                          <span className="font-semibold text-gray-800 text-sm truncate max-w-xs" title={f.file_name}>
                            {f.file_name}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <SubtypePill value={f.sub_type || "GSTR-1"} />
                      </td>
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
                                onClick={() => { setUnlockModalFile(f); setPasswordInput(""); setUnlockError(""); setShowPassword(false); }}
                                className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 px-2.5 py-1 rounded-md transition-colors shadow-2xs inline-flex items-center gap-1 cursor-pointer"
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
                          {f.password_protected && <span title="Password-protected" className="text-sm">🔒</span>}
                          {f.authenticity_reasons?.length > 0 && (
                            <button
                              type="button"
                              onClick={() => setReasonsPopoverFile(f)}
                              className="text-gray-400 hover:text-emerald-600 text-xs p-1 rounded-full hover:bg-gray-100 transition-colors"
                              title="View details"
                            >ℹ️</button>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          className="text-gray-400 hover:text-red-600 p-1.5 rounded-md hover:bg-red-50 transition-colors"
                          title="Remove file"
                          onClick={() => setFileToDelete(f)}
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Analysis Progress */}
        {analysing && (
          <div className="bg-white rounded-2xl shadow-xl shadow-emerald-200/40 border border-emerald-200/60 p-5 sm:p-6 overflow-hidden relative">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-teal-500 to-blue-500" />
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-3">
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-600" />
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-bold text-slate-900">GST Return Analysis — Live</h4>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200/80">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
                      PROCESSING
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">Tax extraction, ITC reconciliation & compliance checks active</p>
                </div>
              </div>
              <div className="flex items-center gap-3 self-start sm:self-center bg-slate-50/90 px-3.5 py-1.5 rounded-xl border border-slate-200/80">
                <span className="text-xs font-mono font-extrabold text-white bg-gradient-to-r from-emerald-600 to-teal-600 px-2.5 py-0.5 rounded-md">
                  {analysisProgress.percent}%
                </span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="relative my-2">
              <div className="h-4 bg-slate-100 rounded-full overflow-hidden p-0.5 border border-slate-200/90 shadow-inner">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-teal-500 to-emerald-400 transition-all duration-300 ease-out flex items-center justify-end shadow-xs overflow-hidden"
                  style={{ width: `${Math.min(Math.max(analysisProgress.percent || 0, 3), 100)}%` }}
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer pointer-events-none rounded-full" />
                  <div className="relative z-10 h-full w-2.5 bg-white rounded-full shadow-[0_0_8px_rgba(255,255,255,0.9)] mr-0.5" />
                </div>
              </div>
            </div>

            <p className="text-xs font-semibold text-slate-700 mt-2 mb-4">{analysisProgress.message || "Extracting GST data..."}</p>

            {/* Steps */}
            <div className="pt-3 border-t border-slate-100 grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {[
                { label: "File Ingestion", sub: "Reading returns", done: 15, active: 0 },
                { label: "Tax Extraction", sub: "IGST/CGST/SGST", done: 60, active: 15 },
                { label: "ITC Matching", sub: "GSTR-1 vs 2B", done: 90, active: 60 },
                { label: "Compliance Check", sub: "3B reconciliation", done: 100, active: 90 },
              ].map((step, i) => {
                const done = analysisProgress.percent >= step.done;
                const active = analysisProgress.percent >= step.active && analysisProgress.percent < step.done;
                return (
                  <div key={i} className={`flex items-center gap-2.5 p-2 rounded-xl border text-xs transition-all ${
                    done ? "bg-emerald-50/70 border-emerald-200/80 text-emerald-900"
                    : active ? "bg-emerald-50/90 border-emerald-400 text-emerald-950 shadow-xs ring-2 ring-emerald-500/20"
                    : "bg-slate-50/60 border-slate-200/60 text-slate-400"
                  }`}>
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${
                      done ? "bg-emerald-600 text-white" : active ? "bg-emerald-600 text-white animate-pulse" : "bg-slate-200 text-slate-500"
                    }`}>{done ? "✓" : i + 1}</div>
                    <div className="truncate">
                      <p className="font-semibold text-[11px] truncate">{step.label}</p>
                      <p className="text-[10px] text-slate-500 truncate">{done ? "Complete" : active ? step.sub : "Queued"}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Bottom Actions */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/80 p-5 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-xs text-gray-500 text-center sm:text-left">
            {report.files.length > 0 ? (
              <span className="text-emerald-700 font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                {report.files.length} return file(s) ready for analysis
              </span>
            ) : (
              <span>Upload GST return files above to enable analysis</span>
            )}
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <button className="btn-secondary flex-1 sm:flex-none text-xs" onClick={() => navigate("/my-reports")}>
              Cancel
            </button>
            <button
              className={`btn-primary flex-1 sm:flex-none text-xs font-semibold py-2.5 px-6 shadow-sm inline-flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 ${
                (analysing || report.files.length === 0 || hasLockedFiles) ? "opacity-60 cursor-not-allowed" : ""
              }`}
              disabled={analysing || report.files.length === 0 || hasLockedFiles}
              onClick={handleAnalyse}
            >
              {analysing ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <span>{analysisProgress.percent ? `${analysisProgress.percent}%` : "Processing..."}</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Analyse GST Returns
                </>
              )}
            </button>
            {report.status === "Ready to use" && (
              <button
                className={`text-xs font-medium px-4 py-2.5 rounded-md transition-colors shadow-sm inline-flex items-center gap-1.5 ${
                  allProcessed ? "bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer" : "bg-gray-200 text-gray-400 cursor-not-allowed"
                }`}
                disabled={!allProcessed}
                onClick={() => setShowResult(true)}
              >
                View GST Report
              </button>
            )}
          </div>
        </div>
      </main>

      {/* Password Modal */}
      {unlockModalFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-md bg-white rounded-xl shadow-2xl border border-gray-200 p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2"><span>🔒</span> Enter PDF Password</h3>
              <button onClick={() => setUnlockModalFile(null)} className="text-gray-400 hover:text-gray-600 text-xl font-bold">&times;</button>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">File Name</p>
              <p className="text-sm font-semibold text-gray-900 truncate mt-0.5">{unlockModalFile.file_name}</p>
            </div>
            <form onSubmit={handleUnlockSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Document Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={passwordInput}
                    onChange={(e) => setPasswordInput(e.target.value)}
                    disabled={unlocking || lockouts[unlockModalFile.id] > 0}
                    placeholder="Enter password..."
                    autoFocus
                    className="w-full text-sm px-3.5 py-2.5 pr-16 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-600 hover:text-gray-900 font-medium px-2 py-1 rounded bg-gray-100 hover:bg-gray-200">
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
                {unlockError && <p className="text-xs text-red-600 mt-1.5 font-medium flex items-center gap-1"><span>⚠️</span> {unlockError}</p>}
              </div>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button type="button" className="btn-secondary text-xs" onClick={() => setUnlockModalFile(null)} disabled={unlocking}>Cancel</button>
                <button type="submit" disabled={unlocking || !passwordInput.trim() || lockouts[unlockModalFile.id] > 0} className="btn-primary text-xs font-semibold px-4 py-2 bg-emerald-600 hover:bg-emerald-700 inline-flex items-center gap-2">
                  {unlocking ? "Decrypting..." : "Unlock"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Authenticity Popover */}
      {reasonsPopoverFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-lg bg-white rounded-xl shadow-2xl border border-gray-200 p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2"><span>🛡️</span> Authenticity Inspection</h3>
              <button onClick={() => setReasonsPopoverFile(null)} className="text-gray-400 hover:text-gray-600 text-xl font-bold">&times;</button>
            </div>
            <div>
              <p className="text-xs text-gray-500">File: <span className="text-gray-800 font-semibold">{reasonsPopoverFile.file_name}</span></p>
              <div className="mt-2 flex items-center gap-2">
                <Badge label={reasonsPopoverFile.authenticity} />
                {reasonsPopoverFile.password_protected && <span className="text-xs text-gray-600">🔒 Password Protected</span>}
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3.5 border border-gray-200 max-h-60 overflow-y-auto">
              <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Forensic Checks</h4>
              <ul className="text-xs space-y-1.5 text-gray-700 list-disc list-inside">
                {(reasonsPopoverFile.authenticity_reasons || ["No anomalies found"]).map((r, i) => (
                  <li key={i} className="leading-relaxed">{r}</li>
                ))}
              </ul>
            </div>
            <div className="flex justify-end pt-1">
              <button className="btn-secondary text-xs" onClick={() => setReasonsPopoverFile(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* File Delete Confirm */}
      {fileToDelete && (
        <ConfirmDialog
          title="Remove File"
          message={`Are you sure you want to remove "${fileToDelete.file_name}" from this GST analysis?`}
          confirmLabel="Remove File"
          danger={true}
          onConfirm={confirmDeleteFile}
          onCancel={() => setFileToDelete(null)}
        />
      )}

      {/* Result Modal */}
      {showResult && <GSTResultModal report={report} onClose={() => setShowResult(false)} />}
    </div>
  );
}

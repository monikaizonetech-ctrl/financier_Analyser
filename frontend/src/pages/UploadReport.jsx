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
  const [isDragging, setIsDragging] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);

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

  const handleAnalyse = async () => {
    if (!report?.files?.length) {
      notify("Please upload at least one statement file before analysing", "warning");
      return;
    }
    setAnalysing(true);
    try {
      const res = await api.post(`/reports/${reportId}/analyse`);
      setReport(res.data);
      notify("Analysis complete. Your report is ready.");
      setShowResult(true);
    } catch (err) {
      notify(apiErrorMessage(err, "Analysis failed"), "error");
    } finally {
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
              <span className="text-xl">{typeMeta.icon}</span>
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-white">{report.name}</h1>
              <Badge label={report.status} />
            </div>
            <p className="text-xs text-white/70 mt-0.5">{typeMeta.label}</p>
          </div>

          <div className="flex items-center gap-2">
            {report.status === "Ready to use" && (
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

      <main className="max-w-6xl mx-auto px-4 sm:px-6 mt-8 space-y-6">
        {/* Metadata Summary Banner */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/80 p-5 grid grid-cols-2 md:grid-cols-4 gap-4 divide-x divide-gray-100">
          <div className="pr-4">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">Applicant / Entity</span>
            <span className="text-sm font-semibold text-gray-900 truncate block mt-0.5">{report.name}</span>
          </div>
          <div className="px-4">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">Reference ID</span>
            <span className="text-sm font-mono text-gray-700 truncate block mt-0.5">{report.reference_id || "N/A"}</span>
          </div>
          <div className="px-4">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">Module Type</span>
            <span className="text-sm font-semibold text-brand-600 truncate block mt-0.5">{typeMeta.shortLabel}</span>
          </div>
          <div className="pl-4">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">Statements Uploaded</span>
            <span className="text-sm font-semibold text-gray-900 truncate block mt-0.5">
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
                        </div>
                      </td>
                      <td className="px-6 py-4 text-gray-600 text-xs font-medium">{f.sub_type || "-"}</td>
                      <td className="px-6 py-4 text-gray-600 text-xs font-medium">{f.year || "-"}</td>
                      <td className="px-6 py-4">
                        <Badge label={f.file_status} />
                      </td>
                      <td className="px-6 py-4">
                        <Badge label={f.authenticity} />
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
              className="btn-primary flex-1 sm:flex-none text-xs font-semibold py-2.5 px-6 shadow-sm inline-flex items-center justify-center gap-2"
              disabled={analysing || report.files.length === 0}
              onClick={handleAnalyse}
            >
              {analysing ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Processing Analysis...
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
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs px-4 py-2.5 rounded-md transition-colors shadow-sm inline-flex items-center gap-1.5"
                onClick={() => setShowResult(true)}
              >
                View Report Output
              </button>
            )}
          </div>
        </div>
      </main>

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
      {showResult && <ReportResultModal report={report} onClose={() => setShowResult(false)} />}
    </div>
  );
}

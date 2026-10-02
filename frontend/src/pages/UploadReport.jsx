import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api, { apiErrorMessage } from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";
import { Badge } from "../components/Common.jsx";
import ReportResultModal from "./ReportResultModal.jsx";

const TYPE_LABELS = {
  BSA: "BANK STATEMENT",
  GST: "GST",
  ITR: "ITR",
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

  const fetchReport = async () => {
    const res = await api.get(`/reports/${reportId}`);
    setReport(res.data);
  };

  useEffect(() => {
    fetchReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId]);

  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
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

  const handleAnalyse = async () => {
    if (!report?.files?.length) {
      notify("Please upload at least one file before analysing", "warning");
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

  const handleDeleteFile = async (fileId) => {
    try {
      await api.delete(`/reports/${reportId}/files/${fileId}`);
      notify("File removed");
      await fetchReport();
    } catch (err) {
      notify(apiErrorMessage(err, "Could not remove file"), "error");
    }
  };

  if (!report) {
    return <div className="p-8 text-gray-500">Loading...</div>;
  }

  const typeLabel = TYPE_LABELS[report.report_type] || report.report_type;

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="bg-brand-600 text-white flex items-center justify-between px-6 py-4">
        <button onClick={() => navigate("/my-reports")} className="bg-white text-brand-700 text-sm font-semibold px-4 py-1.5 rounded-md">
          Exit
        </button>
        <h1 className="text-lg font-bold">{typeLabel} DEMO</h1>
        <div className="w-16" />
      </div>

      <div className="max-w-5xl mx-auto px-6 py-6">
        <div className="card px-5 py-4 mb-6 text-sm">
          <p className="text-gray-700">
            Trying first time? <span className="text-brand-600 underline font-medium">Watch quick video</span> to learn.
          </p>
          <p className="text-gray-500 mt-1">
            👉 Upload {typeLabel.toLowerCase()} statements 👉 Enter required details 👉 Press the analyse button below.
          </p>
        </div>

        <div className="flex justify-end mb-4">
          <label className="btn-primary cursor-pointer inline-flex items-center gap-2">
            ⬆️ {uploading ? "Uploading..." : "Upload Files"}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              hidden
              disabled={uploading}
              onChange={handleFileChange}
            />
          </label>
        </div>

        <div className="card p-0 overflow-hidden mb-6">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-bold text-gray-900">{typeLabel} Account</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">S.No</th>
                  <th className="px-4 py-3 text-left">File Name</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Year</th>
                  <th className="px-4 py-3 text-left">File Status</th>
                  <th className="px-4 py-3 text-left">File Authenticity</th>
                  <th className="px-4 py-3 text-left">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {report.files.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-gray-400">
                      No files uploaded
                    </td>
                  </tr>
                ) : (
                  report.files.map((f) => (
                    <tr key={f.id}>
                      <td className="px-4 py-3">{f.s_no}</td>
                      <td className="px-4 py-3">{f.file_name}</td>
                      <td className="px-4 py-3">{f.sub_type || "-"}</td>
                      <td className="px-4 py-3">{f.year || "-"}</td>
                      <td className="px-4 py-3">
                        <Badge label={f.file_status} />
                      </td>
                      <td className="px-4 py-3">
                        <Badge label={f.authenticity} />
                      </td>
                      <td className="px-4 py-3">
                        <button
                          className="text-red-500 hover:text-red-700 text-xs font-medium"
                          onClick={() => handleDeleteFile(f.id)}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card px-5 py-4 flex gap-3">
          <button className="btn-primary" disabled={analysing} onClick={handleAnalyse}>
            {analysing ? "Analysing..." : "Analyse"}
          </button>
          <button className="btn-secondary" onClick={() => navigate("/my-reports")}>
            Cancel
          </button>
          {report.status === "Ready to use" && (
            <button className="btn-secondary ml-auto" onClick={() => setShowResult(true)}>
              View Result
            </button>
          )}
        </div>
      </div>

      {showResult && <ReportResultModal report={report} onClose={() => setShowResult(false)} />}
    </div>
  );
}

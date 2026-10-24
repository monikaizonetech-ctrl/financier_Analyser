import { useState } from "react";
import Modal from "../components/Modal.jsx";
import api from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";
import { Badge } from "../components/Common.jsx";

export default function ReportResultModal({ report, onClose, activeFile = null }) {
  const { notify } = useNotification();
  const [downloading, setDownloading] = useState("");

  const handleDownload = async (format) => {
    setDownloading(format);
    try {
      const res = await api.get(`/reports/${report.id}/download`, {
        params: { file_format: format },
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      const ext = format === "xlsx" ? "xlsx" : "pdf";
      link.setAttribute("download", `${report.name.replace(/\s+/g, "_")}.${ext}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      notify(`${format.toUpperCase()} downloaded successfully`);
    } catch (err) {
      if (err.response && err.response.data instanceof Blob) {
        const text = await err.response.data.text();
        try {
          const json = JSON.parse(text);
          notify(json.detail || "Could not download report", "error");
        } catch (e) {
          notify("Could not download report", "error");
        }
      } else {
        notify("Could not download report", "error");
      }
    } finally {
      setDownloading("");
    }
  };

  const filesList = report.files || [];
  const displayFileName = activeFile || (filesList.length > 0 ? filesList[0]?.file_name : report.name);

  return (
    <Modal onClose={onClose} maxWidth="max-w-2xl" title={null}>
      <div className="-mx-4 sm:-mx-6 -mt-4 sm:-mt-5 bg-brand-600 text-white px-4 sm:px-6 py-3.5 sm:py-4 mb-4 sm:mb-5">
        <div className="flex items-center justify-between">
          <div className="min-w-0 pr-2">
            <h2 className="text-base sm:text-lg font-bold flex items-center gap-2 flex-wrap">
              <span className="truncate">{report.name}</span>
              <span className="font-normal text-xs bg-white/20 text-blue-100 px-2 py-0.5 rounded-full shrink-0">
                {report.report_type} Analysis
              </span>
            </h2>
            {displayFileName && (
              <p className="text-xs text-blue-100 mt-1 flex items-center gap-1.5 flex-wrap">
                <span>📄 Uploaded File:</span>
                <span className="font-semibold text-white bg-white/20 px-2 py-0.5 rounded truncate max-w-xs sm:max-w-md">
                  {displayFileName}
                </span>
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {filesList.length > 1 && !activeFile ? (
          filesList.map((f, idx) => (
            <div key={f.id || idx} className="flex items-center justify-between border border-gray-200 rounded-lg px-3.5 sm:px-4 py-3 bg-gray-50/50 gap-2">
              <div className="min-w-0 pr-2">
                <p className="font-semibold text-gray-800 text-xs sm:text-sm truncate">{f.file_name}</p>
                <p className="text-[11px] sm:text-xs text-gray-500">{f.sub_type || report.report_type} • {f.year || "Uploaded"}</p>
              </div>
              <Badge label={f.file_status || report.status} />
            </div>
          ))
        ) : (
          <div className="flex items-center justify-between border border-gray-200 rounded-lg px-3.5 sm:px-4 py-3 bg-gray-50/50 gap-2">
            <div className="min-w-0 pr-2">
              <p className="font-semibold text-gray-800 text-xs sm:text-sm truncate">{displayFileName}</p>
              <p className="text-[11px] sm:text-xs text-gray-500">{report.owner_name || "You"}</p>
            </div>
            <Badge label={report.status} />
          </div>
        )}

        <div className="mt-4 pt-3 border-t border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <span className="text-xs text-gray-500 font-medium">Download full report output:</span>
          <div className="flex items-center gap-2.5 self-end sm:self-auto">
            <button
              className="flex items-center gap-2 bg-[#00a86b] hover:bg-[#00925d] text-black text-xs sm:text-sm font-semibold px-3 sm:px-3.5 py-1.5 rounded-xl transition-all disabled:opacity-50 cursor-pointer shadow-sm active:scale-95 min-h-[34px]"
              disabled={downloading === "xlsx"}
              onClick={() => handleDownload("xlsx")}
              title="Download Excel"
            >
              <span className="text-sm leading-none">📊</span>
              <span className="tracking-tight text-black font-semibold">Excel</span>
            </button>
            <button
              className="flex items-center gap-2 bg-[#f04438] hover:bg-[#dc3528] text-black text-xs sm:text-sm font-semibold px-3 sm:px-3.5 py-1.5 rounded-xl transition-all disabled:opacity-50 cursor-pointer shadow-sm active:scale-95 min-h-[34px]"
              disabled={downloading === "pdf"}
              onClick={() => handleDownload("pdf")}
              title="Download PDF"
            >
              <span className="text-sm leading-none">📕</span>
              <span className="tracking-tight text-black font-semibold">PDF</span>
            </button>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-3 mt-6 pt-3 border-t border-gray-100">
        <button className="btn-secondary text-xs sm:text-sm" onClick={onClose}>
          Close
        </button>
      </div>
    </Modal>
  );
}


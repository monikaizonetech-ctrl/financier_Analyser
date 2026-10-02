import { useState } from "react";
import Modal from "../components/Modal.jsx";
import api from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";
import { Badge } from "../components/Common.jsx";

export default function ReportResultModal({ report, onClose }) {
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
      notify("Could not download report", "error");
    } finally {
      setDownloading("");
    }
  };

  const fileName = report.files?.[0]?.file_name || report.name;

  return (
    <Modal onClose={onClose} maxWidth="max-w-2xl" title={null}>
      <div className="-mx-6 -mt-5 bg-brand-600 text-white px-6 py-4 mb-5">
        <h2 className="text-lg font-bold">
          {report.name} <span className="font-normal text-blue-100">({report.report_type} Reports)</span>
        </h2>
      </div>

      <div className="flex items-center justify-between border border-gray-200 rounded-md px-4 py-3">
        <div>
          <p className="font-semibold text-gray-800 text-sm">{fileName}</p>
          <p className="text-xs text-gray-500">{report.owner_name || "You"}</p>
        </div>
        <div className="flex items-center gap-4">
          <Badge label={report.status} />
          <button
            className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium px-3 py-1.5 rounded-md disabled:opacity-50"
            disabled={downloading === "xlsx"}
            onClick={() => handleDownload("xlsx")}
          >
            📊 {downloading === "xlsx" ? "..." : "Download"}
          </button>
          <button
            className="flex items-center gap-1.5 bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-3 py-1.5 rounded-md disabled:opacity-50"
            disabled={downloading === "pdf"}
            onClick={() => handleDownload("pdf")}
          >
            📕 {downloading === "pdf" ? "..." : "Download"}
          </button>
        </div>
      </div>

      <div className="flex justify-end gap-3 mt-6">
        <button className="btn-secondary" onClick={onClose}>
          Cancel
        </button>
        <button className="btn-primary" onClick={onClose}>
          Ok
        </button>
      </div>
    </Modal>
  );
}

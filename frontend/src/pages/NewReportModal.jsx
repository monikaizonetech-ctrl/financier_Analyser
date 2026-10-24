import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Modal from "../components/Modal.jsx";
import api, { apiErrorMessage } from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";

const REPORT_TYPES = [
  { value: "BSA", label: "Bank Statement Analyzer" },
  { value: "GST", label: "GST Analyzer" },
  { value: "ITR", label: "ITR Analyzer" },
];

export default function NewReportModal({ onClose, onCreated, totalReports }) {
  const { notify } = useNotification();
  const navigate = useNavigate();

  const [form, setForm] = useState({ name: "", report_type: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [nextId, setNextId] = useState("Select a report type");

  useEffect(() => {
    if (!form.report_type) {
      setNextId("Select a report type");
      return;
    }
    let isCancelled = false;
    setNextId("Loading...");
    api.get("/reports/next-id", { params: { report_type: form.report_type } })
      .then(res => {
        if (!isCancelled) {
          setNextId(res.data.next_id);
        }
      })
      .catch(() => {
        if (!isCancelled) {
          setNextId("Auto-generated on create");
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [form.report_type]);


  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.report_type) {
      setError("Please select a report type");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await api.post("/reports", {
        name: form.name,
        report_type: form.report_type,
      });
      notify("Report created. Now upload your files.");
      onCreated?.(res.data);
      const path = res.data.report_type === "GST" ? `/gst-report/${res.data.id}` : `/upload-report/${res.data.id}`;
      navigate(path);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not create report"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Create New Report" onClose={onClose} maxWidth="max-w-lg">
      {error && (
        <div className="mb-4 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-semibold text-gray-800 mb-1">
            Select Report Type <span className="text-red-500">*</span>
          </label>
          <select
            required
            className="input-field"
            value={form.report_type}
            onChange={(e) => setForm({ ...form, report_type: e.target.value })}
          >
            <option value="">Select Product</option>
            {REPORT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>

        </div>


        <div>
          <label className="block text-sm font-semibold text-gray-800 mb-1">
            Reporter Name <span className="text-red-500">*</span>
          </label>
          <input
            required
            className="input-field"
            placeholder="eg:(Ram GST )"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-sm font-semibold text-gray-800 mb-1">Reference ID (Auto-Generated)</label>
          <input
            className="input-field bg-gray-50 cursor-not-allowed text-gray-500 font-medium"
            value={nextId}
            disabled
          />
        </div>



        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? "Please wait..." : "Next"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

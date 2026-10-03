import { useState } from "react";
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

  const autoRefId = String((totalReports || 0) + 1);
  const [form, setForm] = useState({ name: "", reference_id: autoRefId, report_type: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
        reference_id: form.reference_id || undefined,
        report_type: form.report_type,
      });
      notify("Report created. Now upload your files.");
      onCreated?.(res.data);
      navigate(`/upload-report/${res.data.id}`);
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
          <label className="block text-sm font-semibold text-gray-800 mb-1">Reference ID (Auto-Generated)</label>
          <input
            className="input-field bg-gray-50 cursor-not-allowed text-gray-500"
            value={form.reference_id}
            disabled
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-800 mb-1">
            Report Name <span className="text-red-500">*</span>
          </label>
          <input
            required
            className="input-field"
            placeholder="Enter Report Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </div>

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
          <p className="text-xs text-gray-500 mt-2">
            Not sure which product to choose? View product details, sample inputs, and outputs from{" "}
            <span className="text-brand-600 font-medium">My Profile</span>.
          </p>
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

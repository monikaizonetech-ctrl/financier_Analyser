import { createPortal } from "react-dom";

export function StatCard({ title, value, icon }) {
  return (
    <div className="card p-6 flex items-center justify-between">
      <div>
        <p className="text-sm text-gray-500">{title}</p>
        <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
      </div>
      <div className="text-4xl">{icon}</div>
    </div>
  );
}

const statusStyles = {
  "Need to analyse": "bg-amber-50 text-amber-700 border border-amber-200",
  Processing: "bg-blue-50 text-blue-700 border border-blue-200",
  "Ready to use": "bg-emerald-50 text-emerald-700 border border-emerald-200",
  Failed: "bg-red-50 text-red-700 border border-red-200",
  Active: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  Inactive: "bg-gray-100 text-gray-600 border border-gray-200",
  Pending: "bg-amber-50 text-amber-700 border border-amber-200",
  Uploaded: "bg-slate-50 text-slate-700 border border-slate-200",
  "Password required": "bg-amber-50 text-amber-700 border border-amber-300 font-semibold",
  Unlocked: "bg-blue-50 text-blue-700 border border-blue-200 font-medium",
  Processed: "bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium",
  Original: "bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium",
  Suspicious: "bg-amber-50 text-amber-800 border border-amber-300 font-semibold",
  Tampered: "bg-red-50 text-red-700 border border-red-300 font-bold",
  Unverifiable: "bg-purple-50 text-purple-700 border border-purple-200 font-medium",
};

export function Badge({ label }) {
  let displayLabel = label;
  if (label === "Need to analyse") displayLabel = "Upload & Analyse";

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
        statusStyles[label] || "bg-gray-100 text-gray-600 border border-gray-200"
      }`}
    >
      {displayLabel}
    </span>
  );
}

export function ConfirmDialog({ title, message, onConfirm, onCancel, confirmLabel = "Confirm", danger = false }) {
  const dialogContent = (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-3 sm:p-4 overflow-y-auto">
      <div className="fixed inset-0" aria-hidden="true" onClick={onCancel} />
      <div className="relative w-full max-w-sm bg-white rounded-xl shadow-2xl p-5 sm:p-6 my-auto z-10" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-base sm:text-lg font-bold text-gray-900 mb-2">{title}</h3>
        <p className="text-xs sm:text-sm text-gray-500 mb-5 sm:mb-6">{message}</p>
        <div className="flex justify-end gap-2 sm:gap-3">
          <button className="btn-secondary text-xs sm:text-sm py-2 px-3.5" onClick={onCancel}>
            Cancel
          </button>
          <button
            className={`px-4 py-2 rounded-md text-white text-xs sm:text-sm font-medium transition-colors ${
              danger ? "bg-red-600 hover:bg-red-700" : "bg-brand-600 hover:bg-brand-700"
            }`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );

  return typeof document !== "undefined" ? createPortal(dialogContent, document.body) : dialogContent;
}


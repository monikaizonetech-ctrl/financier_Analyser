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
};

export function Badge({ label }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
        statusStyles[label] || "bg-gray-100 text-gray-600 border border-gray-200"
      }`}
    >
      {label}
    </span>
  );
}

export function ConfirmDialog({ title, message, onConfirm, onCancel, confirmLabel = "Confirm", danger = false }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-sm bg-white rounded-lg shadow-xl p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-2">{title}</h3>
        <p className="text-sm text-gray-500 mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <button className="btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button
            className={`px-4 py-2 rounded-md text-white font-medium ${
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
}

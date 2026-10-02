import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { apiErrorMessage } from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";
import DataTable from "../components/DataTable.jsx";
import Pagination from "../components/Pagination.jsx";
import { Badge, ConfirmDialog } from "../components/Common.jsx";
import NewReportModal from "./NewReportModal.jsx";
import ReportResultModal from "./ReportResultModal.jsx";

export default function MyReports() {
  const navigate = useNavigate();
  const { notify } = useNotification();

  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 10 });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showNewReport, setShowNewReport] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [viewReport, setViewReport] = useState(null);

  const fetchReports = async (page = 1) => {
    setLoading(true);
    try {
      const res = await api.get("/reports", { params: { search: search || undefined, page, page_size: 10 } });
      setData(res.data);
    } catch (err) {
      notify(apiErrorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const handleRowAction = (report) => {
    if (report.status === "Ready to use") {
      setViewReport(report);
    } else {
      navigate(`/upload-report/${report.id}`);
    }
  };

  const handleDelete = async () => {
    try {
      await api.delete(`/reports/${deleteTarget.id}`);
      notify("Report deleted");
      setDeleteTarget(null);
      fetchReports(data.page);
    } catch (err) {
      notify(apiErrorMessage(err), "error");
    }
  };

  const columns = [
    { key: "name", label: "Report Name", render: (r) => <span className="font-medium text-gray-800">{r.name}</span> },
    { key: "reference_id", label: "Reference ID" },
    {
      key: "status",
      label: "Report Status",
      render: (r) => (
        <button onClick={() => handleRowAction(r)} className="underline">
          <Badge label={r.status} />
        </button>
      ),
    },
    {
      key: "created_at",
      label: "Creation Info",
      render: (r) => new Date(r.created_at + (r.created_at.endsWith("Z") ? "" : "Z")).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }),
    },
    {
      key: "actions",
      label: "Actions",
      render: (r) => (
        <div className="flex items-center gap-3">
          <button
            title="Download"
            disabled={r.status !== "Ready to use"}
            className="text-gray-500 hover:text-brand-600 disabled:opacity-30"
            onClick={() => setViewReport(r)}
          >
            ⬇️
          </button>
          <button title="Delete" className="text-red-400 hover:text-red-600" onClick={() => setDeleteTarget(r)}>
            🗑️
          </button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="card p-0 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 border-b border-gray-100">
          <h1 className="text-lg font-bold text-gray-900">My Reports</h1>
          <div className="flex items-center gap-3 flex-wrap">
            <input
              className="input-field w-64"
              placeholder="Search by Report Name"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button className="btn-secondary text-sm" onClick={() => fetchReports(data.page)}>
              ↻ Refresh
            </button>
            <button className="btn-primary text-sm" onClick={() => setShowNewReport(true)}>
              + New Report
            </button>
          </div>
        </div>

        <DataTable columns={columns} rows={data.items} loading={loading} emptyMessage="No reports yet. Create your first report." />
        <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPageChange={(p) => fetchReports(p)} />
      </div>

      {showNewReport && <NewReportModal onClose={() => setShowNewReport(false)} />}
      {viewReport && <ReportResultModal report={viewReport} onClose={() => setViewReport(null)} />}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete Report"
          message={`Are you sure you want to delete "${deleteTarget.name}"? This cannot be undone.`}
          confirmLabel="Delete"
          danger
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
        />
      )}
    </div>
  );
}

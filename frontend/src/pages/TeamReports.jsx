import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { apiErrorMessage } from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";
import DataTable from "../components/DataTable.jsx";
import Pagination from "../components/Pagination.jsx";
import { Badge, ConfirmDialog } from "../components/Common.jsx";
import ReportResultModal from "./ReportResultModal.jsx";
import { FolderOpen, Download, Trash2, RotateCw, ChevronDown } from "lucide-react";

export default function TeamReports() {
  const { notify } = useNotification();
  const navigate = useNavigate();
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 10 });
  const [loading, setLoading] = useState(true);
  const [searchEmail, setSearchEmail] = useState("");
  const [searchName, setSearchName] = useState("");
  const [selectedType, setSelectedType] = useState("ALL");
  const [viewReport, setViewReport] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const reportPath = (r) => (r.report_type === "GST" ? `/gst-report/${r.id}` : `/upload-report/${r.id}`);

  const handleRowAction = (report) => {
    if (report.status === "Ready to use" && report.report_type !== "GST") {
      setViewReport(report);
    } else if (report.status === "Need to analyse" || report.report_type === "GST") {
      navigate(reportPath(report));
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

  const fetchReports = async (page = 1) => {
    setLoading(true);
    try {
      const res = await api.get("/reports/team", {
        params: {
          search_email: searchEmail || undefined,
          search_name: searchName || undefined,
          report_type: selectedType !== "ALL" ? selectedType : undefined,
          page,
          page_size: 10,
        },
      });
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
  }, [searchEmail, searchName, selectedType]);

  const REPORT_TYPE_LABELS = {
    BSA: "Bank Statement",
    GST: "GST",
    ITR: "ITR",
  };

  const REPORT_TYPE_BADGES = {
    BSA: "bg-blue-50 text-blue-700 border-blue-200",
    GST: "bg-emerald-50 text-emerald-700 border-emerald-200",
    ITR: "bg-purple-50 text-purple-700 border-purple-200",
  };

  const columns = [
    {
      key: "reference_id",
      label: "Reference id",
      render: (r) => (
        <span className="font-mono text-xs font-semibold text-gray-700 bg-gray-100 px-2.5 py-1 rounded-md">
          {r.reference_id || "—"}
        </span>
      ),
    },
    {
      key: "name",
      label: "Reporter Name",
      render: (r) => (
        <button
          onClick={() => navigate(reportPath(r))}
          className="font-semibold text-brand-700 hover:text-brand-900 hover:underline text-left cursor-pointer"
          title="Open statement files and analysis"
        >
          {r.name}
        </button>
      ),
    },
    {
      key: "report_type",
      label: "Report Type",
      render: (r) => {
        const typeKey = r.report_type;
        const label = REPORT_TYPE_LABELS[typeKey] || typeKey;
        const badgeClass = REPORT_TYPE_BADGES[typeKey] || "bg-gray-50 text-gray-700 border-gray-200";
        return (
          <span className={`inline-block text-xs font-semibold px-2.5 py-0.5 rounded-full border ${badgeClass}`}>
            {label}
          </span>
        );
      },
    },
    {
      key: "status",
      label: "Report Status",
      render: (r) => (
        <button onClick={() => handleRowAction(r)} className="cursor-pointer">
          <Badge label={r.status} />
        </button>
      ),
    },
    {
      key: "creation_info",
      label: "Date and Time",
      render: (r) => (
        <div>
          <p>
            {new Date(r.created_at + (r.created_at.endsWith("Z") ? "" : "Z")).toLocaleString("en-IN", {
              day: "2-digit",
              month: "short",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
          <p className="text-xs text-gray-400">{r.owner_email}</p>
        </div>
      ),
    },
    {
      key: "actions",
      label: "Actions",
      render: (r) => (
        <div className="flex items-center gap-2">
          <button
            title="Manage Statements / Files"
            className="p-1.5 rounded-lg text-amber-600 hover:text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200/80 transition-all hover:scale-105 active:scale-95 cursor-pointer shadow-xs"
            onClick={() => navigate(reportPath(r))}
          >
            <FolderOpen className="w-4 h-4" />
          </button>
          <button
            title="Download Report"
            disabled={r.status !== "Ready to use"}
            className="p-1.5 rounded-lg text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200/80 transition-all hover:scale-105 active:scale-95 disabled:opacity-30 disabled:pointer-events-none cursor-pointer shadow-xs"
            onClick={() => setViewReport(r)}
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            title="Delete"
            className="p-1.5 rounded-lg text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200/80 transition-all hover:scale-105 active:scale-95 cursor-pointer shadow-xs"
            onClick={() => setDeleteTarget(r)}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="card p-0 overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 px-4 sm:px-5 py-3.5 border-b border-gray-100">
          <div className="flex items-center gap-2.5 shrink-0">
            <h1 className="text-base sm:text-lg font-bold text-gray-900 whitespace-nowrap">Team Reports</h1>
            <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2.5 py-0.5 rounded-full whitespace-nowrap">
              {data.total} {data.total === 1 ? "record" : "records"}
              {selectedType !== "ALL" && ` in ${REPORT_TYPE_LABELS[selectedType] || selectedType}`}
            </span>
          </div>

          <div className="flex flex-wrap lg:flex-nowrap items-center gap-2">
            {/* Filter for Report Type */}
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="text-xs text-gray-500 font-medium whitespace-nowrap">Type:</span>
              <div className="relative">
                <select
                  className="appearance-none bg-white border border-gray-300 rounded-md pl-3 pr-8 py-1 text-xs font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent h-8 cursor-pointer w-32 shadow-xs"
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                >
                  <option value="ALL">All Types</option>
                  <option value="GST">GST</option>
                  <option value="BSA">Bank Statement</option>
                  <option value="ITR">ITR</option>
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-gray-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>

            <input
              className="input-field w-full sm:w-36 text-xs py-1 px-3 h-8"
              placeholder="Search by Email"
              value={searchEmail}
              onChange={(e) => setSearchEmail(e.target.value)}
            />

            <input
              className="input-field w-full sm:w-44 text-xs py-1 px-3 h-8"
              placeholder="Search report / Ref ID"
              value={searchName}
              onChange={(e) => setSearchName(e.target.value)}
            />

            <button
              className="btn-secondary text-xs py-1 px-2.5 h-8 flex items-center gap-1.5 whitespace-nowrap shadow-xs hover:border-gray-400 transition-colors ml-auto lg:ml-0"
              onClick={() => fetchReports(data.page)}
            >
              <RotateCw className={`w-3.5 h-3.5 text-gray-500 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        <DataTable
          columns={columns}
          rows={data.items}
          loading={loading}
          emptyMessage={
            selectedType !== "ALL"
              ? `No ${REPORT_TYPE_LABELS[selectedType] || selectedType} reports found.`
              : "No team reports found."
          }
        />
        <Pagination
          page={data.page}
          pageSize={data.page_size}
          total={data.total}
          onPageChange={(p) => fetchReports(p)}
        />
      </div>


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

import { useEffect, useState } from "react";
import api, { apiErrorMessage } from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";
import DataTable from "../components/DataTable.jsx";
import Pagination from "../components/Pagination.jsx";
import { Badge } from "../components/Common.jsx";
import ReportResultModal from "./ReportResultModal.jsx";

export default function TeamReports() {
  const { notify } = useNotification();
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 10 });
  const [loading, setLoading] = useState(true);
  const [searchEmail, setSearchEmail] = useState("");
  const [searchName, setSearchName] = useState("");
  const [viewReport, setViewReport] = useState(null);

  const fetchReports = async (page = 1) => {
    setLoading(true);
    try {
      const res = await api.get("/reports/team", {
        params: {
          search_email: searchEmail || undefined,
          search_name: searchName || undefined,
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
  }, [searchEmail, searchName]);

  const columns = [
    { key: "name", label: "Report Name", render: (r) => <span className="font-medium text-gray-800">{r.name}</span> },
    { key: "reference_id", label: "Reference ID" },
    {
      key: "status",
      label: "Report Status",
      render: (r) => (
        <button onClick={() => r.status === "Ready to use" && setViewReport(r)}>
          <Badge label={r.status} />
        </button>
      ),
    },
    {
      key: "creation_info",
      label: "Creation Info",
      render: (r) => (
        <div>
          <p>{new Date(r.created_at + (r.created_at.endsWith("Z") ? "" : "Z")).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}</p>
          <p className="text-xs text-gray-400">{r.owner_email}</p>
        </div>
      ),
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
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="card p-0 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 border-b border-gray-100">
          <h1 className="text-lg font-bold text-gray-900">Team Reports</h1>
          <div className="flex items-center gap-3 flex-wrap">
            <input
              className="input-field w-56"
              placeholder="Search by Email ID"
              value={searchEmail}
              onChange={(e) => setSearchEmail(e.target.value)}
            />
            <input
              className="input-field w-56"
              placeholder="Search by Report Name"
              value={searchName}
              onChange={(e) => setSearchName(e.target.value)}
            />
            <button className="btn-secondary text-sm" onClick={() => fetchReports(data.page)}>
              ↻ Refresh
            </button>
          </div>
        </div>

        <DataTable columns={columns} rows={data.items} loading={loading} emptyMessage="No team reports found." />
        <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPageChange={(p) => fetchReports(p)} />
      </div>

      {viewReport && <ReportResultModal report={viewReport} onClose={() => setViewReport(null)} />}
    </div>
  );
}

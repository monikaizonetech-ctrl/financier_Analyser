import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/axios.js";
import { StatCard } from "../components/Common.jsx";
import NewReportModal from "./NewReportModal.jsx";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [showNewReport, setShowNewReport] = useState(false);

  const fetchStats = () => {
    api.get("/dashboard").then((res) => setStats(res.data));
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard title="Bank Statement Analysed via Files" value={stats?.bank_statements_analysed ?? "—"} icon="🏦" />
        <StatCard title="GST Analysed via Files" value={stats?.gst_analysed ?? "—"} icon="🧾" />
        <StatCard title="ITR Analysed via Files" value={stats?.itr_analysed ?? "—"} icon="📑" />
      </div>

      <div className="mt-8 flex gap-3">
        <button className="btn-primary" onClick={() => setShowNewReport(true)}>
          + New Report
        </button>
        <Link to="/my-reports" className="btn-secondary">
          View My Reports
        </Link>
      </div>

      {showNewReport && <NewReportModal onClose={() => setShowNewReport(false)} />}
    </div>
  );
}

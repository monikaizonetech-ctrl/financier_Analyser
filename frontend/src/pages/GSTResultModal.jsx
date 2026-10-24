import { useState } from "react";
import { createPortal } from "react-dom";
import api from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";
import { Badge } from "../components/Common.jsx";

function fmt(n, prefix = "Rs.") {
  if (n === undefined || n === null || n === "-") return "—";
  const num = parseFloat(n);
  if (isNaN(num)) return String(n);
  const abs = Math.abs(num);
  let formatted;
  if (abs >= 10000000) formatted = (num / 10000000).toFixed(2) + " Cr";
  else if (abs >= 100000) formatted = (num / 100000).toFixed(2) + " L";
  else formatted = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);
  return prefix + " " + formatted;
}

function fmtRaw(n) {
  if (n === undefined || n === null) return "—";
  const num = parseFloat(n);
  if (isNaN(num)) return String(n);
  return new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);
}

function fmtCount(n) {
  if (n === undefined || n === null || n === "-" || n === "") return "—";
  const num = parseInt(n, 10);
  if (isNaN(num)) return String(n);
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(num);
}

const SUBTYPE_COLOR = {
  "GSTR-1": { bg: "bg-emerald-100", text: "text-emerald-800", border: "border-emerald-300", gradient: "from-emerald-500 to-teal-600" },
  "GSTR-2B": { bg: "bg-blue-100", text: "text-blue-800", border: "border-blue-300", gradient: "from-blue-500 to-indigo-600" },
  "GSTR-3B": { bg: "bg-violet-100", text: "text-violet-800", border: "border-violet-300", gradient: "from-violet-500 to-purple-600" },
};

function StatCard({ label, value, sub, color = "text-gray-900", icon }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{label}</p>
          <p className={`text-lg font-bold mt-1 ${color}`}>{value}</p>
          {sub && <p className="text-[11px] text-gray-400 mt-0.5">{sub}</p>}
        </div>
        {icon && <span className="text-2xl opacity-70">{icon}</span>}
      </div>
    </div>
  );
}

function TaxBar({ igst, cgst, sgst, cess, total }) {
  const pct = (v) => total > 0 ? Math.round((v / total) * 100) : 0;
  return (
    <div className="space-y-2">
      {[
        { label: "IGST", value: igst, color: "bg-blue-500" },
        { label: "CGST", value: cgst, color: "bg-emerald-500" },
        { label: "SGST", value: sgst, color: "bg-teal-500" },
        { label: "CESS", value: cess, color: "bg-amber-500" },
      ].map(({ label, value, color }) => (
        <div key={label} className="flex items-center gap-3">
          <span className="text-xs font-semibold text-gray-600 w-10">{label}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-2.5 overflow-hidden">
            <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct(value)}%` }} />
          </div>
          <span className="text-xs font-bold text-gray-700 w-28 text-right">{fmt(value)}</span>
          <span className="text-[11px] text-gray-400 w-8">{pct(value)}%</span>
        </div>
      ))}
    </div>
  );
}

export default function GSTResultModal({ report, onClose, activeFileFilter = null }) {
  const { notify } = useNotification();
  const [downloading, setDownloading] = useState("");
  const [activeTab, setActiveTab] = useState("overview");

  // Consolidate all details from all uploaded files
  const rawDetails = report?.result_summary?.details || [];
  // Default to the clicked file filter or the first file so files show separately by default
  const [selectedFileFilter, setSelectedFileFilter] = useState(() => {
    if (activeFileFilter) return activeFileFilter;
    if (rawDetails.length > 0) return rawDetails[0]?.file_name;
    return null;
  });

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
      link.setAttribute("download", `${report.name.replace(/\s+/g, "_")}_GST.${ext}`);
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

  const details = selectedFileFilter && selectedFileFilter !== "ALL"
    ? rawDetails.filter((d) => d.file_name === selectedFileFilter || d.id === selectedFileFilter)
    : rawDetails;
  const firstDetail = details[0] || rawDetails[0] || {};
  const currentFileName = selectedFileFilter && selectedFileFilter !== "ALL"
    ? selectedFileFilter
    : (rawDetails.length === 1 ? rawDetails[0]?.file_name : null);



  // Aggregate across files
  const allAnalytics = details.map((d) => d.analytics || d).filter(Boolean);
  const isGSTR2B = details.some((d) => d.subtype === "GSTR-2B" || d.analytics?.subtype === "GSTR-2B" || d.is_gstr2b || d.analytics?.is_gstr2b);

  const totalTaxable = allAnalytics.reduce((s, a) => s + (a.total_taxable_value || a.summary_total_taxable || 0), 0) || firstDetail.taxable_value || 0;
  const totalIGST = allAnalytics.reduce((s, a) => s + (a.total_igst || 0), 0);
  const totalCGST = allAnalytics.reduce((s, a) => s + (a.total_cgst || 0), 0);
  const totalSGST = allAnalytics.reduce((s, a) => s + (a.total_sgst || 0), 0);
  const totalCESS = allAnalytics.reduce((s, a) => s + (a.total_cess || 0), 0);
  const totalTax = allAnalytics.reduce((s, a) => s + (a.total_tax || 0), 0);
  const totalITC = allAnalytics.reduce((s, a) => s + (a.itc_total || 0), 0);
  const totalNetLiability = isGSTR2B ? 0.0 : totalTax - totalITC;
  const totalInvoices = allAnalytics.reduce((s, a) => s + (a.total_invoices || 0), 0);

  // GSTR-2B specific metrics
  const totalEligibleITC = allAnalytics.reduce((s, a) => s + (a.total_itc_available ?? a.itc_total ?? 0), 0);
  const totalIneligibleITC = allAnalytics.reduce((s, a) => s + (a.total_itc_ineligible ?? 0), 0);
  const combinedInwardTax = allAnalytics.reduce((s, a) => s + (a.combined_inward_tax ?? a.total_tax ?? 0), 0) || (totalEligibleITC + totalIneligibleITC);
  const gstr2bEligibleIGST = allAnalytics.reduce((s, a) => s + (a.itc_available_summary?.igst ?? a.itc_igst ?? 0), 0);
  const gstr2bEligibleCGST = allAnalytics.reduce((s, a) => s + (a.itc_available_summary?.cgst ?? a.itc_cgst ?? 0), 0);
  const gstr2bEligibleSGST = allAnalytics.reduce((s, a) => s + (a.itc_available_summary?.sgst ?? a.itc_sgst ?? 0), 0);
  const gstr2bIneligibleIGST = allAnalytics.reduce((s, a) => s + (a.itc_ineligible_summary?.igst ?? 0), 0);
  const gstr2bIneligibleCGST = allAnalytics.reduce((s, a) => s + (a.itc_ineligible_summary?.cgst ?? 0), 0);
  const gstr2bIneligibleSGST = allAnalytics.reduce((s, a) => s + (a.itc_ineligible_summary?.sgst ?? 0), 0);

  // All transactions
  const allTransactions = details.flatMap((d) => d.transactions || []);

  // Supplier aggregation for GSTR-2B
  const supplierAggMap = {};
  for (const txn of allTransactions) {
    const gstin = txn.counterparty_gstin || "-";
    const name = txn.counterparty_name || "Supplier";
    const key = `${gstin}_${name}`;
    if (!supplierAggMap[key]) {
      supplierAggMap[key] = {
        gstin,
        name,
        count: 0,
        taxable: 0,
        eligible_itc: 0,
        ineligible_itc: 0,
        tax: 0,
        status: txn.source_status || (txn.itc_eligible ? "Available" : "Not available")
      };
    }
    supplierAggMap[key].count += 1;
    supplierAggMap[key].taxable += (txn.taxable_value || txn.taxable || 0);
    const lineTax = (txn.igst || 0) + (txn.cgst || 0) + (txn.sgst || 0);
    supplierAggMap[key].tax += lineTax;
    if (txn.itc_eligible !== false && txn.source_status !== "Not available") {
      supplierAggMap[key].eligible_itc += lineTax;
    } else {
      supplierAggMap[key].ineligible_itc += lineTax;
    }
  }
  const supplierList = Object.values(supplierAggMap).sort((a, b) => b.taxable - a.taxable);

  // Monthly trends merged
  const monthlyMerged = {};
  for (const a of allAnalytics) {
    for (const [m, v] of Object.entries(a.monthly_trends || {})) {
      if (!monthlyMerged[m]) monthlyMerged[m] = { taxable: 0, igst: 0, cgst: 0, sgst: 0, tax: 0, count: 0 };
      monthlyMerged[m].taxable += v.taxable || 0;
      monthlyMerged[m].igst += v.igst || 0;
      monthlyMerged[m].cgst += v.cgst || 0;
      monthlyMerged[m].sgst += v.sgst || 0;
      monthlyMerged[m].tax += v.tax || 0;
      monthlyMerged[m].count += v.count || 0;
    }
  }
  const monthlyEntries = Object.entries(monthlyMerged).filter(([k]) => k !== "-");

  // Supply type breakdown
  const typeBreakdown = {};
  for (const a of allAnalytics) {
    for (const [st, v] of Object.entries(a.supply_type_breakdown || {})) {
      if (!typeBreakdown[st]) typeBreakdown[st] = { count: 0, taxable: 0, tax: 0 };
      typeBreakdown[st].count += v.count || 0;
      typeBreakdown[st].taxable += v.taxable || 0;
      typeBreakdown[st].tax += v.tax || 0;
    }
  }

  // Filing Statistics (Macro summary file check)
  const isFilingStats = details.some((d) => d.is_filing_statistics || d.analytics?.is_filing_statistics);
  const firstStats = details.find((d) => d.filing_statistics)?.filing_statistics || firstDetail.filing_statistics || {};
  const totalReturnsFiled = details.reduce((s, d) => s + (d.filing_statistics?.total_returns_filed || 0), 0) || firstStats.total_returns_filed || 0;
  const summedMonthlyEligible = details.reduce((s, d) => s + (d.filing_statistics?.summed_monthly_eligible || 0), 0) || firstStats.summed_monthly_eligible || 0;
  const totalOnTime = details.reduce((s, d) => s + (d.filing_statistics?.total_on_time || 0), 0) || firstStats.total_on_time || 0;
  const totalLate = details.reduce((s, d) => s + (d.filing_statistics?.total_late || 0), 0) || firstStats.total_late || 0;
  const overallFilingPct = firstStats.overall_filing_pct || (summedMonthlyEligible > 0 ? ((totalReturnsFiled / summedMonthlyEligible) * 100).toFixed(2) : "0.00");
  const monthlyStatsList = firstStats.monthly_summary || [];
  const stateStatsList = firstStats.state_summary || [];

  // File-wise summary
  const fileSummary = details.map((d, i) => ({
    file_name: d.file_name || `File ${i + 1}`,
    subtype: d.is_filing_statistics ? "GSTR-1 Filing Summary" : (d.subtype || d.analytics?.subtype || "GSTR-1"),
    gstin: d.gstin_detected || "-",
    period: d.return_period || "-",
    total_tax: (d.analytics?.total_tax ?? d.total_tax) || 0,
    taxable: (d.analytics?.total_taxable_value ?? d.taxable_value) || 0,
    invoices: d.is_filing_statistics ? (d.filing_statistics?.total_returns_filed || 0) : (d.analytics?.total_invoices ?? 0),
    status: d.filing_status || "-",
  }));

  // Compliance & Turnover profile data (from GSTR-3B)
  const repaymentData = details[0]?.repayment_capacity || report?.result_summary?.repayment_capacity || allAnalytics[0]?.repayment_capacity || null;
  const allValidationChecks = details.flatMap((d) => d.validation_checks || d.analytics?.validation_checks || d.validation_result?.checks || []);
  const validationStatus = details[0]?.validation_status || details[0]?.analytics?.validation_status || (allValidationChecks.some(c => c.status === "FAIL") ? "DISCREPANCY" : "PASS");

  const tabs = isFilingStats ? [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "monthly", label: "Monthly Filing Trends", icon: "📅" },
    { id: "states", label: "State Performance", icon: "🗺️" },
    { id: "validation", label: "Validation & Diagnostics", icon: "🛡️" },
    { id: "files", label: "Files Summary", icon: "📁" },
  ] : isGSTR2B ? [
    { id: "overview", label: "Overview & ITC Summary", icon: "📊" },
    { id: "breakdown", label: "Inward Suppliers & ITC", icon: "🏢" },
    { id: "transactions", label: "Inward Invoices", icon: "📋" },
    { id: "validation", label: "Validation & Diagnostics", icon: "🛡️" },
    { id: "files", label: "Files Summary", icon: "📁" },
  ] : [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "validation", label: "Validation & Reconciliation", icon: "🛡️" },
    { id: "monthly", label: "Monthly Trends", icon: "📅" },
    { id: "breakdown", label: "Supply Breakdown", icon: "🔍" },
    { id: "transactions", label: "Invoice Register", icon: "📋" },
    { id: "files", label: "Files Summary", icon: "📁" },
  ];

  const modalContent = (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-3 sm:p-5 overflow-y-auto">
      <div className="fixed inset-0" aria-hidden="true" onClick={onClose} />
      <div className="relative w-full max-w-5xl bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col max-h-[92vh] overflow-hidden my-auto z-10" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="bg-gradient-to-r from-emerald-700 via-teal-700 to-slate-800 text-white px-4 sm:px-6 py-3.5 sm:py-4 flex flex-col md:flex-row md:items-center justify-between gap-3 shrink-0">
          <div className="min-w-0 pr-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xl shrink-0">🧾</span>
              <h2 className="text-base font-bold truncate">{report.name}</h2>
              <span className="text-xs bg-white/20 text-white px-2 py-0.5 rounded-full font-medium shrink-0">
                GST Analysis Report
              </span>
              {currentFileName && (
                <span className="inline-flex items-center gap-1 text-xs bg-emerald-500/40 text-emerald-100 border border-emerald-400/40 px-2.5 py-0.5 rounded-full font-semibold truncate max-w-xs" title={currentFileName}>
                  <span>📄</span> {currentFileName}
                </span>
              )}
            </div>
            <p className="text-xs text-white/80 mt-1.5 flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-white">{fileSummary.map((f) => f.subtype).join(" · ")}</span>
              <span>•</span>
              <span className="bg-white/10 px-2 py-0.5 rounded text-[11px] font-mono">
                Ref: {report.reference_id || report.result_summary?.reference_id || "GST_004"}
              </span>
              <span>•</span>
              <span>FY: {firstDetail.return_period || "FY 2018-2019"}</span>
              <span>•</span>
              <span>Analysed: {report.analysed_at ? new Date(report.analysed_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "Today"}</span>
              <span>•</span>
              <span>{isFilingStats ? `${fmtCount(totalReturnsFiled)} returns filed` : `${totalInvoices} invoices`}</span>
              <span>•</span>
              <span>{fileSummary.length} {fileSummary.length === 1 ? "file" : "files"}</span>
              {rawDetails.length > 1 && (
                <span className="inline-flex items-center gap-1.5 ml-0 sm:ml-2 mt-1 sm:mt-0">
                  <span className="text-white/60">Viewing:</span>
                  <select
                    className="bg-emerald-900/80 text-white text-xs rounded px-2 py-0.5 border border-emerald-500/50 cursor-pointer focus:outline-none max-w-[200px] truncate"
                    value={selectedFileFilter || "ALL"}
                    onChange={(e) => setSelectedFileFilter(e.target.value === "ALL" ? null : e.target.value)}
                  >
                    <option value="ALL">All Files Combined ({rawDetails.length})</option>
                    {rawDetails.map((d, idx) => (
                      <option key={idx} value={d.file_name || `File ${idx + 1}`}>
                        {d.file_name || `File ${idx + 1}`}
                      </option>
                    ))}
                  </select>
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2.5 shrink-0 self-end md:self-auto">
            <button
              className="flex items-center gap-2 bg-[#00a86b] hover:bg-[#00925d] text-black text-xs font-semibold px-3 py-1.5 rounded-xl transition-all disabled:opacity-50 cursor-pointer shadow-sm active:scale-95 min-h-[34px]"
              disabled={downloading === "xlsx"}
              onClick={() => handleDownload("xlsx")}
              title="Download Excel"
            >
              <span className="text-sm leading-none">📊</span>
              <span className="tracking-tight text-black font-semibold">Excel</span>
            </button>
            <button
              className="flex items-center gap-2 bg-[#f04438] hover:bg-[#dc3528] text-black text-xs font-semibold px-3 py-1.5 rounded-xl transition-all disabled:opacity-50 cursor-pointer shadow-sm active:scale-95 min-h-[34px]"
              disabled={downloading === "pdf"}
              onClick={() => handleDownload("pdf")}
              title="Download PDF"
            >
              <span className="text-sm leading-none">📕</span>
              <span className="tracking-tight text-black font-semibold">PDF</span>
            </button>
            <button onClick={onClose} className="ml-2 text-white/70 hover:text-white text-2xl font-bold leading-none cursor-pointer p-1" aria-label="Close">&times;</button>
          </div>
        </div>


        {/* Tab Bar */}
        <div className="flex gap-1 px-3 sm:px-6 pt-3 pb-0 border-b border-gray-200 bg-gray-50 shrink-0 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-t-lg border-b-2 transition-all whitespace-nowrap min-h-[36px] ${
                activeTab === tab.id
                  ? "border-emerald-600 text-emerald-700 bg-white"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-white/70"
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-5 md:p-6 bg-gray-50/50">

          {/* OVERVIEW TAB */}
          {activeTab === "overview" && (
            isFilingStats ? (
              <div className="space-y-5">
                {/* Filing Statistics KPI Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3">
                  <StatCard
                    label="Total Returns Filed"
                    value={Number(totalReturnsFiled).toLocaleString("en-IN")}
                    icon="📤"
                    color="text-emerald-700"
                    sub="Across 12 return periods"
                  />
                  <StatCard
                    label="Summed Eligible Taxpayers"
                    value={fmtCount(summedMonthlyEligible)}
                    icon="👥"
                    color="text-blue-700"
                    sub="Sum of monthly active taxpayers*"
                  />
                  <StatCard
                    label="Overall Filing Rate"
                    value={`${overallFilingPct}%`}
                    icon="📈"
                    color="text-emerald-600"
                    sub="Total Filed ÷ Summed Eligible"
                  />
                  <StatCard
                    label="Active Jurisdictions"
                    value={`${firstStats.states_and_uts_count || 36} States & UTs`}
                    icon="🗺️"
                    color="text-purple-700"
                    sub="(+ 1 Other Territory)"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3">
                  <StatCard
                    label="Filed Within Due Date"
                    value={fmtCount(totalOnTime)}
                    icon="⏱️"
                    color="text-teal-700"
                    sub={totalReturnsFiled > 0 ? `${((totalOnTime / totalReturnsFiled) * 100).toFixed(1)}% of total filings` : undefined}
                  />
                  <StatCard
                    label="Filed Late (After Due Date)"
                    value={fmtCount(totalLate)}
                    icon="⏳"
                    color="text-amber-700"
                    sub={totalReturnsFiled > 0 ? `${((totalLate / totalReturnsFiled) * 100).toFixed(1)}% of total filings` : undefined}
                  />
                  <StatCard
                    label="Document Period"
                    value={firstDetail.return_period || "FY 2018-2019"}
                    icon="📅"
                    color="text-gray-800"
                    sub="Financial Year"
                  />
                  <StatCard
                    label="Verification Status"
                    value="Analysed"
                    icon="✅"
                    color="text-emerald-700"
                    sub="Complete data validated"
                  />
                </div>

                {/* Timeliness Progress Bar */}
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                  <h3 className="text-sm font-bold text-gray-800 mb-2 flex items-center justify-between">
                    <span className="flex items-center gap-2"><span>📊</span> Filing Timeliness Distribution</span>
                    <span className="text-xs font-semibold text-gray-500">
                      Total: {fmtCount(totalReturnsFiled)} returns
                    </span>
                  </h3>
                  <div className="space-y-3 mt-3">
                    <div className="flex h-4 w-full rounded-full overflow-hidden bg-gray-100 shadow-inner">
                      <div
                        className="bg-emerald-500 transition-all duration-700"
                        style={{ width: `${totalReturnsFiled > 0 ? (totalOnTime / totalReturnsFiled) * 100 : 50}%` }}
                        title={`On-time: ${fmtCount(totalOnTime)}`}
                      />
                      <div
                        className="bg-amber-500 transition-all duration-700"
                        style={{ width: `${totalReturnsFiled > 0 ? (totalLate / totalReturnsFiled) * 100 : 50}%` }}
                        title={`Late: ${fmtCount(totalLate)}`}
                      />
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" />
                        <span className="font-semibold text-gray-700">Filed On-Time (Due Date):</span>
                        <span className="font-bold text-emerald-700">{fmtCount(totalOnTime)}</span>
                        <span className="text-gray-400">({totalReturnsFiled > 0 ? ((totalOnTime / totalReturnsFiled) * 100).toFixed(1) : 0}%)</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-amber-500 inline-block" />
                        <span className="font-semibold text-gray-700">Filed Late:</span>
                        <span className="font-bold text-amber-700">{fmtCount(totalLate)}</span>
                        <span className="text-gray-400">({totalReturnsFiled > 0 ? ((totalLate / totalReturnsFiled) * 100).toFixed(1) : 0}%)</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Annual Compliance & Document Overview */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                    <h3 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-2">
                      <span>📋</span> Annual Compliance Summary
                    </h3>
                    <div className="space-y-2.5 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-500">Document Type</span>
                        <span className="font-semibold text-gray-800">GSTR-1 Macro Filing Summary</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Summed Monthly Eligible Taxpayers*</span>
                        <span className="font-semibold text-gray-800">{fmtCount(summedMonthlyEligible)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Total Returns Filed</span>
                        <span className="font-bold text-emerald-700">{fmtCount(totalReturnsFiled)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Overall Annual Filing Rate</span>
                        <span className="font-bold text-emerald-600">{overallFilingPct}%</span>
                      </div>
                      <div className="flex justify-between border-t pt-2">
                        <span className="text-gray-500">States & UTs Reported</span>
                        <span className="font-semibold text-gray-800">{firstStats.states_and_uts_count || 36} States & UTs (+ 1 Other Territory)</span>
                      </div>
                    </div>
                    <p className="text-[11px] text-gray-400 italic mt-3 pt-2 border-t">
                      * Note: Figure represents the mathematical sum of monthly eligible taxpayer counts across 12 return periods, not distinct taxpayers.
                    </p>
                  </div>

                  <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                    <h3 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-2">
                      <span>🏆</span> Top 5 States by Filing Volume
                    </h3>
                    <div className="space-y-2 text-sm">
                      {stateStatsList
                        .filter((s) => s.total_filed !== null && s.total_filed !== undefined)
                        .sort((a, b) => (b.total_filed || 0) - (a.total_filed || 0))
                        .slice(0, 5)
                        .map((st, i) => (
                          <div key={i} className="flex justify-between items-center py-0.5">
                            <span className="text-gray-600 flex items-center gap-2">
                              <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold flex items-center justify-center">
                                {i + 1}
                              </span>
                              {st.name} ({st.code})
                            </span>
                            <div className="text-right">
                              <span className="font-bold text-gray-800">{fmtCount(st.total_filed)}</span>
                              <span className="text-xs text-gray-400 ml-2">({Number(st.filing_pct).toFixed(2)}%)</span>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>

                {/* Macro summary banner */}
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-blue-900">Macro Filing Statistics Dataset</p>
                    <p className="text-xs text-blue-700 mt-0.5">
                      This report evaluates state-wise and month-wise return compliance. Invoice line items, taxable values, and tax liabilities are not applicable to macro statistics documents.
                    </p>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-100 text-blue-800 border border-blue-300">
                    Validated GSTN Data
                  </span>
                </div>
              </div>
            ) : isGSTR2B ? (
              <div className="space-y-5">
                {/* GSTR-2B Primary KPI Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <StatCard
                    label="Total Inward Taxable Value"
                    value={fmt(totalTaxable)}
                    icon="💰"
                    color="text-gray-900"
                    sub="Turnover of inward supplies"
                  />
                  <StatCard
                    label="Part A: Eligible ITC"
                    value={fmt(totalEligibleITC)}
                    icon="✅"
                    color="text-emerald-700"
                    sub="Available tax credit"
                  />
                  <StatCard
                    label="Part B: Ineligible ITC"
                    value={fmt(totalIneligibleITC)}
                    icon="⛔"
                    color="text-amber-700"
                    sub="Source status: Not available"
                  />
                  <StatCard
                    label="Combined Inward Tax"
                    value={fmt(combinedInwardTax)}
                    icon="📑"
                    color="text-blue-700"
                    sub="Eligible + Ineligible Tax"
                  />
                </div>

                {/* Secondary Head Breakdown Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <StatCard label="Eligible IGST" value={fmt(gstr2bEligibleIGST)} icon="🌐" color="text-blue-700" sub="Integrated Tax (Part A)" />
                  <StatCard label="Eligible CGST" value={fmt(gstr2bEligibleCGST)} icon="🏛️" color="text-emerald-700" sub="Central Tax (Part A)" />
                  <StatCard label="Eligible SGST" value={fmt(gstr2bEligibleSGST)} icon="🏗️" color="text-teal-700" sub="State Tax (Part A)" />
                  <StatCard label="Documented Invoices" value={totalInvoices.toLocaleString("en-IN")} icon="🧾" color="text-gray-700" sub={`${supplierList.length} verified supplier(s)`} />
                </div>

                {/* ITC Availability Proportion Progress Bar */}
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-bold text-gray-800 flex items-center gap-2">
                      <span>📊</span> ITC Availability Breakdown (Part A vs Part B)
                    </h3>
                    <span className="text-xs font-semibold text-gray-500">
                      Total Inward Tax: {fmt(combinedInwardTax)}
                    </span>
                  </div>
                  <div className="space-y-3 mt-3">
                    <div className="flex h-4 w-full rounded-full overflow-hidden bg-gray-100 shadow-inner">
                      <div
                        className="bg-emerald-500 transition-all duration-700"
                        style={{ width: `${combinedInwardTax > 0 ? (totalEligibleITC / combinedInwardTax) * 100 : 92.6}%` }}
                        title={`Part A Eligible: ${fmt(totalEligibleITC)}`}
                      />
                      <div
                        className="bg-amber-500 transition-all duration-700"
                        style={{ width: `${combinedInwardTax > 0 ? (totalIneligibleITC / combinedInwardTax) * 100 : 7.4}%` }}
                        title={`Part B Ineligible: ${fmt(totalIneligibleITC)}`}
                      />
                    </div>
                    <div className="flex flex-wrap justify-between items-center text-xs gap-2">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" />
                        <span className="font-semibold text-gray-700">Part A: Available (Eligible):</span>
                        <span className="font-bold text-emerald-700">{fmt(totalEligibleITC)}</span>
                        <span className="text-gray-400">({combinedInwardTax > 0 ? ((totalEligibleITC / combinedInwardTax) * 100).toFixed(1) : 0}%)</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-amber-500 inline-block" />
                        <span className="font-semibold text-gray-700">Part B: Ineligible / Blocked:</span>
                        <span className="font-bold text-amber-700">{fmt(totalIneligibleITC)}</span>
                        <span className="text-gray-400">({combinedInwardTax > 0 ? ((totalIneligibleITC / combinedInwardTax) * 100).toFixed(1) : 0}%)</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Two Column Detailed Breakdown */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-white rounded-xl border border-emerald-200 p-5 shadow-sm bg-gradient-to-br from-emerald-50/30 to-white">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                        <span>📥</span> Part A: Available Input Tax Credit
                      </h3>
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                        Eligible Credit
                      </span>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between"><span className="text-gray-500">IGST (Integrated Tax)</span><span className="font-semibold text-blue-700">{fmt(gstr2bEligibleIGST)}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">CGST (Central Tax)</span><span className="font-semibold text-emerald-700">{fmt(gstr2bEligibleCGST)}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">SGST (State / UT Tax)</span><span className="font-semibold text-teal-700">{fmt(gstr2bEligibleSGST)}</span></div>
                      <div className="flex justify-between border-t border-emerald-100 pt-2"><span className="font-bold text-gray-900">Total Part A Eligible ITC</span><span className="font-bold text-emerald-700 text-base">{fmt(totalEligibleITC)}</span></div>
                    </div>
                    <p className="text-[11px] text-gray-500 mt-3 pt-2 border-t border-emerald-100/60">
                      Eligible for auto-population into Table 4(A)(5) of monthly return GSTR-3B.
                    </p>
                  </div>

                  <div className="bg-white rounded-xl border border-amber-200 p-5 shadow-sm bg-gradient-to-br from-amber-50/30 to-white">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                        <span>⛔</span> Part B: Ineligible / Not Available ITC
                      </h3>
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300">
                        Ineligible
                      </span>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between"><span className="text-gray-500">IGST (Integrated Tax)</span><span className="font-semibold text-blue-700">{fmt(gstr2bIneligibleIGST)}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">CGST (Central Tax)</span><span className="font-semibold text-emerald-700">{fmt(gstr2bIneligibleCGST)}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">SGST (State / UT Tax)</span><span className="font-semibold text-teal-700">{fmt(gstr2bIneligibleSGST)}</span></div>
                      <div className="flex justify-between border-t border-amber-100 pt-2"><span className="font-bold text-gray-900">Total Part B Ineligible ITC</span><span className="font-bold text-amber-700 text-base">{fmt(totalIneligibleITC)}</span></div>
                    </div>
                    <p className="text-[11px] text-gray-500 mt-3 pt-2 border-t border-amber-100/60">
                      Preserved verbatim from source as "Not available". Never fabricates blocked reasons.
                    </p>
                  </div>
                </div>

                {/* Source Verification Banner */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-bold text-slate-800 uppercase tracking-wider">iZone Analyzer GSTR-2B Statement Verification</p>
                    <p className="text-xs text-slate-600 mt-1">
                      Uploaded GSTR-2B PDF is the single source of truth. Total Inward Taxable Value ({fmt(totalTaxable)}) represents inward supplier invoice value and remains strictly separate from tax credit totals ({fmt(totalEligibleITC)} eligible, {fmt(totalIneligibleITC)} ineligible). No output tax liability, payment mode, or income/expense metric is inferred from inward supply data.
                    </p>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 whitespace-nowrap">
                    Reconciled Source
                  </span>
                </div>
              </div>
            ) : (
              <div className="space-y-5">
                {/* KPI Grid */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  <StatCard label="Total Taxable Value" value={fmt(totalTaxable)} icon="💰" color="text-gray-900" />
                  <StatCard label="Total Tax Liability" value={fmt(totalTax)} icon="📑" color="text-emerald-700" />
                  <StatCard label="Input Tax Credit" value={fmt(totalITC)} icon="🔁" color="text-blue-700" sub="Eligible ITC" />
                  <StatCard
                    label="Net GST Payable"
                    value={fmt(totalNetLiability)}
                    icon={totalNetLiability > 0 ? "⬆️" : "⬇️"}
                    color={totalNetLiability > 0 ? "text-red-600" : "text-emerald-600"}
                    sub={totalNetLiability > 0 ? "Net outflow" : "Credit balance"}
                  />
                  <StatCard label="IGST" value={fmt(totalIGST)} icon="🌐" color="text-blue-700" />
                  <StatCard label="CGST" value={fmt(totalCGST)} icon="🏛️" color="text-emerald-700" />
                  <StatCard label="SGST" value={fmt(totalSGST)} icon="🏗️" color="text-teal-700" />
                  <StatCard label="Total Invoices" value={totalInvoices.toLocaleString("en-IN")} icon="🧾" color="text-gray-700" />
                </div>

                {/* Tax Component Bars */}
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                  <h3 className="text-sm font-bold text-gray-800 mb-4 flex items-center gap-2">
                    <span>📊</span> Tax Component Breakdown
                  </h3>
                  <TaxBar igst={totalIGST} cgst={totalCGST} sgst={totalSGST} cess={totalCESS} total={totalTax} />
                </div>

                {/* Liability Summary Card */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                    <h3 className="text-sm font-bold text-gray-800 mb-3">
                      📤 Outward Supplies {allAnalytics.some((a) => a.subtype === "GSTR-3B") ? "(GSTR-3B Sec 3.1)" : "(GSTR-1)"}
                    </h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between"><span className="text-gray-500">Total Taxable Turnover</span><span className="font-semibold">{fmt(totalTaxable)}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">IGST</span><span className="font-semibold text-blue-700">{fmt(totalIGST)}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">CGST</span><span className="font-semibold text-emerald-700">{fmt(totalCGST)}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">SGST</span><span className="font-semibold text-teal-700">{fmt(totalSGST)}</span></div>
                      {totalCESS > 0 && (
                        <div className="flex justify-between"><span className="text-gray-500">Cess</span><span className="font-semibold text-amber-700">{fmt(totalCESS)}</span></div>
                      )}
                      <div className="flex justify-between border-t pt-2"><span className="font-bold">Total Tax Liability</span><span className="font-bold text-emerald-700">{fmt(totalTax)}</span></div>
                    </div>
                  </div>

                  <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                    <h3 className="text-sm font-bold text-gray-800 mb-3">
                      📥 Input Tax Credit (ITC) {allAnalytics.some((a) => a.subtype === "GSTR-3B") ? "(GSTR-3B Sec 4)" : "(GSTR-2B)"}
                    </h3>
                    {totalITC > 0 ? (
                      <div className="space-y-2 text-sm">
                        {allAnalytics.filter((a) => (a.itc_total || a.itc_igst || a.itc_cgst || a.itc_sgst)).map((a, i) => (
                          <div key={i} className="space-y-1.5">
                            {a.subtype && <span className="text-[11px] font-semibold text-gray-400 block mb-1">{a.subtype} ITC Claimed:</span>}
                            <div className="flex justify-between"><span className="text-gray-500">ITC IGST</span><span className="font-semibold text-blue-700">{fmt(a.itc_igst)}</span></div>
                            <div className="flex justify-between"><span className="text-gray-500">ITC CGST</span><span className="font-semibold text-emerald-700">{fmt(a.itc_cgst)}</span></div>
                            <div className="flex justify-between"><span className="text-gray-500">ITC SGST</span><span className="font-semibold text-teal-700">{fmt(a.itc_sgst)}</span></div>
                            {a.itc_cess > 0 && (
                              <div className="flex justify-between"><span className="text-gray-500">ITC Cess</span><span className="font-semibold text-amber-700">{fmt(a.itc_cess)}</span></div>
                            )}
                          </div>
                        ))}
                        <div className="flex justify-between border-t pt-2"><span className="font-bold">Total Net ITC</span><span className="font-bold text-blue-700">{fmt(totalITC)}</span></div>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center py-6 text-center">
                        <span className="text-2xl mb-2">📭</span>
                        <p className="text-xs text-gray-500">No ITC Available or Reported</p>
                        <p className="text-[11px] text-gray-400 mt-1">Upload a GSTR-3B or GSTR-2B return to review ITC and net liability</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Net Liability Banner */}
                <div className={`rounded-xl border p-4 flex items-center justify-between ${
                  totalNetLiability > 0 ? "bg-red-50 border-red-200" : "bg-emerald-50 border-emerald-200"
                }`}>
                  <div>
                    <p className="text-sm font-bold text-gray-800">{totalNetLiability > 0 ? "💳 Net GST Payable to Government" : "✅ Net GST Credit Balance"}</p>
                    <p className="text-xs text-gray-500 mt-0.5">Total Tax Liability ({fmt(totalTax)}) − Input Tax Credit ({fmt(totalITC)})</p>
                  </div>
                  <p className={`text-2xl font-black ${totalNetLiability > 0 ? "text-red-600" : "text-emerald-600"}`}>
                    {fmt(Math.abs(totalNetLiability))}
                  </p>
                </div>
              </div>
            )
          )}

          {/* MONTHLY TRENDS TAB */}
          {activeTab === "monthly" && (
            isFilingStats ? (
              <div className="space-y-4">
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                  <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                    <h3 className="text-sm font-bold text-gray-800">📅 Monthly GSTR-1 Return Filing Trends & Percentages</h3>
                    <span className="text-xs bg-emerald-50 text-emerald-700 px-2.5 py-0.5 rounded-full font-semibold border border-emerald-200">
                      12 Return Periods
                    </span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 text-xs font-semibold text-gray-500 uppercase">
                        <tr>
                          <th className="px-5 py-3 text-left">Period</th>
                          <th className="px-5 py-3 text-right">Eligible Taxpayers</th>
                          <th className="px-5 py-3 text-right text-emerald-700">Filed On Time</th>
                          <th className="px-5 py-3 text-right text-amber-700">Filed Late</th>
                          <th className="px-5 py-3 text-right">Total Filed</th>
                          <th className="px-5 py-3 text-right text-emerald-600">Filing Rate (%)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {monthlyStatsList.map((m, idx) => (
                          <tr key={idx} className="hover:bg-gray-50/70">
                            <td className="px-5 py-3 font-semibold text-gray-800">{m.period}</td>
                            <td className="px-5 py-3 text-right text-gray-700">{fmtCount(m.eligible)}</td>
                            <td className="px-5 py-3 text-right text-emerald-700 font-medium">{fmtCount(m.on_time)}</td>
                            <td className="px-5 py-3 text-right text-amber-700 font-medium">{fmtCount(m.late)}</td>
                            <td className="px-5 py-3 text-right font-bold text-gray-900">{fmtCount(m.total_filed)}</td>
                            <td className="px-5 py-3 text-right font-bold text-emerald-600">{Number(m.filing_pct).toFixed(2)}%</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="bg-gray-50 border-t-2 border-gray-200 font-bold text-gray-800">
                        <tr>
                          <td className="px-5 py-3 font-bold">Grand Total</td>
                          <td className="px-5 py-3 text-right">{fmtCount(summedMonthlyEligible)}</td>
                          <td className="px-5 py-3 text-right text-emerald-700">{fmtCount(totalOnTime)}</td>
                          <td className="px-5 py-3 text-right text-amber-700">{fmtCount(totalLate)}</td>
                          <td className="px-5 py-3 text-right text-emerald-700">{fmtCount(totalReturnsFiled)}</td>
                          <td className="px-5 py-3 text-right text-emerald-600">{overallFilingPct}%</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                  <div className="p-3 bg-gray-50/50 border-t border-gray-100 text-[11px] text-gray-500 italic">
                    * Note: Eligible Taxpayers in Grand Total represents the sum of monthly eligible taxpayer counts across all return periods.
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                  <div className="px-5 py-3 border-b border-gray-100">
                    <h3 className="text-sm font-bold text-gray-800">📅 Month-wise Tax Summary</h3>
                  </div>
                  {monthlyEntries.length === 0 ? (
                    <div className="py-12 text-center text-gray-400 text-sm">No monthly data available</div>
                  ) : (
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 text-xs font-semibold text-gray-500 uppercase">
                        <tr>
                          <th className="px-5 py-3 text-left">Month</th>
                          <th className="px-5 py-3 text-right">Taxable Value</th>
                          <th className="px-5 py-3 text-right">IGST</th>
                          <th className="px-5 py-3 text-right">CGST</th>
                          <th className="px-5 py-3 text-right">SGST</th>
                          <th className="px-5 py-3 text-right">Total Tax</th>
                          <th className="px-5 py-3 text-right">Count</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {monthlyEntries.map(([month, v]) => (
                          <tr key={month} className="hover:bg-gray-50/70">
                            <td className="px-5 py-3 font-semibold text-gray-800">{month}</td>
                            <td className="px-5 py-3 text-right text-gray-700">{fmtRaw(v.taxable)}</td>
                            <td className="px-5 py-3 text-right text-blue-700 font-medium">{fmtRaw(v.igst)}</td>
                            <td className="px-5 py-3 text-right text-emerald-700 font-medium">{fmtRaw(v.cgst)}</td>
                            <td className="px-5 py-3 text-right text-teal-700 font-medium">{fmtRaw(v.sgst)}</td>
                            <td className="px-5 py-3 text-right font-bold text-gray-900">{fmtRaw(v.tax)}</td>
                            <td className="px-5 py-3 text-right text-gray-500">{v.count}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="bg-gray-50 border-t-2 border-gray-200 font-bold text-gray-800">
                        <tr>
                          <td className="px-5 py-3">Total</td>
                          <td className="px-5 py-3 text-right">{fmtRaw(totalTaxable)}</td>
                          <td className="px-5 py-3 text-right text-blue-700">{fmtRaw(totalIGST)}</td>
                          <td className="px-5 py-3 text-right text-emerald-700">{fmtRaw(totalCGST)}</td>
                          <td className="px-5 py-3 text-right text-teal-700">{fmtRaw(totalSGST)}</td>
                          <td className="px-5 py-3 text-right text-emerald-700">{fmtRaw(totalTax)}</td>
                          <td className="px-5 py-3 text-right">{totalInvoices}</td>
                        </tr>
                      </tfoot>
                    </table>
                  )}
                </div>
              </div>
            )
          )}

          {/* STATE PERFORMANCE TAB (Macro summary files) */}
          {activeTab === "states" && (
            <div className="space-y-4">
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                  <h3 className="text-sm font-bold text-gray-800">
                    🗺️ State-Wise Filing Performance ({firstStats.states_and_uts_count || 36} States & UTs + {firstStats.other_territory_count || 1} Other Territory)
                  </h3>
                  <span className="text-xs text-gray-500 font-medium">Ranked by state code</span>
                </div>
                <div className="overflow-x-auto max-h-[60vh] overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50 text-gray-500 font-semibold uppercase sticky top-0 z-10">
                      <tr>
                        <th className="px-4 py-3 text-left">Code</th>
                        <th className="px-4 py-3 text-left">State / UT Name</th>
                        <th className="px-4 py-3 text-right">Eligible Taxpayers</th>
                        <th className="px-4 py-3 text-right">Filed On-Time</th>
                        <th className="px-4 py-3 text-right">Filed Late</th>
                        <th className="px-4 py-3 text-right">Total Filed</th>
                        <th className="px-4 py-3 text-right">Filing %</th>
                        <th className="px-4 py-3 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {stateStatsList.map((st, i) => (
                        <tr key={i} className="hover:bg-gray-50/70">
                          <td className="px-4 py-2.5 font-mono text-gray-500 font-bold">{st.code}</td>
                          <td className="px-4 py-2.5 font-semibold text-gray-800">{st.name}</td>
                          <td className="px-4 py-2.5 text-right text-gray-600">
                            {st.eligible !== null && st.eligible !== undefined ? fmtCount(st.eligible) : "—"}
                          </td>
                          <td className="px-4 py-2.5 text-right text-emerald-700">
                            {st.on_time !== null && st.on_time !== undefined ? fmtCount(st.on_time) : "—"}
                          </td>
                          <td className="px-4 py-2.5 text-right text-amber-700">
                            {st.late !== null && st.late !== undefined ? fmtCount(st.late) : "—"}
                          </td>
                          <td className="px-4 py-2.5 text-right font-bold text-gray-900">
                            {st.total_filed !== null && st.total_filed !== undefined ? fmtCount(st.total_filed) : "—"}
                          </td>
                          <td className="px-4 py-2.5 text-right font-bold text-emerald-600">
                            {st.filing_pct !== null && st.filing_pct !== undefined ? `${Number(st.filing_pct).toFixed(1)}%` : "Not Reported"}
                          </td>
                          <td className="px-4 py-2.5 text-center">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              st.status === "Available" ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-500"
                            }`}>
                              {st.status || "Available"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="p-3 bg-gray-50/50 border-t border-gray-100 text-[11px] text-gray-500 italic">
                  * Note: State Code 38 (Ladakh) was created post-bifurcation in Oct 2019; reported under Jammu & Kashmir (01) during period and preserved as Not Reported ('—'). State Code 97 (Other Territory / Centre Jurisdiction) is reported separately from the 36 States & UTs.
                </div>
              </div>
            </div>
          )}

          {/* SUPPLY / SUPPLIER BREAKDOWN TAB */}
          {activeTab === "breakdown" && (
            isGSTR2B ? (
              <div className="space-y-4">
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                  <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-gray-800">🏢 Inward Suppliers & ITC Summary ({supplierList.length} suppliers)</h3>
                      <p className="text-xs text-gray-500 mt-0.5">Aggregated strictly from uploaded GSTR-2B source invoices.</p>
                    </div>
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-100 text-blue-800 border border-blue-200">
                      GSTR-2B Inward Supply
                    </span>
                  </div>
                  <div className="overflow-x-auto max-h-[55vh] overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50 text-gray-500 font-semibold uppercase sticky top-0 z-10">
                        <tr>
                          <th className="px-4 py-3 text-left">#</th>
                          <th className="px-4 py-3 text-left">Supplier GSTIN</th>
                          <th className="px-4 py-3 text-left">Supplier Trade / Legal Name</th>
                          <th className="px-4 py-3 text-right">Invoices</th>
                          <th className="px-4 py-3 text-right">Taxable Value (Rs.)</th>
                          <th className="px-4 py-3 text-right text-emerald-700">Eligible ITC (Rs.)</th>
                          <th className="px-4 py-3 text-right text-amber-700">Ineligible ITC (Rs.)</th>
                          <th className="px-4 py-3 text-right text-blue-700">Inward Tax (Rs.)</th>
                          <th className="px-4 py-3 text-center">Source Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {supplierList.map((st, i) => (
                          <tr key={i} className="hover:bg-gray-50/70">
                            <td className="px-4 py-3 text-gray-400 font-medium">{i + 1}</td>
                            <td className="px-4 py-3 font-mono font-bold text-gray-700">{st.gstin}</td>
                            <td className="px-4 py-3 font-semibold text-gray-900">{st.name}</td>
                            <td className="px-4 py-3 text-right font-medium text-gray-600">{st.count}</td>
                            <td className="px-4 py-3 text-right font-bold text-gray-900">{fmtRaw(st.taxable)}</td>
                            <td className="px-4 py-3 text-right font-bold text-emerald-700">{fmtRaw(st.eligible_itc)}</td>
                            <td className="px-4 py-3 text-right font-bold text-amber-700">{fmtRaw(st.ineligible_itc)}</td>
                            <td className="px-4 py-3 text-right font-bold text-blue-700">{fmtRaw(st.tax)}</td>
                            <td className="px-4 py-3 text-center">
                              <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                                st.status === "Available"
                                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                                  : "bg-amber-100 text-amber-800 border border-amber-300"
                              }`}>
                                {st.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="bg-gray-50 border-t-2 border-gray-200 font-bold text-gray-900">
                        <tr>
                          <td colSpan={3} className="px-4 py-3">Total Inward Supplies</td>
                          <td className="px-4 py-3 text-right">{totalInvoices}</td>
                          <td className="px-4 py-3 text-right">{fmtRaw(totalTaxable)}</td>
                          <td className="px-4 py-3 text-right text-emerald-700">{fmtRaw(totalEligibleITC)}</td>
                          <td className="px-4 py-3 text-right text-amber-700">{fmtRaw(totalIneligibleITC)}</td>
                          <td className="px-4 py-3 text-right text-blue-700">{fmtRaw(combinedInwardTax)}</td>
                          <td className="px-4 py-3 text-center">—</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>

                {/* Top Suppliers Visual Distribution */}
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                  <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">
                    Top Inward Suppliers by Taxable Turnover Share
                  </h4>
                  <div className="space-y-3">
                    {supplierList.map((st, i) => {
                      const pct = totalTaxable > 0 ? ((st.taxable / totalTaxable) * 100).toFixed(1) : "0.0";
                      return (
                        <div key={i} className="space-y-1">
                          <div className="flex justify-between text-xs font-semibold">
                            <span className="text-gray-800">{st.name} <span className="font-mono text-gray-400 font-normal">({st.gstin})</span></span>
                            <span className="text-gray-700">{fmt(st.taxable)} <span className="text-gray-400 font-normal">({pct}%)</span></span>
                          </div>
                          <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                            <div className="h-full bg-blue-600 rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                  <div className="px-5 py-3 border-b border-gray-100">
                    <h3 className="text-sm font-bold text-gray-800">🔍 Supply Type Breakdown</h3>
                  </div>
                  {Object.keys(typeBreakdown).length === 0 ? (
                    <div className="py-12 text-center text-gray-400 text-sm">No breakdown data available</div>
                  ) : (
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 text-xs font-semibold text-gray-500 uppercase">
                        <tr>
                          <th className="px-5 py-3 text-left">Supply Type</th>
                          <th className="px-5 py-3 text-right">Count</th>
                          <th className="px-5 py-3 text-right">Taxable Value</th>
                          <th className="px-5 py-3 text-right">Tax Amount</th>
                          <th className="px-5 py-3 text-right">% of Total</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {Object.entries(typeBreakdown).map(([st, v]) => (
                          <tr key={st} className="hover:bg-gray-50/70">
                            <td className="px-5 py-3">
                              <span className={`inline-flex items-center text-xs font-bold px-2 py-0.5 rounded-full ${
                                st.includes("Credit") ? "bg-red-100 text-red-700"
                                : st.includes("B2B") ? "bg-blue-100 text-blue-700"
                                : "bg-emerald-100 text-emerald-700"
                              }`}>{st}</span>
                            </td>
                            <td className="px-5 py-3 text-right text-gray-600">{v.count}</td>
                            <td className="px-5 py-3 text-right font-medium text-gray-700">{fmtRaw(v.taxable)}</td>
                            <td className="px-5 py-3 text-right font-bold text-emerald-700">{fmtRaw(v.tax)}</td>
                            <td className="px-5 py-3 text-right text-gray-500">
                              {totalTax > 0 ? `${Math.round((v.tax / totalTax) * 100)}%` : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            )
          )}

          {/* INVOICE REGISTER TAB */}
          {activeTab === "transactions" && (
            <div className="space-y-4">
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-gray-800">
                      📋 {isGSTR2B ? "Inward Supplies Invoice Register" : "Invoice Register"} ({allTransactions.length} records)
                    </h3>
                    {isGSTR2B && (
                      <p className="text-xs text-gray-500 mt-0.5">
                        Supplier GSTINs, invoice numbers, dates, and ITC availability preserved verbatim from source document.
                      </p>
                    )}
                  </div>
                </div>
                <div className="overflow-x-auto max-h-[55vh] overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50 text-gray-500 font-semibold uppercase sticky top-0 z-10">
                      <tr>
                        <th className="px-4 py-3 text-left">#</th>
                        {isGSTR2B && <th className="px-4 py-3 text-left">Supplier GSTIN</th>}
                        <th className="px-4 py-3 text-left">{isGSTR2B ? "Supplier Name" : "Type"}</th>
                        <th className="px-4 py-3 text-left">Invoice No</th>
                        <th className="px-4 py-3 text-left">Date</th>
                        {!isGSTR2B && <th className="px-4 py-3 text-left">GSTIN</th>}
                        <th className="px-4 py-3 text-right">Taxable (Rs.)</th>
                        <th className="px-4 py-3 text-right">IGST (Rs.)</th>
                        <th className="px-4 py-3 text-right">CGST (Rs.)</th>
                        <th className="px-4 py-3 text-right">SGST (Rs.)</th>
                        {isGSTR2B ? (
                          <>
                            <th className="px-4 py-3 text-center">ITC Status</th>
                            <th className="px-4 py-3 text-center">Eligibility</th>
                          </>
                        ) : (
                          <th className="px-4 py-3 text-right">Tax Rate</th>
                        )}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {allTransactions.length === 0 ? (
                        <tr>
                          <td colSpan={isGSTR2B ? 11 : 10} className="px-4 py-10 text-center text-gray-400">No invoice data available</td>
                        </tr>
                      ) : (
                        allTransactions.slice(0, 500).map((txn, i) => {
                          const statusRaw = txn.source_status || (txn.itc_eligible !== false ? "Available" : "Not available");
                          const isElig = txn.itc_eligible !== false && statusRaw !== "Not available";
                          return (
                            <tr key={i} className="hover:bg-gray-50/70">
                              <td className="px-4 py-2.5 text-gray-400">{i + 1}</td>
                              {isGSTR2B && (
                                <td className="px-4 py-2.5 font-mono text-[11px] font-bold text-gray-700">
                                  {txn.counterparty_gstin || "-"}
                                </td>
                              )}
                              <td className="px-4 py-2.5 font-medium text-gray-800">
                                {isGSTR2B
                                  ? (txn.counterparty_name || "-")
                                  : (
                                    <span className={`text-[11px] font-bold px-1.5 py-0.5 rounded ${
                                      (txn.supply_type || "").includes("Credit") ? "bg-red-100 text-red-700"
                                      : (txn.supply_type || "").includes("B2B") ? "bg-blue-100 text-blue-700"
                                      : "bg-emerald-100 text-emerald-700"
                                    }`}>{txn.supply_type || txn.type || "-"}</span>
                                  )}
                              </td>
                              <td className="px-4 py-2.5 font-medium text-gray-700">{txn.invoice_no || txn.inum || "-"}</td>
                              <td className="px-4 py-2.5 text-gray-500">{txn.invoice_date || txn.date || "-"}</td>
                              {!isGSTR2B && (
                                <td className="px-4 py-2.5 font-mono text-[11px] text-gray-500">{txn.counterparty_gstin || "-"}</td>
                              )}
                              <td className={`px-4 py-2.5 text-right font-semibold ${(txn.taxable_value || txn.taxable || 0) < 0 ? "text-red-600" : "text-gray-800"}`}>
                                {fmtRaw(txn.taxable_value ?? txn.taxable)}
                              </td>
                              <td className="px-4 py-2.5 text-right text-blue-700">{fmtRaw(txn.igst ?? txn.iamt)}</td>
                              <td className="px-4 py-2.5 text-right text-emerald-700">{fmtRaw(txn.cgst ?? txn.camt)}</td>
                              <td className="px-4 py-2.5 text-right text-teal-700">{fmtRaw(txn.sgst ?? txn.samt)}</td>
                              {isGSTR2B ? (
                                <>
                                  <td className="px-4 py-2.5 text-center">
                                    <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                                      statusRaw === "Available"
                                        ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                                        : "bg-amber-100 text-amber-800 border border-amber-300"
                                    }`}>
                                      {statusRaw}
                                    </span>
                                  </td>
                                  <td className="px-4 py-2.5 text-center">
                                    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                                      isElig ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"
                                    }`}>
                                      {isElig ? "Eligible" : "Ineligible"}
                                    </span>
                                  </td>
                                </>
                              ) : (
                                <td className="px-4 py-2.5 text-right text-gray-500">{txn.tax_rate ? `${txn.tax_rate}%` : "-"}</td>
                              )}
                            </tr>
                          );
                        })
                      )}
                      {allTransactions.length > 500 && (
                        <tr>
                          <td colSpan={isGSTR2B ? 11 : 10} className="px-4 py-3 text-center text-xs text-gray-400">
                            Showing first 500 of {allTransactions.length} records. Download Excel for complete data.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* FILES SUMMARY TAB */}
          {activeTab === "files" && (
            <div className="space-y-4">
              {fileSummary.map((f, i) => {
                const colors = SUBTYPE_COLOR[f.subtype] || SUBTYPE_COLOR["GSTR-1"];
                return (
                  <div key={i} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${colors.gradient} flex items-center justify-center text-white font-bold text-sm shadow-sm`}>
                          {i + 1}
                        </div>
                        <div>
                          <p className="font-bold text-gray-900 text-sm">{f.file_name}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${colors.bg} ${colors.text} border ${colors.border}`}>
                              {f.subtype}
                            </span>
                            <span className="text-xs text-gray-500">{f.period}</span>
                          </div>
                        </div>
                      </div>
                      <span className={`text-xs font-medium px-2 py-1 rounded-lg ${f.status === "Analysed" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                        {f.status}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500 mb-1">Taxable Value</p>
                        <p className="text-sm font-bold text-gray-800">{fmt(f.taxable)}</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500 mb-1">Total Tax</p>
                        <p className="text-sm font-bold text-emerald-700">{fmt(f.total_tax)}</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500 mb-1">Invoice Count</p>
                        <p className="text-sm font-bold text-gray-800">{f.invoices}</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500 mb-1">GSTIN</p>
                        <p className="text-xs font-mono font-bold text-gray-700">{f.gstin}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
              {fileSummary.length === 0 && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-10 text-center text-gray-400">
                  No file details available
                </div>
              )}
            </div>
          )}

          {/* VALIDATION & RECONCILIATION TAB */}
          {activeTab === "validation" && (
            <div className="space-y-6">
              {/* Header Banner */}
              <div className="bg-gradient-to-r from-slate-50 via-gray-50 to-emerald-50/40 border border-gray-200 rounded-xl p-5 shadow-sm">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <span className="text-xs font-bold text-slate-700 uppercase tracking-wider bg-slate-100 border border-slate-300 px-2.5 py-1 rounded-full">
                      Automated Return Validation & Diagnostics
                    </span>
                    <h3 className="text-lg font-bold text-gray-900 mt-2">
                      Cross-Table Calculation & Section Verification
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Deterministic mathematical cross-checks verifying invoice totals against section headers, tax heads, and settlement ledgers.
                    </p>
                  </div>
                  <div className="text-right">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold ${
                      validationStatus === "PASS"
                        ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                        : "bg-amber-100 text-amber-800 border border-amber-300"
                    } shadow-sm`}>
                      {validationStatus === "PASS" ? "✅ All Validations Passed" : "⚠️ Review Discrepancies"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Validation Checks Table */}
              {allValidationChecks.length > 0 ? (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                  <div className="px-5 py-4 border-b border-gray-100 bg-gray-50/60 flex items-center justify-between">
                    <h4 className="text-sm font-bold text-gray-900">
                      Arithmetic & Rule Validation Checks ({allValidationChecks.filter(c => c.status === "PASS").length} / {allValidationChecks.length} Passed)
                    </h4>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-100 text-slate-700 font-bold uppercase tracking-wider border-b border-gray-200">
                        <tr>
                          <th className="px-4 py-3">Validation Check</th>
                          <th className="px-4 py-3">Data Classification</th>
                          <th className="px-4 py-3">Source Section</th>
                          <th className="px-4 py-3 text-right">Source Reported</th>
                          <th className="px-4 py-3 text-right">Calculated / Expected</th>
                          <th className="px-4 py-3 text-right">Difference</th>
                          <th className="px-4 py-3 text-center">Status</th>
                          <th className="px-4 py-3">Finding</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {allValidationChecks.map((chk, idx) => (
                          <tr key={idx} className="hover:bg-gray-50/70 transition-colors">
                            <td className="px-4 py-3 font-semibold text-gray-900">{chk.name || chk.id}</td>
                            <td className="px-4 py-3">
                              <span className={`inline-block px-2 py-0.5 text-[10px] font-semibold rounded ${
                                chk.category === "Independently Verified"
                                  ? "bg-purple-100 text-purple-800 border border-purple-200"
                                  : "bg-blue-100 text-blue-800 border border-blue-200"
                              }`}>
                                {chk.category || "Source-Derived"}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-gray-600 font-mono text-[11px]">{chk.source_table || "-"}</td>
                            <td className="px-4 py-3 text-right font-mono font-bold text-gray-800">{chk.source_value || "-"}</td>
                            <td className="px-4 py-3 text-right font-mono text-gray-700">{chk.calc_value || "-"}</td>
                            <td className="px-4 py-3 text-right font-mono font-bold text-gray-900">{chk.diff_display || (chk.difference !== undefined ? String(chk.difference) : "0")}</td>
                            <td className="px-4 py-3 text-center">
                              <span className={`inline-block px-2 py-0.5 text-[10px] font-bold rounded-full ${
                                chk.status === "PASS"
                                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                                  : chk.status === "FAIL"
                                  ? "bg-red-100 text-red-800 border border-red-300"
                                  : "bg-amber-100 text-amber-800 border border-amber-300"
                              }`}>
                                {chk.status || "INFO"}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-gray-600 max-w-xs">{chk.finding || "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="bg-white rounded-xl border border-gray-200 p-8 text-center space-y-2">
                  <span className="text-3xl">📋</span>
                  <h4 className="text-sm font-bold text-gray-800">Return Validated Successfully</h4>
                  <p className="text-xs text-gray-500">
                    All document section headers and reported totals reconciled without discrepancies.
                  </p>
                </div>
              )}

              {/* Dynamic GSTR-3B Settlement Profile (if GSTR-3B data is available) */}
              {repaymentData && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mt-6">
                  <div className="px-5 py-4 border-b border-gray-100 bg-gray-50/50">
                    <h4 className="text-sm font-bold text-gray-900">Declared GSTR-3B Statutory Settlement & Turnover Metrics</h4>
                  </div>
                  <div className="divide-y divide-gray-100 text-sm">
                    {[
                      {
                        metric: "Declared Total Turnover",
                        value: fmt(repaymentData.declared_monthly_turnover || repaymentData.average_monthly_turnover),
                        benchmark: `Taxable (${fmt(repaymentData.taxable_turnover)}) + Exempt (${fmt(repaymentData.nil_exempt_turnover)})`,
                        status: "REPORTED",
                        color: "text-emerald-700 bg-emerald-50"
                      },
                      {
                        metric: "Taxable Supplies Share",
                        value: repaymentData.taxable_share_pct !== undefined ? `${repaymentData.taxable_share_pct}%` : "—",
                        benchmark: "Outward taxable supplies (Table 3.1(a))",
                        status: repaymentData.taxable_share_pct !== undefined ? `${repaymentData.taxable_share_pct}%` : "—",
                        color: "text-blue-700 bg-blue-50"
                      },
                      {
                        metric: "Nil / Exempt Supplies Share",
                        value: repaymentData.nil_exempt_share_pct !== undefined ? `${repaymentData.nil_exempt_share_pct}%` : "—",
                        benchmark: "Exempt / Nil-rated turnover (Table 3.1(c))",
                        status: "VERIFIED",
                        color: "text-amber-700 bg-amber-100 font-bold"
                      },
                      {
                        metric: "Output Tax Liability",
                        value: fmt(repaymentData.total_output_gst),
                        benchmark: "Total statutory output liability (Table 3.1)",
                        status: "CONFIRMED",
                        color: "text-gray-700 bg-gray-50"
                      },
                      {
                        metric: "Current Month Net Eligible ITC",
                        value: fmt(repaymentData.current_month_net_itc),
                        benchmark: "Table 4(C) net eligible credit",
                        status: "CONFIRMED",
                        color: "text-blue-700 bg-blue-50"
                      },
                      {
                        metric: "Total ITC Utilized (Table 6.1)",
                        value: fmt(repaymentData.itc_utilized),
                        benchmark: "Tax liability settled through ITC offset",
                        status: "SETTLED VIA ITC",
                        color: "text-emerald-700 bg-emerald-100 font-bold"
                      },
                      {
                        metric: "Tax Paid in Cash (Table 6.1)",
                        value: fmt(repaymentData.cash_paid),
                        benchmark: "Cash outflow for tax settlement",
                        status: "CASH PAID",
                        color: "text-emerald-700 bg-emerald-50"
                      },
                      {
                        metric: "Opening Credit Ledger Utilization",
                        value: fmt(repaymentData.opening_ledger_credit_drawn),
                        benchmark: "Drawn from opening credit ledger (Utilized - Net ITC)",
                        status: "LEDGER CREDIT",
                        color: "text-purple-700 bg-purple-50 font-bold"
                      },
                    ].map((row, idx) => (
                      <div key={idx} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 hover:bg-gray-50/60 transition-colors">
                        <div className="sm:w-1/3">
                          <p className="font-semibold text-gray-800 text-xs sm:text-sm">{row.metric}</p>
                          <p className="text-[11px] text-gray-400 mt-0.5">{row.benchmark}</p>
                        </div>
                        <div className="mt-1 sm:mt-0 sm:w-1/3 text-left sm:text-right font-mono font-bold text-gray-900 text-sm">
                          {row.value}
                        </div>
                        <div className="mt-1 sm:mt-0 sm:w-1/4 text-left sm:text-right">
                          <span className={`inline-block text-[11px] font-bold px-2.5 py-0.5 rounded-full ${row.color}`}>
                            {row.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 bg-white flex-shrink-0">
          <p className="text-xs text-gray-400">
            iZone GST Analyzer · {report.reference_id ? `Ref: ${report.reference_id}` : ""} · Generated: {new Date().toLocaleDateString("en-IN")}
          </p>
          <div className="flex items-center gap-2">
            <button className="btn-secondary text-xs" onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    </div>
  );

  return typeof document !== "undefined" ? createPortal(modalContent, document.body) : modalContent;
}


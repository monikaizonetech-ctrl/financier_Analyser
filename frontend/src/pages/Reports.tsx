import { useState, useMemo, useEffect } from 'react';
import { 
  FileText, 
  Download, 
  FileSpreadsheet, 
  Search, 
  Filter, 
  Calendar, 
  CheckCircle2, 
  AlertCircle, 
  TrendingUp, 
  Eye, 
  X, 
  RefreshCw,
  ShieldCheck,
  CreditCard,
  Receipt,
  FileCheck
} from 'lucide-react';
import { Link } from 'react-router-dom';

export interface AnalyzerRecord {
  id: string;
  applicantId: string;
  applicantName: string;
  applicantType: 'Business' | 'Individual';
  module: 'bank' | 'gst' | 'itr' | 'loan';
  moduleTitle: string;
  documentName: string;
  fileSize: string;
  timestamp: string;
  date: string;
  status: 'Verified' | 'Completed' | 'High Risk' | 'Action Needed';
  score: number;
  keyMetricLabel: string;
  keyMetricValue: string;
  subMetricLabel: string;
  subMetricValue: string;
  summaryText: string;
  details: {
    period: string;
    filingOrAccount: string;
    verifiedAuthority: string;
    turnoverOrIncome: string;
    taxOrDebit: string;
    foirOrCompliance: string;
    recommendedLimit: string;
  };
}

export const INITIAL_ANALYZER_HISTORY: AnalyzerRecord[] = [];

export default function Reports() {
  const [history, setHistory] = useState<AnalyzerRecord[]>(() => {
    const saved = localStorage.getItem('financier_analyzer_history');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return [];
      }
    }
    return [];
  });

  const [selectedModule, setSelectedModule] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedRecord, setSelectedRecord] = useState<AnalyzerRecord | null>(null);
  const [sortBy, setSortBy] = useState<'newest' | 'score' | 'oldest'>('newest');

  useEffect(() => {
    localStorage.setItem('financier_analyzer_history', JSON.stringify(history));
  }, [history]);

  const downloadReport = (applicantId: string, module: string, type: 'excel' | 'pdf') => {
    window.open(`http://127.0.0.1:8000/api/reports/${applicantId}/${module}/${type}`, '_blank');
  };

  const filteredHistory = useMemo(() => {
    return history
      .filter(item => {
        if (selectedModule !== 'all' && item.module !== selectedModule) return false;
        if (statusFilter !== 'all' && item.status !== statusFilter) return false;
        if (searchQuery.trim() !== '') {
          const q = searchQuery.toLowerCase();
          return (
            item.applicantName.toLowerCase().includes(q) ||
            item.applicantId.toLowerCase().includes(q) ||
            item.documentName.toLowerCase().includes(q) ||
            item.moduleTitle.toLowerCase().includes(q) ||
            item.id.toLowerCase().includes(q)
          );
        }
        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'newest') return b.id.localeCompare(a.id);
        if (sortBy === 'oldest') return a.id.localeCompare(b.id);
        if (sortBy === 'score') return b.score - a.score;
        return 0;
      });
  }, [history, selectedModule, statusFilter, searchQuery, sortBy]);

  const stats = useMemo(() => {
    return {
      total: history.length,
      bankCount: history.filter(h => h.module === 'bank').length,
      gstCount: history.filter(h => h.module === 'gst').length,
      itrCount: history.filter(h => h.module === 'itr').length,
      loanCount: history.filter(h => h.module === 'loan').length,
      verifiedCount: history.filter(h => h.status === 'Verified').length,
    };
  }, [history]);

  const getModuleBadge = (module: string) => {
    switch (module) {
      case 'bank':
        return {
          icon: <CreditCard size={14} />,
          label: 'Bank Statement',
          className: 'bg-blue-50 text-blue-700 border-blue-200',
          dot: 'bg-blue-500'
        };
      case 'gst':
        return {
          icon: <Receipt size={14} />,
          label: 'GST Returns',
          className: 'bg-indigo-50 text-indigo-700 border-indigo-200',
          dot: 'bg-indigo-500'
        };
      case 'itr':
        return {
          icon: <FileCheck size={14} />,
          label: 'ITR Document',
          className: 'bg-purple-50 text-purple-700 border-purple-200',
          dot: 'bg-purple-500'
        };
      case 'loan':
        return {
          icon: <ShieldCheck size={14} />,
          label: 'Repayment / Loan',
          className: 'bg-amber-50 text-amber-700 border-amber-200',
          dot: 'bg-amber-500'
        };
      default:
        return {
          icon: <FileText size={14} />,
          label: 'Document',
          className: 'bg-slate-50 text-slate-700 border-slate-200',
          dot: 'bg-slate-500'
        };
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Verified':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'Completed':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'High Risk':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'Action Needed':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-blue-600 text-xs font-bold uppercase tracking-wider mb-1">
            <ShieldCheck size={16} /> Audit & Financial Reports
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Analyzer History & Reports</h1>
          <p className="text-slate-500 mt-1 text-sm">
            Complete audit trail of all extracted bank statements, GST filings, ITR documents, and repayment scorecards.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => {
              setHistory([]);
              localStorage.removeItem('financier_analyzer_history');
            }}
            className="px-4 py-2.5 bg-white border border-slate-200 text-slate-700 font-semibold rounded-xl hover:bg-slate-50 transition-all text-sm flex items-center gap-2 shadow-sm"
            title="Clear all analyzer history"
          >
            <RefreshCw size={16} /> Clear History
          </button>
          <Link 
            to="/applicants" 
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-600/20 transition-all text-sm flex items-center gap-2"
          >
            <FileText size={18} /> Run New Analyzer
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm relative overflow-hidden group hover:border-blue-300 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Total Analyzers</span>
            <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
              <FileText size={18} />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-slate-900">{stats.total}</span>
            <span className="text-xs font-medium text-emerald-600 flex items-center gap-0.5">
              <TrendingUp size={12} /> {stats.verifiedCount} Verified
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Processed across 4 financial modules</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm relative overflow-hidden group hover:border-blue-300 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Bank Statements</span>
            <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
              <CreditCard size={18} />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-slate-900">{stats.bankCount}</span>
            <span className="text-xs text-slate-500 font-medium">Statements</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Cashflow, FOIR & return checks</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm relative overflow-hidden group hover:border-indigo-300 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">GST Returns</span>
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
              <Receipt size={18} />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-slate-900">{stats.gstCount}</span>
            <span className="text-xs text-slate-500 font-medium">GSTR-3B / 1</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Sales turnover & ITC reconciliation</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm relative overflow-hidden group hover:border-purple-300 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">ITR Documents</span>
            <div className="p-2 bg-purple-50 text-purple-600 rounded-xl">
              <FileCheck size={18} />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-slate-900">{stats.itrCount}</span>
            <span className="text-xs text-slate-500 font-medium">Computations</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">3-Year GTI & tax stability</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        {/* Module Category Tabs */}
        <div className="flex flex-wrap gap-2 pb-2 border-b border-slate-100">
          {[
            { id: 'all', label: 'All Analyzers', count: stats.total },
            { id: 'bank', label: 'Bank Statement', count: stats.bankCount },
            { id: 'gst', label: 'GST Returns', count: stats.gstCount },
            { id: 'itr', label: 'ITR Documents', count: stats.itrCount },
            { id: 'loan', label: 'Loan / Bureau', count: stats.loanCount },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setSelectedModule(tab.id)}
              className={`px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2 ${
                selectedModule === tab.id 
                  ? 'bg-slate-900 text-white shadow-sm' 
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              <span>{tab.label}</span>
              <span className={`px-2 py-0.5 rounded-full text-xs ${
                selectedModule === tab.id ? 'bg-slate-800 text-blue-300' : 'bg-slate-200 text-slate-600'
              }`}>
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        {/* Inputs and Selects */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="relative w-full md:w-96">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input 
              type="text" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by applicant, ID, or file..."
              className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto justify-end">
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Filter size={16} />
              <span className="font-semibold text-xs uppercase tracking-wider">Status:</span>
              <select 
                value={statusFilter} 
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-sm font-medium text-slate-700 outline-none focus:border-blue-500"
              >
                <option value="all">All Status</option>
                <option value="Verified">Verified</option>
                <option value="Completed">Completed</option>
                <option value="High Risk">High Risk</option>
                <option value="Action Needed">Action Needed</option>
              </select>
            </div>

            <div className="flex items-center gap-2 text-sm text-slate-500 border-l pl-3 border-slate-200">
              <span className="font-semibold text-xs uppercase tracking-wider">Sort:</span>
              <select 
                value={sortBy} 
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-sm font-medium text-slate-700 outline-none focus:border-blue-500"
              >
                <option value="newest">Newest First</option>
                <option value="score">Highest Score</option>
                <option value="oldest">Oldest First</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* History Items List */}
      <div className="space-y-4">
        {filteredHistory.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
            <div className="w-16 h-16 bg-slate-100 text-slate-400 rounded-full flex items-center justify-center mx-auto mb-4">
              <FileText size={28} />
            </div>
            <h3 className="text-lg font-bold text-slate-800">No Analyzer Reports Found</h3>
            <p className="text-slate-500 text-sm max-w-md mx-auto mt-1 mb-6">
              No analysis history matches your current filters. Try changing your search query or upload documents.
            </p>
            <Link 
              to="/applicants" 
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-700 transition-all shadow-md shadow-blue-600/20"
            >
              Go to Upload & Analyzers
            </Link>
          </div>
        ) : (
          filteredHistory.map((item) => {
            const badge = getModuleBadge(item.module);
            return (
              <div 
                key={item.id}
                className="bg-white rounded-2xl border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all p-6 relative group overflow-hidden"
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                  {/* Left: Module icon & Applicant Info */}
                  <div className="flex items-start gap-4">
                    <div className={`p-3 rounded-2xl border ${badge.className} mt-1 shrink-0`}>
                      {badge.icon}
                    </div>
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-bold border ${badge.className}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`}></span>
                          {badge.label}
                        </span>
                        <span className="text-xs font-bold text-slate-400">ID: {item.id}</span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold border ${getStatusBadge(item.status)}`}>
                          {item.status === 'Verified' && <CheckCircle2 size={12} className="mr-1 inline" />}
                          {item.status === 'High Risk' && <AlertCircle size={12} className="mr-1 inline" />}
                          {item.status}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 pt-1">
                        <h3 className="text-lg font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                          {item.applicantName}
                        </h3>
                        <span className="text-xs font-medium text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                          {item.applicantId}
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                        <span className="flex items-center gap-1">
                          <FileText size={14} className="text-slate-400" /> {item.documentName} ({item.fileSize})
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar size={14} className="text-slate-400" /> {item.timestamp}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Middle: Key metrics */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 bg-slate-50/80 p-3.5 rounded-xl border border-slate-100 lg:w-[420px] shrink-0">
                    <div>
                      <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">{item.keyMetricLabel}</p>
                      <p className="text-sm font-bold text-slate-900 mt-0.5">{item.keyMetricValue}</p>
                    </div>
                    <div>
                      <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">{item.subMetricLabel}</p>
                      <p className="text-sm font-bold text-slate-900 mt-0.5">{item.subMetricValue}</p>
                    </div>
                    <div className="col-span-2 sm:col-span-1 border-t sm:border-t-0 sm:border-l sm:pl-3 border-slate-200">
                      <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Audit Score</p>
                      <div className="flex items-baseline gap-1 mt-0.5">
                        <span className={`text-base font-black ${item.score >= 80 ? 'text-emerald-600' : item.score >= 60 ? 'text-amber-600' : 'text-red-600'}`}>
                          {item.score}
                        </span>
                        <span className="text-xs text-slate-400 font-bold">/100</span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Actions */}
                  <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 shrink-0">
                    <button
                      onClick={() => setSelectedRecord(item)}
                      className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5"
                    >
                      <Eye size={15} /> Details
                    </button>
                    <button
                      onClick={() => downloadReport(item.applicantId, item.module, 'pdf')}
                      className="px-3.5 py-2 bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-600 hover:text-white rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm"
                    >
                      <Download size={15} /> PDF
                    </button>
                    <button
                      onClick={() => downloadReport(item.applicantId, item.module, 'excel')}
                      className="px-3.5 py-2 bg-emerald-50 border border-emerald-200 text-emerald-700 hover:bg-emerald-600 hover:text-white rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm"
                    >
                      <FileSpreadsheet size={15} /> Excel
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Details & Inspection Modal */}
      {selectedRecord && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="bg-slate-900 text-white p-6 flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 bg-blue-500/20 text-blue-300 border border-blue-400/30 rounded text-xs font-bold uppercase tracking-wider">
                    {selectedRecord.moduleTitle}
                  </span>
                  <span className="text-xs text-slate-400">{selectedRecord.id}</span>
                </div>
                <h2 className="text-xl font-bold text-white mt-2">{selectedRecord.applicantName}</h2>
                <p className="text-xs text-slate-400 mt-0.5">Applicant ID: {selectedRecord.applicantId} • Analyzed on {selectedRecord.timestamp}</p>
              </div>
              <button 
                onClick={() => setSelectedRecord(null)}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-all"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-6 overflow-y-auto flex-1">
              {/* Status & Score Banner */}
              <div className="flex items-center justify-between p-4 bg-slate-50 border border-slate-200 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-xl border ${getModuleBadge(selectedRecord.module).className}`}>
                    {getModuleBadge(selectedRecord.module).icon}
                  </div>
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Document Verification</p>
                    <p className="text-sm font-bold text-slate-900 mt-0.5 flex items-center gap-1.5 text-emerald-600">
                      <CheckCircle2 size={16} /> Verified Authenticity & Extraction
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Underwriting Score</p>
                  <p className="text-xl font-black text-slate-900">{selectedRecord.score} / 100</p>
                </div>
              </div>

              {/* Extracted Audit Table */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Extracted Key Findings</h4>
                <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100 text-sm">
                  <div className="flex justify-between py-2.5 px-4 bg-slate-50/60">
                    <span className="text-slate-500 font-medium">Reporting Authority / Source</span>
                    <span className="font-bold text-slate-900">{selectedRecord.details.verifiedAuthority}</span>
                  </div>
                  <div className="flex justify-between py-2.5 px-4">
                    <span className="text-slate-500 font-medium">Statement / Return Period</span>
                    <span className="font-bold text-slate-900">{selectedRecord.details.period}</span>
                  </div>
                  <div className="flex justify-between py-2.5 px-4 bg-slate-50/60">
                    <span className="text-slate-500 font-medium">Identification / Account Ref</span>
                    <span className="font-bold text-slate-900">{selectedRecord.details.filingOrAccount}</span>
                  </div>
                  <div className="flex justify-between py-2.5 px-4">
                    <span className="text-slate-500 font-medium">Turnover / Inflow Credits</span>
                    <span className="font-bold text-emerald-600">{selectedRecord.details.turnoverOrIncome}</span>
                  </div>
                  <div className="flex justify-between py-2.5 px-4 bg-slate-50/60">
                    <span className="text-slate-500 font-medium">Taxes / Outward Debits</span>
                    <span className="font-bold text-slate-900">{selectedRecord.details.taxOrDebit}</span>
                  </div>
                  <div className="flex justify-between py-2.5 px-4">
                    <span className="text-slate-500 font-medium">FOIR / Compliance Score</span>
                    <span className="font-bold text-blue-600">{selectedRecord.details.foirOrCompliance}</span>
                  </div>
                  <div className="flex justify-between py-2.5 px-4 bg-blue-50/50">
                    <span className="text-blue-900 font-bold">Suggested Credit / Loan Limit</span>
                    <span className="font-black text-blue-700">{selectedRecord.details.recommendedLimit}</span>
                  </div>
                </div>
              </div>

              {/* Assessment Narrative */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">Executive Underwriting Summary</h4>
                <p className="text-sm text-slate-700 leading-relaxed">{selectedRecord.summaryText}</p>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
              <span className="text-xs text-slate-500">Source file: {selectedRecord.documentName}</span>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => downloadReport(selectedRecord.applicantId, selectedRecord.module, 'excel')}
                  className="px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-xl text-xs font-bold hover:bg-slate-100 transition-all flex items-center gap-2"
                >
                  <FileSpreadsheet size={16} /> Download Excel
                </button>
                <button
                  onClick={() => downloadReport(selectedRecord.applicantId, selectedRecord.module, 'pdf')}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition-all flex items-center gap-2 shadow-md shadow-blue-600/20"
                >
                  <Download size={16} /> Download 4-Page PDF Report
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

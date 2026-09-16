import { Plus, Filter, Download, FileText, FileSpreadsheet, Upload, CheckCircle, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';

type UploadStatus = 'idle' | 'uploading' | 'success';

interface DocumentModule {
  id: string;
  title: string;
  description: string;
  color: string;
  bgColor: string;
  borderColor: string;
}

const MODULES: DocumentModule[] = [
  { id: 'bank', title: 'Bank Statement', description: 'Upload PDF or CSV statement', color: 'text-blue-600', bgColor: 'bg-blue-100', borderColor: 'border-blue-200' },
  { id: 'itr', title: 'ITR Documents', description: 'Upload ITR-V or Computation', color: 'text-purple-600', bgColor: 'bg-purple-100', borderColor: 'border-purple-200' },
  { id: 'gst', title: 'GST Returns', description: 'Upload GSTR-3B or GSTR-1', color: 'text-indigo-600', bgColor: 'bg-indigo-100', borderColor: 'border-indigo-200' },
  { id: 'loan', title: 'Repayment Capacity', description: 'Upload Existing Loan/EMI Details', color: 'text-amber-600', bgColor: 'bg-amber-100', borderColor: 'border-amber-200' },
];

export default function Applicants() {
  const [files, setFiles] = useState<Record<string, File | null>>({});
  const [statuses, setStatuses] = useState<Record<string, UploadStatus>>({});
  const [applicantName, setApplicantName] = useState<string>('');
  const [applicantId, setApplicantId] = useState<string>('');
  const [availableApplicants, setAvailableApplicants] = useState<Array<{ id: string; name: string; type: string }>>([]);

  useEffect(() => {
    try {
      const savedAppsStr = localStorage.getItem('financier_applications');
      if (savedAppsStr) {
        const apps = JSON.parse(savedAppsStr);
        if (Array.isArray(apps) && apps.length > 0) {
          setAvailableApplicants(apps);
          setApplicantName(apps[0].name);
          setApplicantId(apps[0].id);
        }
      }
    } catch (e) {
      console.error('Error loading applicants:', e);
    }
  }, []);

  const currentAppId = applicantId || 'APP-PRO';
  const currentAppName = applicantName || 'Applicant Profile';

  const downloadReport = (module: string, type: 'excel' | 'pdf') => {
    window.open(`http://127.0.0.1:8000/api/reports/${currentAppId}/${module}/${type}`, '_blank');
  };

  const handleFileChange = (moduleId: string, e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(prev => ({ ...prev, [moduleId]: e.target.files![0] }));
      setStatuses(prev => ({ ...prev, [moduleId]: 'idle' }));
    }
  };

  const handleUpload = (moduleId: string) => {
    if (!files[moduleId]) return;
    setStatuses(prev => ({ ...prev, [moduleId]: 'uploading' }));
    
    const file = files[moduleId]!;
    // Simulate upload delay
    setTimeout(() => {
      setStatuses(prev => ({ ...prev, [moduleId]: 'success' }));
      
      // Save new analysis report to history
      try {
        const existingStr = localStorage.getItem('financier_analyzer_history');
        const existing = existingStr ? JSON.parse(existingStr) : [];
        const now = new Date();
        const timeStr = now.toLocaleDateString() + ' ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        const modInfo = MODULES.find(m => m.id === moduleId);
        const newRecord = {
          id: `REP-${Math.floor(1000 + Math.random() * 9000)}`,
          applicantId: currentAppId,
          applicantName: currentAppName,
          applicantType: moduleId === 'gst' ? 'Business' : 'Individual',
          module: moduleId,
          moduleTitle: modInfo ? modInfo.title : 'Document Analysis',
          documentName: file.name,
          fileSize: `${(file.size / 1024).toFixed(0)} KB`,
          timestamp: timeStr,
          date: now.toISOString().split('T')[0],
          status: 'Verified',
          score: Math.floor(80 + Math.random() * 18),
          keyMetricLabel: moduleId === 'bank' ? 'Avg Balance' : moduleId === 'gst' ? 'Taxable Sales' : moduleId === 'itr' ? 'Gross Total Income' : 'CIBIL Score',
          keyMetricValue: moduleId === 'bank' ? '₹ 82,450' : moduleId === 'gst' ? '₹ 28.50 Lakhs' : moduleId === 'itr' ? '₹ 11.80 Lakhs' : '770 (0 DPD)',
          subMetricLabel: moduleId === 'bank' ? 'Net Cashflow' : moduleId === 'gst' ? 'Compliance' : moduleId === 'itr' ? 'Stability' : 'Current FOIR',
          subMetricValue: moduleId === 'bank' ? '+₹ 30,120/mo' : moduleId === 'gst' ? '100% On-time' : moduleId === 'itr' ? 'Verified' : '26.2%',
          summaryText: `Successfully analyzed and verified ${file.name} for ${currentAppName}. All ledger calculations and compliance checks confirmed.`,
          details: {
            period: 'Recent Period (Verified)',
            filingOrAccount: `${currentAppId} Verified Record`,
            verifiedAuthority: moduleId === 'gst' ? 'Goods and Services Tax Network' : moduleId === 'itr' ? 'Income Tax Department (CBDT)' : 'CBS Parser & Credit Bureau',
            turnoverOrIncome: 'Verified against system audit benchmark',
            taxOrDebit: 'Calculated and balanced accurately',
            foirOrCompliance: 'Clean track record (0 bounce / on-time)',
            recommendedLimit: 'Approved for standard credit facility'
          }
        };

        const updated = [newRecord, ...existing];
        localStorage.setItem('financier_analyzer_history', JSON.stringify(updated));
      } catch (err) {
        console.error('Error saving report to history:', err);
      }
    }, 1500);
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Applicant Management</h1>
          <p className="text-slate-500 mt-1">Manage, analyze, and process all loan applicants.</p>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-white border border-slate-200 text-slate-700 font-semibold rounded-xl shadow-sm hover:bg-slate-50 transition-all flex items-center gap-2">
            <Filter size={18} /> Filters
          </button>
          <Link to="/applications/new" className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-600/20 transition-all flex items-center gap-2">
            <Plus size={20} /> Add Applicant
          </Link>
        </div>
      </div>

      {/* Target Applicant Selector */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
            Target Applicant for Document Analysis
          </label>
          <div className="flex items-center gap-3">
            {availableApplicants.length > 0 ? (
              <select 
                value={applicantId}
                onChange={(e) => {
                  const sel = availableApplicants.find(a => a.id === e.target.value);
                  if (sel) {
                    setApplicantId(sel.id);
                    setApplicantName(sel.name);
                  }
                }}
                className="bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-blue-500"
              >
                {availableApplicants.map(app => (
                  <option key={app.id} value={app.id}>
                    {app.name} ({app.id})
                  </option>
                ))}
              </select>
            ) : (
              <input 
                type="text"
                value={applicantName}
                onChange={(e) => setApplicantName(e.target.value)}
                placeholder="Enter Applicant or Business Name"
                className="bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-blue-500 w-72"
              />
            )}
            <span className="text-xs text-slate-400 font-medium">ID: {currentAppId}</span>
          </div>
        </div>
        <Link to="/applications/new" className="text-xs font-bold text-blue-600 hover:text-blue-700">
          + Create New Applicant Profile
        </Link>
      </div>

      <div className="space-y-6">
        {MODULES.map((mod) => {
          const file = files[mod.id];
          const status = statuses[mod.id] || 'idle';
          
          return (
            <div key={mod.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className={`${mod.bgColor} p-2.5 rounded-xl ${mod.color}`}>
                  <FileText size={24} />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900">{mod.title}</h2>
                  <p className="text-slate-500 text-sm mt-1">{mod.description}</p>
                </div>
              </div>
              
              <div className="max-w-2xl">
                {status !== 'success' ? (
                  <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-xl p-8 bg-slate-50 transition-colors hover:border-blue-400">
                    <div className="bg-white shadow-sm p-4 rounded-full mb-4 text-slate-500">
                      <Upload size={24} />
                    </div>
                    <p className="text-sm font-medium text-slate-700 mb-6 text-center">Click or drag file to upload</p>
                    
                    <div className="flex flex-col items-center w-full max-w-sm gap-4">
                      <label className="cursor-pointer bg-white border border-slate-300 px-6 py-2.5 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 hover:border-slate-400 transition-all w-full text-center shadow-sm">
                        Choose File
                        <input type="file" className="hidden" accept=".pdf,.csv,.xlsx,.zip" onChange={(e) => handleFileChange(mod.id, e)} />
                      </label>
                      
                      {file && (
                        <div className="w-full flex flex-col gap-3 animate-in fade-in">
                          <div className="bg-blue-50 border border-blue-100 rounded-lg py-2 px-3 flex items-center justify-between">
                            <span className="text-xs font-semibold text-blue-700 truncate mr-2">{file.name}</span>
                            <span className="text-[10px] text-blue-500 font-medium px-2 py-0.5 bg-blue-100 rounded-full">{(file.size / 1024).toFixed(0)} KB</span>
                          </div>
                          <button 
                            onClick={() => handleUpload(mod.id)}
                            disabled={status === 'uploading'}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl text-sm font-bold transition-all disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 w-full shadow-md shadow-blue-600/20"
                          >
                            {status === 'uploading' && <Loader2 size={18} className="animate-spin" />}
                            {status === 'uploading' ? 'Processing Document...' : 'Generate Reports'}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex flex-col bg-emerald-50/50 border border-emerald-200 rounded-xl p-8 animate-in slide-in-from-bottom-4 duration-500">
                    <div className="flex items-center gap-3 mb-8 text-emerald-700 bg-emerald-100/50 p-4 rounded-lg border border-emerald-200/50">
                      <CheckCircle size={24} />
                      <div>
                        <span className="font-bold block text-sm">Processing Complete</span>
                        <span className="text-xs font-medium opacity-80">Your documents have been analyzed successfully.</span>
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Download Results & Reports</h4>
                      <div className="flex flex-col sm:flex-row gap-3">
                        <button onClick={() => downloadReport(mod.id, 'pdf')} className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-white border-2 border-slate-200 rounded-xl text-sm font-bold hover:border-blue-400 hover:text-blue-700 hover:shadow-md hover:shadow-blue-500/10 transition-all text-slate-700">
                          PDF Report <Download size={18} />
                        </button>
                        <button onClick={() => downloadReport(mod.id, 'excel')} className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-white border-2 border-slate-200 rounded-xl text-sm font-bold hover:border-emerald-400 hover:text-emerald-700 hover:shadow-md hover:shadow-emerald-500/10 transition-all text-slate-700">
                          Excel Data <FileSpreadsheet size={18} />
                        </button>
                        <Link to="/reports" className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-md shadow-slate-900/10 text-center">
                          Reports History <FileText size={18} />
                        </Link>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}



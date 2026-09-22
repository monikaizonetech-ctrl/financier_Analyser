import { useState, useEffect } from 'react';
import { 
  Building2, 
  Sliders, 
  Cpu, 
  Key, 
  ShieldCheck, 
  Save, 
  RotateCcw, 
  CheckCircle2, 
  Trash2, 
  Download, 
  Lock,
  Percent
} from 'lucide-react';

interface SettingsState {
  // General
  orgName: string;
  adminEmail: string;
  financialYear: string;
  currency: string;
  dateFormat: string;

  // Risk Thresholds
  minDscr: number;
  maxFoir: number;
  maxBouncesAllowed: number;
  gstVarianceTolerance: number;
  highRiskScoreCutoff: number;
  lowRiskScoreCutoff: number;

  // OCR & Parsers
  ocrMode: 'accuracy' | 'fast';
  autoEmiDetection: boolean;
  gstrAutoReconcile: boolean;
  multiAccountConsolidation: boolean;
  confidenceThreshold: number;

  // Integrations
  backendUrl: string;
  gstnApiKey: string;
  bureauProvider: 'cibil' | 'experian' | 'crif';
  webhookUrl: string;

  // Security & Notifications
  emailAlertsOnHighRisk: boolean;
  autoPurgeDays: number;
  soundNotifications: boolean;
}

const DEFAULT_SETTINGS: SettingsState = {
  orgName: 'Apex Capital & Credit NBFC',
  adminEmail: 'admin@apexcapital.in',
  financialYear: '2024-2025',
  currency: 'INR (₹)',
  dateFormat: 'DD/MM/YYYY',

  minDscr: 1.25,
  maxFoir: 55,
  maxBouncesAllowed: 2,
  gstVarianceTolerance: 15,
  highRiskScoreCutoff: 550,
  lowRiskScoreCutoff: 720,

  ocrMode: 'accuracy',
  autoEmiDetection: true,
  gstrAutoReconcile: true,
  multiAccountConsolidation: true,
  confidenceThreshold: 85,

  backendUrl: 'http://127.0.0.1:8000',
  gstnApiKey: 'gst_live_sec_994829104882',
  bureauProvider: 'cibil',
  webhookUrl: 'https://api.apexcapital.in/v1/webhooks/risk-engine',

  emailAlertsOnHighRisk: true,
  autoPurgeDays: 90,
  soundNotifications: false
};

export default function Settings() {
  const [activeTab, setActiveTab] = useState<'general' | 'risk' | 'ocr' | 'api' | 'security'>('risk');
  const [settings, setSettings] = useState<SettingsState>(DEFAULT_SETTINGS);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem('financier_system_settings');
      if (saved) {
        setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(saved) });
      }
    } catch (e) {
      console.error('Failed to load settings from storage:', e);
    }
  }, []);

  const handleSave = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      localStorage.setItem('financier_system_settings', JSON.stringify(settings));
      setSaveSuccess(true);
      setStatusMessage('Settings updated successfully');
      setTimeout(() => {
        setSaveSuccess(false);
        setStatusMessage(null);
      }, 3000);
    } catch (err) {
      console.error('Error saving settings:', err);
    }
  };

  const handleReset = () => {
    if (window.confirm('Reset all settings to system defaults?')) {
      setSettings(DEFAULT_SETTINGS);
      localStorage.removeItem('financier_system_settings');
      setStatusMessage('Reset to factory defaults');
      setTimeout(() => setStatusMessage(null), 3000);
    }
  };

  const handleExportData = () => {
    const backupData = {
      settings,
      applications: localStorage.getItem('financier_applications') ? JSON.parse(localStorage.getItem('financier_applications')!) : [],
      history: localStorage.getItem('financier_analyzer_history') ? JSON.parse(localStorage.getItem('financier_analyzer_history')!) : [],
      exportedAt: new Date().toISOString()
    };
    const blob = new Blob([JSON.stringify(backupData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `financier_backup_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleClearCache = () => {
    if (window.confirm('Clear all local application history and cached reports? Active settings will be kept.')) {
      localStorage.removeItem('financier_applications');
      localStorage.removeItem('financier_analyzer_history');
      setStatusMessage('Cache and history wiped clean');
      setTimeout(() => setStatusMessage(null), 3000);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-blue-600 uppercase tracking-widest mb-1">
            <Sliders size={15} /> System Configuration & Control
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Financier Settings</h1>
          <p className="text-sm text-slate-500 mt-1">
            Configure risk assessment parameters, bank statement OCR thresholds, API connections, and organizational preferences.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 text-slate-600 rounded-xl text-sm font-semibold hover:bg-slate-50 hover:border-slate-300 transition-all shadow-sm"
          >
            <RotateCcw size={16} /> Reset Defaults
          </button>
          <button
            onClick={() => handleSave()}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl text-sm font-semibold hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md shadow-blue-500/20"
          >
            {saveSuccess ? <CheckCircle2 size={16} className="text-emerald-300" /> : <Save size={16} />}
            {saveSuccess ? 'Saved!' : 'Save Changes'}
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-sm flex items-center gap-3 animate-fade-in shadow-sm">
          <CheckCircle2 size={18} className="text-emerald-600 flex-shrink-0" />
          <span className="font-medium">{statusMessage}</span>
        </div>
      )}

      {/* Main Grid: Sidebar Tabs + Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Navigation Sidebar */}
        <div className="lg:col-span-3 space-y-1.5">
          <div className="bg-white rounded-2xl border border-slate-200/80 p-2 shadow-sm">
            <button
              onClick={() => setActiveTab('risk')}
              className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-semibold transition-all text-left ${
                activeTab === 'risk'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <Sliders size={18} className={activeTab === 'risk' ? 'text-white' : 'text-blue-600'} />
              <div>
                <p>Risk & Underwriting</p>
                <p className={`text-[11px] font-normal ${activeTab === 'risk' ? 'text-blue-100' : 'text-slate-400'}`}>DSCR, FOIR & scoring cutoffs</p>
              </div>
            </button>

            <button
              onClick={() => setActiveTab('ocr')}
              className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-semibold transition-all text-left ${
                activeTab === 'ocr'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <Cpu size={18} className={activeTab === 'ocr' ? 'text-white' : 'text-purple-600'} />
              <div>
                <p>OCR & Document Rules</p>
                <p className={`text-[11px] font-normal ${activeTab === 'ocr' ? 'text-blue-100' : 'text-slate-400'}`}>Statement parsers & matching</p>
              </div>
            </button>

            <button
              onClick={() => setActiveTab('general')}
              className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-semibold transition-all text-left ${
                activeTab === 'general'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <Building2 size={18} className={activeTab === 'general' ? 'text-white' : 'text-indigo-600'} />
              <div>
                <p>Organization Profile</p>
                <p className={`text-[11px] font-normal ${activeTab === 'general' ? 'text-blue-100' : 'text-slate-400'}`}>Entity info & currency</p>
              </div>
            </button>

            <button
              onClick={() => setActiveTab('api')}
              className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-semibold transition-all text-left ${
                activeTab === 'api'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <Key size={18} className={activeTab === 'api' ? 'text-white' : 'text-amber-600'} />
              <div>
                <p>API & Integrations</p>
                <p className={`text-[11px] font-normal ${activeTab === 'api' ? 'text-blue-100' : 'text-slate-400'}`}>GSTN, Bureau & Webhooks</p>
              </div>
            </button>

            <button
              onClick={() => setActiveTab('security')}
              className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-semibold transition-all text-left ${
                activeTab === 'security'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <ShieldCheck size={18} className={activeTab === 'security' ? 'text-white' : 'text-emerald-600'} />
              <div>
                <p>Data & Maintenance</p>
                <p className={`text-[11px] font-normal ${activeTab === 'security' ? 'text-blue-100' : 'text-slate-400'}`}>Cache, export & storage</p>
              </div>
            </button>
          </div>

          {/* Quick System Badge */}
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] uppercase font-bold tracking-widest bg-blue-500/20 text-blue-300 px-2.5 py-1 rounded-full border border-blue-400/20">
                PRO ENGINE V2.4
              </span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            </div>
            <p className="text-sm font-semibold text-white">Analyzer Engine Active</p>
            <p className="text-xs text-slate-400 mt-1">Backend: FastApi on port 8000</p>
            <div className="mt-4 pt-3 border-t border-slate-700/60 flex items-center justify-between text-xs text-slate-300">
              <span>Financial Rules:</span>
              <span className="font-mono text-blue-400">Strict Model</span>
            </div>
          </div>
        </div>

        {/* Tab Content Panel */}
        <div className="lg:col-span-9">
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden p-6 md:p-8">
            {/* 1. Risk & Underwriting Tab */}
            {activeTab === 'risk' && (
              <div className="space-y-8 animate-fade-in">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Underwriting & Score Weights</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Set policy boundaries for automated scoring, debt repayment ratios, and loan eligibility evaluations.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="p-5 bg-slate-50 border border-slate-200 rounded-xl">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-bold text-slate-800">Minimum DSCR Threshold</label>
                      <span className="px-2.5 py-1 bg-blue-100 text-blue-800 text-xs font-bold rounded-lg">
                        {settings.minDscr}x
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mb-4">Debt Service Coverage Ratio below this flags application as High Risk.</p>
                    <input 
                      type="range" 
                      min="1.0" 
                      max="2.5" 
                      step="0.05"
                      value={settings.minDscr}
                      onChange={e => setSettings({ ...settings, minDscr: parseFloat(e.target.value) })}
                      className="w-full accent-blue-600 cursor-pointer"
                    />
                    <div className="flex justify-between text-[11px] text-slate-400 mt-1">
                      <span>1.0x (Aggressive)</span>
                      <span>1.5x (Recommended)</span>
                      <span>2.5x (Conservative)</span>
                    </div>
                  </div>

                  <div className="p-5 bg-slate-50 border border-slate-200 rounded-xl">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-bold text-slate-800">Max FOIR Ceiling (%)</label>
                      <span className="px-2.5 py-1 bg-indigo-100 text-indigo-800 text-xs font-bold rounded-lg">
                        {settings.maxFoir}%
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mb-4">Fixed Obligation to Income Ratio maximum limit for eligible repayment.</p>
                    <input 
                      type="range" 
                      min="30" 
                      max="75" 
                      step="1"
                      value={settings.maxFoir}
                      onChange={e => setSettings({ ...settings, maxFoir: parseInt(e.target.value) })}
                      className="w-full accent-indigo-600 cursor-pointer"
                    />
                    <div className="flex justify-between text-[11px] text-slate-400 mt-1">
                      <span>30%</span>
                      <span>50% (Standard)</span>
                      <span>75%</span>
                    </div>
                  </div>

                  <div className="p-5 bg-slate-50 border border-slate-200 rounded-xl">
                    <label className="block text-sm font-bold text-slate-800 mb-1">Max Inward Cheque/ECS Returns</label>
                    <p className="text-xs text-slate-500 mb-3">Allowed inward return entries in 6 months of bank statement.</p>
                    <select
                      value={settings.maxBouncesAllowed}
                      onChange={e => setSettings({ ...settings, maxBouncesAllowed: parseInt(e.target.value) })}
                      className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-xl text-sm font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    >
                      <option value={0}>0 Returns (Zero Tolerance)</option>
                      <option value={1}>1 Return allowed</option>
                      <option value={2}>2 Returns allowed (Standard)</option>
                      <option value={3}>3 Returns allowed</option>
                      <option value={5}>5 Returns allowed (High Tolerance)</option>
                    </select>
                  </div>

                  <div className="p-5 bg-slate-50 border border-slate-200 rounded-xl">
                    <label className="block text-sm font-bold text-slate-800 mb-1">GST vs Bank Turnover Variance (%)</label>
                    <p className="text-xs text-slate-500 mb-3">Permissible discrepancy between GSTR-3B sales and banking turnover.</p>
                    <div className="relative">
                      <input
                        type="number"
                        min="5"
                        max="50"
                        value={settings.gstVarianceTolerance}
                        onChange={e => setSettings({ ...settings, gstVarianceTolerance: parseInt(e.target.value) || 0 })}
                        className="w-full pl-4 pr-10 py-2.5 bg-white border border-slate-300 rounded-xl text-sm font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      />
                      <Percent className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                    </div>
                  </div>
                </div>

                <div className="pt-6 border-t border-slate-200">
                  <h3 className="text-base font-bold text-slate-900 mb-4">Risk Categorization Cutoffs</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-red-700 uppercase">High Risk Boundary</span>
                        <span className="text-sm font-bold text-red-900">&lt; {settings.highRiskScoreCutoff}</span>
                      </div>
                      <p className="text-xs text-red-600 mt-1">Applications scoring below this are flagged for rejection or mandatory manual review.</p>
                    </div>

                    <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-emerald-700 uppercase">Low Risk / Prime Boundary</span>
                        <span className="text-sm font-bold text-emerald-900">&gt; {settings.lowRiskScoreCutoff}</span>
                      </div>
                      <p className="text-xs text-emerald-600 mt-1">Applications scoring above this qualify for instant pre-approval terms.</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 2. OCR & Document Rules Tab */}
            {activeTab === 'ocr' && (
              <div className="space-y-8 animate-fade-in">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Document Parsing & OCR Engine</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Fine-tune financial statement extraction, table detection, and cross-reconciliation pipelines.
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="p-5 border border-slate-200 rounded-xl flex items-center justify-between bg-white hover:border-slate-300 transition-colors">
                    <div>
                      <p className="text-sm font-bold text-slate-800">Deep Learning OCR Mode</p>
                      <p className="text-xs text-slate-500 mt-0.5">Applies multi-pass neural vision to scanned bank statements and stamp-marked PDFs.</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSettings({ ...settings, ocrMode: 'fast' })}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                          settings.ocrMode === 'fast' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                      >
                        Fast Standard
                      </button>
                      <button
                        onClick={() => setSettings({ ...settings, ocrMode: 'accuracy' })}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                          settings.ocrMode === 'accuracy' ? 'bg-blue-600 text-white shadow-sm' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                      >
                        High Accuracy
                      </button>
                    </div>
                  </div>

                  <div className="p-5 border border-slate-200 rounded-xl flex items-center justify-between bg-white hover:border-slate-300 transition-colors">
                    <div>
                      <p className="text-sm font-bold text-slate-800">Auto-Detect Recurring EMI & Loan Debits</p>
                      <p className="text-xs text-slate-500 mt-0.5">Machine-learning pattern analyzer automatically categorizes NACH/ECS mandate debits.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={settings.autoEmiDetection} 
                        onChange={e => setSettings({ ...settings, autoEmiDetection: e.target.checked })}
                        className="sr-only peer" 
                      />
                      <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  <div className="p-5 border border-slate-200 rounded-xl flex items-center justify-between bg-white hover:border-slate-300 transition-colors">
                    <div>
                      <p className="text-sm font-bold text-slate-800">GSTR-3B vs GSTR-1 Auto-Reconciliation</p>
                      <p className="text-xs text-slate-500 mt-0.5">Cross-check tax liabilities, input tax credits (ITC), and outward supply consistency.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={settings.gstrAutoReconcile} 
                        onChange={e => setSettings({ ...settings, gstrAutoReconcile: e.target.checked })}
                        className="sr-only peer" 
                      />
                      <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  <div className="p-5 border border-slate-200 rounded-xl flex items-center justify-between bg-white hover:border-slate-300 transition-colors">
                    <div>
                      <p className="text-sm font-bold text-slate-800">Multi-Account Cashflow Consolidation</p>
                      <p className="text-xs text-slate-500 mt-0.5">Eliminates contra inter-account transfers when merging multiple operational accounts.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={settings.multiAccountConsolidation} 
                        onChange={e => setSettings({ ...settings, multiAccountConsolidation: e.target.checked })}
                        className="sr-only peer" 
                      />
                      <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            )}

            {/* 3. Organization Profile Tab */}
            {activeTab === 'general' && (
              <div className="space-y-6 animate-fade-in">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Organization & Localization</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Manage your institution details, fiscal year periods, and currency symbols used across reports.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-bold text-slate-800 mb-1.5">Institution / Company Name</label>
                    <input
                      type="text"
                      value={settings.orgName}
                      onChange={e => setSettings({ ...settings, orgName: e.target.value })}
                      className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-bold text-slate-800 mb-1.5">Admin Email Address</label>
                    <input
                      type="email"
                      value={settings.adminEmail}
                      onChange={e => setSettings({ ...settings, adminEmail: e.target.value })}
                      className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-bold text-slate-800 mb-1.5">Active Financial Year</label>
                    <select
                      value={settings.financialYear}
                      onChange={e => setSettings({ ...settings, financialYear: e.target.value })}
                      className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    >
                      <option value="2024-2025">FY 2024-2025 (Current)</option>
                      <option value="2023-2024">FY 2023-2024</option>
                      <option value="2022-2023">FY 2022-2023</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-bold text-slate-800 mb-1.5">Reporting Currency</label>
                    <select
                      value={settings.currency}
                      onChange={e => setSettings({ ...settings, currency: e.target.value })}
                      className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    >
                      <option value="INR (₹)">INR (₹) - Indian Rupee (Lakhs & Crores)</option>
                      <option value="USD ($)">USD ($) - US Dollar</option>
                      <option value="EUR (€)">EUR (€) - Euro</option>
                      <option value="AED (د.إ)">AED (د.إ) - UAE Dirham</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* 4. API & Integrations Tab */}
            {activeTab === 'api' && (
              <div className="space-y-6 animate-fade-in">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">API & External Integrations</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Connect GSTN public data, Credit Bureaus (CIBIL/Experian), and backend FastAPI endpoints.
                  </p>
                </div>

                <div className="space-y-5">
                  <div>
                    <label className="block text-sm font-bold text-slate-800 mb-1.5">Financier Backend API Endpoint</label>
                    <input
                      type="text"
                      value={settings.backendUrl}
                      onChange={e => setSettings({ ...settings, backendUrl: e.target.value })}
                      className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-mono focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                    <p className="text-xs text-slate-400 mt-1">Default local runtime: http://127.0.0.1:8000</p>
                  </div>

                  <div>
                    <label className="block text-sm font-bold text-slate-800 mb-1.5">GSTN Production / Sandbox API Key</label>
                    <div className="relative">
                      <input
                        type="password"
                        value={settings.gstnApiKey}
                        onChange={e => setSettings({ ...settings, gstnApiKey: e.target.value })}
                        className="w-full pl-4 pr-10 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-mono focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      />
                      <Lock className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-bold text-slate-800 mb-1.5">Credit Bureau Data Provider</label>
                    <select
                      value={settings.bureauProvider}
                      onChange={e => setSettings({ ...settings, bureauProvider: e.target.value as any })}
                      className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    >
                      <option value="cibil">TransUnion CIBIL Commercial & Consumer</option>
                      <option value="experian">Experian Hunter & Credit Engine</option>
                      <option value="crif">CRIF High Mark Commercial Pro</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-bold text-slate-800 mb-1.5">Underwriting Webhook URL</label>
                    <input
                      type="url"
                      value={settings.webhookUrl}
                      onChange={e => setSettings({ ...settings, webhookUrl: e.target.value })}
                      placeholder="https://your-domain.com/webhooks/risk-event"
                      className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-mono focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                    <p className="text-xs text-slate-400 mt-1">Triggered automatically whenever an analysis is verified or exported.</p>
                  </div>
                </div>
              </div>
            )}

            {/* 5. Data & Maintenance Tab */}
            {activeTab === 'security' && (
              <div className="space-y-6 animate-fade-in">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Data Storage & Maintenance</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Backup local workspace databases, export audit archives, and manage local storage cache.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-5 border border-slate-200 rounded-xl bg-slate-50 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center gap-2.5 text-slate-900 font-bold text-sm mb-1">
                        <Download size={18} className="text-blue-600" /> Export System Backup
                      </div>
                      <p className="text-xs text-slate-500">Download complete snapshot of local applications, analysis logs, and settings to a JSON file.</p>
                    </div>
                    <button
                      onClick={handleExportData}
                      className="mt-4 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition-all shadow-sm"
                    >
                      <Download size={14} /> Download Backup (.json)
                    </button>
                  </div>

                  <div className="p-5 border border-red-200 rounded-xl bg-red-50/50 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center gap-2.5 text-red-900 font-bold text-sm mb-1">
                        <Trash2 size={18} className="text-red-600" /> Purge Cache & History
                      </div>
                      <p className="text-xs text-red-600/80">Clear temporary statement analyzer history and uploaded mock datasets from browser storage.</p>
                    </div>
                    <button
                      onClick={handleClearCache}
                      className="mt-4 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold transition-all shadow-sm"
                    >
                      <Trash2 size={14} /> Clear Local Cache
                    </button>
                  </div>
                </div>

                <div className="p-5 border border-slate-200 rounded-xl bg-white space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-bold text-slate-800">Email Alerts on High Risk Discovery</p>
                      <p className="text-xs text-slate-500">Dispatch instant email notification to underwriters when high risk or fraud markers are flagged.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={settings.emailAlertsOnHighRisk} 
                        onChange={e => setSettings({ ...settings, emailAlertsOnHighRisk: e.target.checked })}
                        className="sr-only peer" 
                      />
                      <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

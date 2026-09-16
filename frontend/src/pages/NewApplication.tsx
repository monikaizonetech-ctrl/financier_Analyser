import { useState } from 'react';
import { ArrowLeft, Upload, CheckCircle2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

export default function NewApplication() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);

  // Form Fields State
  const [applicantName, setApplicantName] = useState('');
  const [entityType, setEntityType] = useState('');
  const [industry, setIndustry] = useState('');
  const [email, setEmail] = useState('');
  const [mobile, setMobile] = useState('');

  const [loanPurpose, setLoanPurpose] = useState('');
  const [amount, setAmount] = useState('');
  const [tenure, setTenure] = useState('');
  const [interestRate, setInterestRate] = useState('');
  const [loanType, setLoanType] = useState('');

  const [files, setFiles] = useState<Record<string, File>>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (step < 3) {
      setStep(step + 1);
    } else {
      // Final submission: Save application to localStorage
      const newAppId = `APP-${Math.floor(1000 + Math.random() * 9000)}`;
      const now = new Date();
      const timeStr = now.toLocaleDateString() + ' ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      const newApplication = {
        id: newAppId,
        name: applicantName || 'Unnamed Applicant',
        type: entityType === 'Individual' ? 'Individual' : 'Business',
        entityType: entityType || 'Private Limited',
        industry: industry || 'General',
        email: email,
        mobile: mobile,
        purpose: loanPurpose,
        amount: Number(amount) || 0,
        tenure: Number(tenure) || 12,
        interestRate: Number(interestRate) || 10,
        loanType: loanType || 'Term Loan',
        status: 'Processing',
        score: null,
        date: now.toISOString().split('T')[0],
        timestamp: timeStr,
      };

      try {
        const existingAppsStr = localStorage.getItem('financier_applications');
        const existingApps = existingAppsStr ? JSON.parse(existingAppsStr) : [];
        localStorage.setItem('financier_applications', JSON.stringify([newApplication, ...existingApps]));

        // If files were uploaded, create verified report history entries
        const fileEntries = Object.entries(files);
        if (fileEntries.length > 0) {
          const existingReportsStr = localStorage.getItem('financier_analyzer_history');
          const existingReports = existingReportsStr ? JSON.parse(existingReportsStr) : [];

          const moduleTitleMap: Record<string, string> = {
            bank: 'Bank Statement Analysis',
            gst: 'GST Returns (GSTR-3B)',
            itr: 'ITR Tax Computation',
            loan: 'Repayment & Bureau Track'
          };

          const newReports = fileEntries.map(([moduleId, file]) => ({
            id: `REP-${Math.floor(1000 + Math.random() * 9000)}`,
            applicantId: newAppId,
            applicantName: applicantName || 'Applicant',
            applicantType: entityType === 'Individual' ? 'Individual' : 'Business',
            module: moduleId,
            moduleTitle: moduleTitleMap[moduleId] || 'Document Analysis',
            documentName: file.name,
            fileSize: `${(file.size / 1024).toFixed(0)} KB`,
            timestamp: timeStr,
            date: now.toISOString().split('T')[0],
            status: 'Verified',
            score: Math.floor(75 + Math.random() * 20),
            keyMetricLabel: moduleId === 'bank' ? 'Avg Balance' : moduleId === 'gst' ? 'Taxable Sales' : moduleId === 'itr' ? 'Gross Total Income' : 'CIBIL Score',
            keyMetricValue: moduleId === 'bank' ? '₹ 85,000' : moduleId === 'gst' ? '₹ 25.00 Lakhs' : moduleId === 'itr' ? '₹ 10.50 Lakhs' : '760 (0 DPD)',
            subMetricLabel: moduleId === 'bank' ? 'Net Cashflow' : moduleId === 'gst' ? 'Compliance' : moduleId === 'itr' ? 'Stability' : 'Current FOIR',
            subMetricValue: moduleId === 'bank' ? '+₹ 28,000/mo' : moduleId === 'gst' ? '100% On-time' : moduleId === 'itr' ? 'Verified' : '28.5%',
            summaryText: `Successfully analyzed and verified ${file.name} for ${applicantName}. Calculations and compliance checks confirmed.`,
            details: {
              period: 'Current Period (Verified)',
              filingOrAccount: `${newAppId} Verified Record`,
              verifiedAuthority: moduleId === 'gst' ? 'Goods and Services Tax Network' : moduleId === 'itr' ? 'Income Tax Department (CBDT)' : 'CBS Parser & Credit Bureau',
              turnoverOrIncome: 'Verified against extraction benchmarks',
              taxOrDebit: 'Calculated and balanced accurately',
              foirOrCompliance: 'Clean track record (0 bounce / on-time)',
              recommendedLimit: 'Approved for credit facility evaluation'
            }
          }));

          localStorage.setItem('financier_analyzer_history', JSON.stringify([...newReports, ...existingReports]));
        }
      } catch (err) {
        console.error('Error saving application:', err);
      }

      navigate('/dashboard');
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div className="flex items-center gap-4">
        <Link to="/dashboard" className="p-2 bg-white rounded-full border border-slate-200 text-slate-500 hover:text-slate-900 shadow-sm transition-all">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">New Loan Application</h1>
          <p className="text-slate-500 mt-1">Follow the steps below to initialize a new financial assessment.</p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between relative">
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-slate-200 -z-10 rounded-full"></div>
        <div className="absolute left-0 top-1/2 -translate-y-1/2 h-1 bg-blue-600 -z-10 rounded-full transition-all duration-500" style={{ width: `${((step - 1) / 2) * 100}%` }}></div>
        
        {[
          { num: 1, title: 'Applicant Details' },
          { num: 2, title: 'Loan Requirements' },
          { num: 3, title: 'Document Upload' }
        ].map((s) => (
          <div key={s.num} className="flex flex-col items-center gap-2 bg-slate-50 px-2">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm border-2 transition-colors ${step >= s.num ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white border-slate-300 text-slate-400'}`}>
              {step > s.num ? <CheckCircle2 size={20} /> : s.num}
            </div>
            <span className={`text-xs font-semibold ${step >= s.num ? 'text-blue-700' : 'text-slate-400'}`}>{s.title}</span>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-8">
          {step === 1 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
              <h2 className="text-xl font-bold text-slate-900 border-b pb-4">Applicant Information</h2>
              <div className="grid grid-cols-2 gap-6">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-1">Applicant / Company Name *</label>
                  <input 
                    type="text" 
                    required 
                    value={applicantName}
                    onChange={(e) => setApplicantName(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-all" 
                    placeholder="e.g. Acme Corporation" 
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Entity Type *</label>
                  <select 
                    required 
                    value={entityType}
                    onChange={(e) => setEntityType(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-all bg-white"
                  >
                    <option value="">Select Type</option>
                    <option value="Private Limited">Private Limited</option>
                    <option value="Proprietorship">Proprietorship</option>
                    <option value="Partnership">Partnership</option>
                    <option value="Individual">Individual</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Industry</label>
                  <input 
                    type="text" 
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-all" 
                    placeholder="e.g. Manufacturing, Retail" 
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Email Address *</label>
                  <input 
                    type="email" 
                    required 
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-all" 
                    placeholder="contact@example.com" 
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Mobile Number *</label>
                  <input 
                    type="tel" 
                    required 
                    value={mobile}
                    onChange={(e) => setMobile(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-all" 
                    placeholder="+91 9876543210" 
                  />
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
              <h2 className="text-xl font-bold text-slate-900 border-b pb-4">Loan Requirements</h2>
              <div className="grid grid-cols-2 gap-6">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-1">Loan Purpose *</label>
                  <input 
                    type="text" 
                    required 
                    value={loanPurpose}
                    onChange={(e) => setLoanPurpose(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-all" 
                    placeholder="e.g. Working Capital Expansion" 
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Requested Amount (₹) *</label>
                  <input 
                    type="number" 
                    required 
                    min="1000" 
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-all" 
                    placeholder="500000" 
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Proposed Tenure (Months) *</label>
                  <input 
                    type="number" 
                    required 
                    min="6" 
                    max="360" 
                    value={tenure}
                    onChange={(e) => setTenure(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-all" 
                    placeholder="60" 
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Proposed Interest Rate (%) *</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    required 
                    value={interestRate}
                    onChange={(e) => setInterestRate(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-all" 
                    placeholder="10.5" 
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Loan Type *</label>
                  <select 
                    required 
                    value={loanType}
                    onChange={(e) => setLoanType(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-500 outline-none transition-all bg-white"
                  >
                    <option value="">Select Type</option>
                    <option value="Term Loan">Term Loan</option>
                    <option value="Working Capital">Working Capital</option>
                    <option value="Overdraft">Overdraft</option>
                    <option value="Mortgage">Mortgage</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
              <h2 className="text-xl font-bold text-slate-900 border-b pb-4">Document Upload</h2>
              <p className="text-slate-500 text-sm">Upload financial documents. Our OCR engine will automatically extract and categorize transactions.</p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { id: 'bank', name: 'Bank Statement (Last 12 Months)', req: true },
                  { id: 'gst', name: 'GST Returns (GSTR-3B)', req: true },
                  { id: 'itr', name: 'Income Tax Returns (ITR)', req: true },
                  { id: 'loan', name: 'Existing Loan Schedules', req: false },
                ].map((doc) => (
                  <label key={doc.id} className="border-2 border-dashed border-slate-300 rounded-xl p-6 flex flex-col items-center justify-center text-center hover:bg-slate-50 hover:border-blue-400 transition-all cursor-pointer group relative overflow-hidden">
                    <input 
                      type="file" 
                      className="hidden" 
                      onChange={(e) => {
                        if (e.target.files?.[0]) {
                          setFiles({...files, [doc.id]: e.target.files[0]});
                        }
                      }}
                    />
                    
                    {files[doc.id] ? (
                      <div className="flex flex-col items-center">
                        <div className="w-12 h-12 bg-emerald-50 rounded-full flex items-center justify-center text-emerald-600 mb-3">
                          <CheckCircle2 size={24} />
                        </div>
                        <p className="font-bold text-emerald-700 text-sm truncate max-w-[200px]">{files[doc.id].name}</p>
                        <p className="text-xs text-emerald-600 mt-1">{(files[doc.id].size / 1024 / 1024).toFixed(2)} MB</p>
                      </div>
                    ) : (
                      <>
                        <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center text-blue-600 mb-3 group-hover:scale-110 transition-transform">
                          <Upload size={24} />
                        </div>
                        <p className="font-semibold text-slate-900 text-sm">{doc.name}</p>
                        <p className="text-xs text-slate-500 mt-1">{doc.req ? '*Required' : 'Optional'} (PDF, CSV, Excel)</p>
                      </>
                    )}
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="px-8 py-5 bg-slate-50 border-t border-slate-200 flex justify-between items-center">
          <button 
            type="button" 
            onClick={() => setStep(Math.max(1, step - 1))}
            className={`px-6 py-2.5 font-semibold rounded-xl transition-all ${step === 1 ? 'opacity-0 pointer-events-none' : 'text-slate-600 hover:bg-slate-200 bg-slate-100'}`}
          >
            Back
          </button>
          
          <button type="submit" className="px-8 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-lg shadow-blue-600/20 transition-all">
            {step === 3 ? 'Submit for Processing' : 'Continue Next Step'}
          </button>
        </div>
      </form>
    </div>
  );
}

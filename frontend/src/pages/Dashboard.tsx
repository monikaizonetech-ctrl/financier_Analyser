import { useMemo, useState, useEffect } from 'react';
import { TrendingUp, Clock, CheckCircle2, AlertCircle, Users, FileText } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Link } from 'react-router-dom';

interface ApplicationItem {
  id: string;
  name: string;
  type: string;
  status: string;
  score: number | null;
  date: string;
  amount?: number;
}

export default function Dashboard() {
  const [applications, setApplications] = useState<ApplicationItem[]>([]);

  useEffect(() => {
    // Load real submitted applications from localStorage
    const savedAppsStr = localStorage.getItem('financier_applications');
    const savedReportsStr = localStorage.getItem('financier_analyzer_history');
    
    let combinedApps: ApplicationItem[] = [];
    
    if (savedAppsStr) {
      try {
        const apps = JSON.parse(savedAppsStr);
        if (Array.isArray(apps)) {
          combinedApps = [...apps];
        }
      } catch (e) {
        console.error('Error parsing financier_applications:', e);
      }
    }

    if (savedReportsStr) {
      try {
        const reports = JSON.parse(savedReportsStr);
        if (Array.isArray(reports)) {
          // If no applications exist yet, use report records as assessment items
          if (combinedApps.length === 0) {
            combinedApps = reports.map(r => ({
              id: r.applicantId || r.id,
              name: r.applicantName,
              type: r.applicantType || 'Business',
              status: r.status,
              score: r.score,
              date: r.date || (r.timestamp ? r.timestamp.split(' ')[0] : 'Today')
            }));
          }
        }
      } catch (e) {
        console.error('Error parsing financier_analyzer_history:', e);
      }
    }

    setApplications(combinedApps);
  }, []);

  // Compute KPI stats dynamically
  const kpiStats = useMemo(() => {
    const total = applications.length;
    const pending = applications.filter(a => a.status === 'Processing' || a.status === 'Pending' || a.status === 'Action Needed').length;
    const approved = applications.filter(a => a.status === 'Completed' || a.status === 'Verified' || a.status === 'Approved').length;
    const highRisk = applications.filter(a => a.status === 'High Risk' || (a.score !== null && a.score < 50)).length;

    return { total, pending, approved, highRisk };
  }, [applications]);

  // Aggregate trends by month dynamically
  const trendData = useMemo(() => {
    if (applications.length === 0) return [];

    const monthMap: Record<string, { applications: number; approved: number }> = {};
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    applications.forEach(app => {
      let monthName = 'Recent';
      if (app.date) {
        const d = new Date(app.date);
        if (!isNaN(d.getTime())) {
          monthName = months[d.getMonth()];
        }
      }
      if (!monthMap[monthName]) {
        monthMap[monthName] = { applications: 0, approved: 0 };
      }
      monthMap[monthName].applications += 1;
      if (app.status === 'Completed' || app.status === 'Verified' || app.status === 'Approved') {
        monthMap[monthName].approved += 1;
      }
    });

    return Object.keys(monthMap).map(name => ({
      name,
      applications: monthMap[name].applications,
      approved: monthMap[name].approved
    }));
  }, [applications]);

  return (
    <div className="p-8 space-y-8">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Overview</h1>
          <p className="text-slate-500 mt-1">Here is the latest financial data and application status.</p>
        </div>
        <Link to="/applications/new" className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-600/20 transition-all flex items-center gap-2">
          <span className="text-xl leading-none">+</span> New Application
        </Link>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-blue-50 rounded-full group-hover:scale-150 transition-transform duration-500 ease-out"></div>
          <p className="text-slate-500 text-sm font-medium relative z-10">Total Applications</p>
          <h3 className="text-3xl font-black text-slate-900 mt-2 relative z-10">{kpiStats.total}</h3>
          <div className="flex items-center gap-2 mt-4 relative z-10 text-slate-500 text-sm font-medium">
            <Users size={16} /> <span>{kpiStats.total === 0 ? 'No applications submitted' : `${kpiStats.total} active candidate${kpiStats.total === 1 ? '' : 's'}`}</span>
          </div>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-amber-50 rounded-full group-hover:scale-150 transition-transform duration-500 ease-out"></div>
          <p className="text-slate-500 text-sm font-medium relative z-10">Pending Review</p>
          <h3 className="text-3xl font-black text-slate-900 mt-2 relative z-10">{kpiStats.pending}</h3>
          <div className="flex items-center gap-2 mt-4 relative z-10 text-amber-600 text-sm font-medium">
            <Clock size={16} /> <span>{kpiStats.pending === 0 ? 'All reviews up to date' : 'Requires review'}</span>
          </div>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-emerald-50 rounded-full group-hover:scale-150 transition-transform duration-500 ease-out"></div>
          <p className="text-slate-500 text-sm font-medium relative z-10">Approved Loans</p>
          <h3 className="text-3xl font-black text-slate-900 mt-2 relative z-10">{kpiStats.approved}</h3>
          <div className="flex items-center gap-2 mt-4 relative z-10 text-emerald-600 text-sm font-medium">
            <CheckCircle2 size={16} /> <span>{kpiStats.approved === 0 ? 'No approved loans yet' : 'Passed underwriting'}</span>
          </div>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-red-50 rounded-full group-hover:scale-150 transition-transform duration-500 ease-out"></div>
          <p className="text-slate-500 text-sm font-medium relative z-10">High Risk Alerts</p>
          <h3 className="text-3xl font-black text-slate-900 mt-2 relative z-10">{kpiStats.highRisk}</h3>
          <div className="flex items-center gap-2 mt-4 relative z-10 text-red-600 text-sm font-medium">
            <AlertCircle size={16} /> <span>{kpiStats.highRisk === 0 ? 'Zero risk alerts' : 'Critical FOIR/DSCR flags'}</span>
          </div>
        </div>
      </div>

      {/* Charts & Tables Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Chart */}
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm lg:col-span-2 flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-slate-900">Application Trends</h3>
            {trendData.length > 0 && (
              <span className="text-xs text-slate-500 font-medium">{trendData.length} active period{trendData.length === 1 ? '' : 's'}</span>
            )}
          </div>
          
          <div className="h-72 flex-1 flex items-center justify-center">
            {trendData.length === 0 ? (
              <div className="text-center p-8 text-slate-400">
                <TrendingUp size={36} className="mx-auto mb-2 opacity-40 text-slate-400" />
                <p className="font-semibold text-slate-600 text-sm">No Trend Data Available</p>
                <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
                  Submit new loan applications to generate visual volume and approval trends.
                </p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorUv" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#64748b'}} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: '#64748b'}} dx={-10} allowDecimals={false} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Area type="monotone" dataKey="applications" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorUv)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Recent Table */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden flex flex-col">
          <div className="p-6 border-b border-slate-100 flex justify-between items-center">
            <h3 className="text-lg font-bold text-slate-900">Recent Assessments</h3>
            <Link to="/reports" className="text-sm font-semibold text-blue-600 hover:text-blue-700">View All</Link>
          </div>
          <div className="flex-1 overflow-auto">
            {applications.length === 0 ? (
              <div className="p-8 text-center text-slate-400 flex flex-col items-center justify-center h-64">
                <FileText size={32} className="mb-2 opacity-40 text-slate-400" />
                <p className="font-semibold text-slate-600 text-sm">No Recent Assessments</p>
                <p className="text-xs text-slate-400 mt-1 max-w-[200px]">
                  Applications and document evaluations will appear here.
                </p>
                <Link to="/applications/new" className="mt-4 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-xs transition-all">
                  Create Application
                </Link>
              </div>
            ) : (
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50 text-slate-500 font-medium">
                  <tr>
                    <th className="px-6 py-3">Applicant</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3 text-right">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {applications.slice(0, 5).map((app) => (
                    <tr key={app.id} className="hover:bg-slate-50 transition-colors cursor-pointer">
                      <td className="px-6 py-4">
                        <p className="font-bold text-slate-900">{app.name}</p>
                        <p className="text-xs text-slate-500">{app.id}</p>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold
                          ${app.status === 'Completed' || app.status === 'Verified' ? 'bg-emerald-100 text-emerald-700' : 
                            app.status === 'Processing' || app.status === 'Pending' ? 'bg-blue-100 text-blue-700' : 
                            'bg-red-100 text-red-700'}`}>
                          {app.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        {app.score ? (
                          <span className={`font-bold ${app.score > 70 ? 'text-emerald-600' : 'text-red-600'}`}>
                            {app.score}/100
                          </span>
                        ) : (
                          <span className="text-slate-400 font-medium">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

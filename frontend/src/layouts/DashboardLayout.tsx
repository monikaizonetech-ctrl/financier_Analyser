import { Link, Outlet, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  FileText, 
  Settings, 
  Bell, 
  Search, 
  LogOut
} from 'lucide-react';

export default function DashboardLayout() {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname.startsWith(path) 
      ? "bg-blue-600/20 text-blue-400 border border-blue-500/20" 
      : "text-slate-400 hover:text-white hover:bg-slate-800 border border-transparent";
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col hidden md:flex fixed h-full z-20">
        <div className="p-6">
          <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">FINANCIER</h2>
          <p className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-semibold">Analyzer Pro</p>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 mt-4">
          <Link to="/dashboard" className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all group ${isActive('/dashboard')}`}>
            <LayoutDashboard size={20} className={location.pathname.startsWith('/dashboard') ? "" : "group-hover:text-blue-400 transition-colors"} />
            <span className="font-medium">Dashboard</span>
          </Link>
          <Link to="/applicants" className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all group ${isActive('/applicants')}`}>
            <Users size={20} className={location.pathname.startsWith('/applicants') ? "" : "group-hover:text-blue-400 transition-colors"} />
            <span className="font-medium">Applicants</span>
          </Link>
          <Link to="/reports" className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all group ${isActive('/reports')}`}>
            <FileText size={20} className={location.pathname.startsWith('/reports') ? "" : "group-hover:text-blue-400 transition-colors"} />
            <span className="font-medium">Reports</span>
          </Link>
        </nav>

        <div className="p-4 border-t border-slate-800 space-y-1">
          <Link to="/settings" className={`flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all group ${isActive('/settings')}`}>
            <Settings size={20} className={location.pathname.startsWith('/settings') ? "" : "group-hover:text-blue-400 transition-colors"} />
            <span className="font-medium">Settings</span>
          </Link>
          <button className="flex items-center gap-3 px-4 py-2 text-slate-400 hover:text-red-400 transition-all w-full text-left rounded-xl hover:bg-slate-800/60" onClick={() => { localStorage.clear(); window.location.href = '/login'; }}>
            <LogOut size={20} />
            <span className="font-medium">Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 md:ml-64 flex flex-col min-h-screen">
        {/* Top Header */}
        <header className="h-20 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-10 shadow-sm shadow-slate-100">
          <div className="relative w-96">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
            <input 
              type="text" 
              placeholder="Search applicants, ID, or GST No..." 
              className="w-full pl-10 pr-4 py-2.5 bg-slate-100 border-transparent focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-200 rounded-xl text-sm transition-all outline-none"
            />
          </div>
          <div className="flex items-center gap-6">
            <button className="relative p-2 text-slate-400 hover:text-slate-600 transition-colors">
              <Bell size={20} />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
            </button>
            <div className="flex items-center gap-3 border-l pl-6 border-slate-200">
              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold shadow-md">
                AD
              </div>
              <div>
                <p className="text-sm font-bold text-slate-900">Admin User</p>
                <p className="text-xs text-slate-500">System Administrator</p>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

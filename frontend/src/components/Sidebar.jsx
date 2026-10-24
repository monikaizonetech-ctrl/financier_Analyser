import { useEffect } from "react";
import { NavLink } from "react-router-dom";
import { X, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: "🏠" },
  { to: "/my-reports", label: "My Reports", icon: "📋" },
  { to: "/team-reports", label: "Team Reports", icon: "📄" },
  { to: "/team-management", label: "Team Management", icon: "📊", adminOnly: true },
  { to: "/billing", label: "Billings", icon: "🧾" },
  { to: "/help", label: "Help", icon: "❓" },
];

export default function Sidebar({ isOpen, onClose }) {
  const { user, logout } = useAuth();

  // Prevent background scrolling when mobile sidebar drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const handleLinkClick = () => {
    if (onClose) onClose();
  };

  const handleLogout = () => {
    if (onClose) onClose();
    logout();
  };

  return (
    <>
      {/* Mobile Backdrop overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-40 md:hidden transition-opacity duration-300"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 max-w-[80vw] bg-brand-900 text-white flex flex-col shadow-2xl transition-transform duration-300 ease-in-out md:static md:w-64 md:shrink-0 md:min-h-screen md:translate-x-0 md:shadow-none ${
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0 pointer-events-none md:pointer-events-auto"
        }`}
      >
        {/* Brand Header */}
        <div className="px-6 py-5 flex items-center justify-between border-b border-white/10">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <span className="text-blue-400 font-extrabold text-2xl">i</span>Zone Analyzer
            </h1>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="md:hidden p-1.5 -mr-1.5 rounded-lg text-blue-200 hover:text-white hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-white/20"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems
            .filter((item) => !item.adminOnly || ["Admin", "Manager"].includes(user?.role))
            .map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={handleLinkClick}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                    isActive ? "bg-white/15 text-white font-semibold" : "text-blue-100 hover:bg-white/5 hover:text-white"
                  }`
                }
              >
                <span className="text-base">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}

          <NavLink
            to="/contact-us"
            onClick={handleLinkClick}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                isActive ? "bg-white/15 text-white font-semibold" : "text-blue-100 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            <span className="text-base">📞</span>
            Contact Us
          </NavLink>
        </nav>

        {/* User Card (Visible on mobile within sidebar for easy account overview) */}
        <div className="md:hidden px-3 pt-2 pb-1">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white/5 border border-white/10">
            <div className="w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-semibold shrink-0">
              {user?.name?.[0]?.toUpperCase() || "U"}
            </div>
            <div className="leading-tight min-w-0 flex-1">
              <p className="text-sm font-medium text-white truncate">{user?.name || "User"}</p>
              <p className="text-xs text-blue-200/70 truncate">{user?.email}</p>
            </div>
          </div>
        </div>

        {/* Footer / Logout */}
        <div className="px-3 pb-6 pt-2 border-t border-white/10">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-md text-sm font-medium text-blue-100 hover:bg-white/10 hover:text-white transition-colors"
          >
            <LogOut className="w-4 h-4 text-blue-300" />
            Logout
          </button>
        </div>
      </aside>
    </>
  );
}


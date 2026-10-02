import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: "🏠" },
  { to: "/my-reports", label: "My Reports", icon: "📋" },
  { to: "/team-reports", label: "Team Reports", icon: "📄" },
  { to: "/team-management", label: "Team Management", icon: "📊", adminOnly: true },
  { to: "/billing", label: "Billings", icon: "🧾" },
  { to: "/help", label: "Help", icon: "❓" },
];

export default function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 shrink-0 bg-brand-900 text-white min-h-screen flex flex-col">
      <div className="px-6 py-6">
        <h1 className="text-2xl font-bold tracking-tight">ProAnalyser</h1>
      </div>

      <nav className="flex-1 px-3 space-y-1">
        {navItems
          .filter((item) => !item.adminOnly || ["Admin", "Manager"].includes(user?.role))
          .map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  isActive ? "bg-white/10 text-white" : "text-blue-100 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}

        <a
          href="tel:+916374345280"
          className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-blue-100 hover:bg-white/5 hover:text-white transition-colors"
        >
          <span>📞</span>
          Contact Us
        </a>
      </nav>

      <div className="px-3 pb-6">
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-md text-sm font-medium text-blue-100 hover:bg-white/5 hover:text-white transition-colors"
        >
          <span>↩️</span>
          Logout
        </button>
      </div>
    </aside>
  );
}

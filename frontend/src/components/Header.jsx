import { useState } from "react";
import { Menu, Headphones } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import ContactUsModal from "./ContactUsModal.jsx";

export default function Header({ onToggleSidebar, isSidebarOpen }) {
  const { user } = useAuth();
  const [showContact, setShowContact] = useState(false);

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between gap-2 sm:gap-3 px-3 sm:px-6 md:px-8 py-2.5 sm:py-3.5 bg-white/95 backdrop-blur-sm border-b border-gray-200">
      {/* Left side: Hamburger button & mobile branding */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-label="Toggle navigation menu"
          className="md:hidden p-2 -ml-1 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 transition-colors"
        >
          <Menu className="w-6 h-6" />
        </button>

        <div className="md:hidden flex items-center gap-1.5 min-w-0">
          <span className="font-bold text-base sm:text-lg text-brand-900 tracking-tight truncate">
            iZone Analyzer
          </span>
        </div>
      </div>

      {/* Right side: Support button & user profile badge */}
      <div className="flex items-center gap-2.5 sm:gap-4 ml-auto shrink-0">
        <button
          onClick={() => setShowContact(true)}
          className="btn-secondary text-xs sm:text-sm px-3 py-1.5 sm:px-4 sm:py-2 flex items-center gap-1.5 shadow-xs"
        >
          <Headphones className="w-4 h-4 text-gray-500 hidden sm:inline" />
          <span>Support</span>
        </button>

        <div className="flex items-center gap-2.5 bg-brand-50 border border-brand-100 rounded-lg px-2.5 py-1 sm:px-3 sm:py-1.5 shrink-0">
          <div className="w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-semibold shrink-0 shadow-xs">
            {user?.name?.[0]?.toUpperCase() || "U"}
          </div>
          <div className="leading-tight min-w-0 hidden sm:block">
            <p className="text-sm font-semibold text-gray-800 truncate max-w-[120px] md:max-w-[180px]">
              {user?.name || "User"}
            </p>
            <p className="text-xs text-gray-500 truncate max-w-[120px] md:max-w-[180px]">
              {user?.email}
            </p>
          </div>
        </div>
      </div>

      {showContact && <ContactUsModal onClose={() => setShowContact(false)} />}
    </header>
  );
}


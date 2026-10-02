import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import ContactUsModal from "./ContactUsModal.jsx";

export default function Header() {
  const { user } = useAuth();
  const [showContact, setShowContact] = useState(false);

  return (
    <header className="flex items-center justify-end gap-4 px-8 py-5 bg-white border-b border-gray-200">
      <button onClick={() => setShowContact(true)} className="btn-secondary text-sm">
        Support
      </button>
      <div className="flex items-center gap-3 bg-brand-50 border border-brand-100 rounded-md px-4 py-2">
        <div className="w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-semibold">
          {user?.name?.[0]?.toUpperCase() || "U"}
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold text-gray-800">{user?.name}</p>
          <p className="text-xs text-gray-500">{user?.email}</p>
        </div>
      </div>

      {showContact && <ContactUsModal onClose={() => setShowContact(false)} />}
    </header>
  );
}

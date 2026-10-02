import { createContext, useCallback, useContext, useState } from "react";

const NotificationContext = createContext(null);
let idCounter = 0;

export function NotificationProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const remove = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const notify = useCallback(
    (message, type = "success") => {
      const id = ++idCounter;
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => remove(id), 4000);
    },
    [remove]
  );

  return (
    <NotificationContext.Provider value={{ notify }}>
      {children}
      <div className="fixed top-4 right-4 z-[100] space-y-2 w-80">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`rounded-md shadow-lg px-4 py-3 text-sm font-medium text-white flex items-start justify-between gap-3 animate-[fadeIn_0.2s_ease-out] ${
              t.type === "error"
                ? "bg-red-600"
                : t.type === "warning"
                ? "bg-amber-500"
                : "bg-emerald-600"
            }`}
          >
            <span>{t.message}</span>
            <button onClick={() => remove(t.id)} className="opacity-80 hover:opacity-100">
              ✕
            </button>
          </div>
        ))}
      </div>
    </NotificationContext.Provider>
  );
}

export function useNotification() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error("useNotification must be used within a NotificationProvider");
  return ctx;
}

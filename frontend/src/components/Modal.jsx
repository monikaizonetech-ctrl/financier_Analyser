import { createPortal } from "react-dom";

export default function Modal({ title, children, onClose, footer, maxWidth = "max-w-lg", headerClass = "" }) {
  const modalContent = (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-2 sm:p-4 md:p-6 overflow-y-auto">
      <div
        className="fixed inset-0 transition-opacity"
        aria-hidden="true"
        onClick={onClose}
      />
      <div
        className={`relative w-full ${maxWidth} max-h-[calc(100vh-1.5rem)] sm:max-h-[calc(100vh-3rem)] flex flex-col bg-white rounded-xl shadow-2xl overflow-hidden my-auto z-10`}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <div className={`flex items-center justify-between px-4 sm:px-6 py-3.5 sm:py-4 border-b border-gray-100 shrink-0 ${headerClass}`}>
            <h2 className="text-base sm:text-lg font-bold text-gray-900 truncate pr-2">{title}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-xl leading-none cursor-pointer p-1.5 rounded-md hover:bg-gray-100 transition-colors shrink-0"
              aria-label="Close modal"
            >
              ✕
            </button>
          </div>
        )}
        <div className="px-4 sm:px-6 py-4 sm:py-5 overflow-y-auto flex-1">{children}</div>
        {footer && <div className="px-4 sm:px-6 py-3 sm:py-4 bg-gray-50 flex justify-end gap-2 sm:gap-3 shrink-0 border-t border-gray-100">{footer}</div>}
      </div>
    </div>
  );

  return typeof document !== "undefined" ? createPortal(modalContent, document.body) : modalContent;
}


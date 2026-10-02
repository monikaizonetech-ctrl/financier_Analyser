export default function Modal({ title, children, onClose, footer, maxWidth = "max-w-lg", headerClass = "" }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className={`w-full ${maxWidth} bg-white rounded-lg shadow-xl overflow-hidden`}>
        {title && (
          <div className={`flex items-center justify-between px-6 py-4 border-b border-gray-100 ${headerClass}`}>
            <h2 className="text-lg font-bold text-gray-900">{title}</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">
              ✕
            </button>
          </div>
        )}
        <div className="px-6 py-5">{children}</div>
        {footer && <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3">{footer}</div>}
      </div>
    </div>
  );
}

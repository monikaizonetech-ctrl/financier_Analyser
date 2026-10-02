import Modal from "./Modal.jsx";

export default function ContactUsModal({ onClose }) {
  return (
    <Modal onClose={onClose} maxWidth="max-w-md">
      <div className="text-center">
        <div className="mx-auto w-14 h-14 rounded-full bg-brand-50 flex items-center justify-center text-2xl mb-4">
          📞
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Contact Us</h2>
        <p className="text-sm text-gray-500 mb-6">
          For any queries or assistance, please feel free to reach out to our support team.
        </p>

        <div className="bg-gray-50 rounded-md p-4 text-left space-y-4 mb-6">
          <div className="flex items-center gap-3">
            <span className="text-brand-600">📞</span>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Phone</p>
              <p className="text-sm font-semibold text-gray-800">+91 9876543210</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-brand-600">✉️</span>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Email</p>
              <p className="text-sm font-semibold text-gray-800">contact@izoneanalyzer.in</p>
            </div>
          </div>
        </div>

        <button onClick={onClose} className="btn-primary w-full">
          Close
        </button>
      </div>
    </Modal>
  );
}

import Modal from "./Modal.jsx";

export default function ContactUsModal({ onClose }) {
  return (
    <Modal onClose={onClose} maxWidth="max-w-md">
      <div className="text-center p-2">
        <div className="mx-auto w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center text-2xl mb-4 shadow-sm">
          <span className="text-pink-500 transform -scale-x-100 rotate-12">📞</span>
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Contact Us</h2>
        <p className="text-sm text-gray-500 mb-6 px-4 leading-relaxed">
          We are here to help! Reach out to us directly using the contact details below.
        </p>

        <div className="bg-white border border-gray-100 rounded-xl text-left mb-6 shadow-sm overflow-hidden">
          
          <div className="flex items-center gap-4 p-4 border-b border-gray-100 hover:bg-gray-50 transition-colors">
            <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center shrink-0 text-lg shadow-sm">
              <span className="text-pink-500 transform -scale-x-100 rotate-12">📞</span>
            </div>
            <div>
              <p className="text-xs text-gray-500 font-medium tracking-wide uppercase mb-0.5">Contact Number</p>
              <p className="text-sm font-bold text-gray-900">+91 9940048776</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4 p-4 border-b border-gray-100 hover:bg-gray-50 transition-colors">
            <div className="w-10 h-10 rounded-full bg-pink-50 flex items-center justify-center shrink-0 text-lg shadow-sm">
              ✉️
            </div>
            <div>
              <p className="text-xs text-gray-500 font-medium tracking-wide uppercase mb-0.5">Email Address</p>
              <p className="text-sm font-bold text-gray-900">info@izonetech.in</p>
            </div>
          </div>

          <div className="flex items-center gap-4 p-4 hover:bg-gray-50 transition-colors">
            <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center shrink-0 text-lg shadow-sm">
              ⏰
            </div>
            <div>
              <p className="text-xs text-gray-500 font-medium tracking-wide uppercase mb-0.5">Working Hours</p>
              <p className="text-sm font-bold text-gray-900">Mon - Sat: 9:00 AM - 7:00 PM IST</p>
              <p className="text-sm font-bold text-gray-900 mt-0.5">Sunday: Closed</p>
            </div>
          </div>

        </div>

        <button onClick={onClose} className="w-full bg-[#1e3a8a] hover:bg-blue-900 text-white font-semibold py-3 rounded-lg transition-colors">
          Close
        </button>
      </div>
    </Modal>
  );
}

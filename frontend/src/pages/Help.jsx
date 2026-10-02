import { useState } from "react";
import ContactUsModal from "../components/ContactUsModal.jsx";

const FAQS = [
  {
    q: "How do I create a new report?",
    a: "Go to Dashboard or My Reports and click 'New Report'. Enter a report name, an optional reference ID, and choose the report type (Bank Statement, GST, or ITR Analyzer).",
  },
  {
    q: "What file formats can I upload?",
    a: "You can upload PDF, CSV, and Excel (XLSX) files. For bank statements, CSV/XLSX e-statements give the most detailed analysis.",
  },
  {
    q: "How are credits consumed?",
    a: "Each successful analysis consumes 0.5 credits from your plan. You can track your remaining credits on the Billings page.",
  },
  {
    q: "Can I invite my team?",
    a: "Admins and Managers can add team members from Team Management and assign them a role (Admin, Manager, or Member).",
  },
];

export default function Help() {
  const [showContact, setShowContact] = useState(false);
  const [openIndex, setOpenIndex] = useState(0);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Help & FAQs</h1>

      <div className="card p-0 overflow-hidden mb-6">
        {FAQS.map((faq, idx) => (
          <div key={idx} className="border-b border-gray-100 last:border-none">
            <button
              className="w-full flex justify-between items-center px-5 py-4 text-left font-medium text-gray-800"
              onClick={() => setOpenIndex(openIndex === idx ? -1 : idx)}
            >
              {faq.q}
              <span className="text-gray-400">{openIndex === idx ? "−" : "+"}</span>
            </button>
            {openIndex === idx && <p className="px-5 pb-4 text-sm text-gray-500">{faq.a}</p>}
          </div>
        ))}
      </div>

      <div className="card p-6 flex items-center justify-between">
        <p className="text-sm text-gray-600">Still need help? Our support team is one click away.</p>
        <button className="btn-primary" onClick={() => setShowContact(true)}>
          Contact Support
        </button>
      </div>

      {showContact && <ContactUsModal onClose={() => setShowContact(false)} />}
    </div>
  );
}

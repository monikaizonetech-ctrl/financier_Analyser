import { useEffect, useState } from "react";
import api, { apiErrorMessage } from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";
import { Badge } from "../components/Common.jsx";
import Modal from "../components/Modal.jsx";
import ContactUsModal from "../components/ContactUsModal.jsx";

export default function Billing() {
  const { notify } = useNotification();
  const [billing, setBilling] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [showRaiseRequest, setShowRaiseRequest] = useState(false);
  const [showContact, setShowContact] = useState(false);

  const fetchBilling = async () => {
    setLoading(true);
    try {
      const res = await api.get("/billing");
      setBilling(res.data);
    } catch (err) {
      notify(apiErrorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBilling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAvailPaidTrial = async () => {
    setBusy(true);
    try {
      await api.post("/billing/avail-paid-trial");
      notify("Paid trial activated!");
      fetchBilling();
    } catch (err) {
      notify(apiErrorMessage(err), "error");
    } finally {
      setBusy(false);
    }
  };

  const handleUpgrade = async (plan) => {
    setBusy(true);
    try {
      await api.post("/billing/upgrade", null, { params: { plan } });
      notify(`Upgraded to ${plan} plan!`);
      fetchBilling();
    } catch (err) {
      notify(apiErrorMessage(err), "error");
    } finally {
      setBusy(false);
    }
  };

  if (loading || !billing) {
    return <div className="text-gray-500">Loading billing details...</div>;
  }

  const { subscription, transactions } = billing;
  const creditsLeft = Math.max(subscription.credits_total - subscription.credits_used, 0);
  const creditsPct = subscription.credits_total > 0 ? (creditsLeft / subscription.credits_total) * 100 : 0;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Billings</h1>

      <div className="rounded-lg overflow-hidden bg-gradient-to-r from-brand-900 to-brand-700 text-white px-6 py-6 mb-6 relative">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold">{subscription.plan}</h2>
            <span className="inline-block mt-1 text-xs bg-white/20 rounded-full px-3 py-1">{subscription.plan}</span>
            <p className="text-sm text-blue-100 mt-3">
              Expires on {new Date(subscription.expires_at).toLocaleDateString("en-GB").replaceAll("/", "-")}
            </p>
          </div>
          <Badge label={subscription.status} />
        </div>
      </div>

      <div className="card p-6 mb-6">
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-semibold text-gray-800">Credits</h3>
          <p className="text-sm text-gray-500">
            ( {creditsLeft.toFixed(2)} left of {subscription.credits_total} )
          </p>
        </div>
        <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden mb-5">
          <div className="h-full bg-brand-500" style={{ width: `${creditsPct}%` }} />
        </div>
        <div className="flex gap-3">
          <button className="bg-brand-900 hover:bg-brand-700 text-white font-medium px-4 py-2 rounded-md" disabled={busy} onClick={handleAvailPaidTrial}>
            Avail Paid Trial →
          </button>
          <UpgradeMenu busy={busy} onUpgrade={handleUpgrade} />
        </div>
      </div>

      <div className="card p-6 mb-6">
        <h3 className="font-semibold text-gray-800 mb-4">💳 Transactions</h3>
        {transactions.length === 0 ? (
          <p className="text-gray-400 text-sm">No transactions found.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-gray-500 text-xs uppercase">
              <tr>
                <th className="text-left py-2">Date</th>
                <th className="text-left py-2">Type</th>
                <th className="text-left py-2">Description</th>
                <th className="text-right py-2">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {transactions.map((t) => (
                <tr key={t.id}>
                  <td className="py-2">{new Date(t.created_at).toLocaleDateString("en-IN")}</td>
                  <td className="py-2">{t.type}</td>
                  <td className="py-2">{t.description}</td>
                  <td className="py-2 text-right">₹{Number(t.amount).toLocaleString("en-IN")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card p-6 flex items-center justify-between">
        <p className="text-gray-700 text-sm">Any doubts? Please feel free to contact us or raise a support request.</p>
        <div className="flex gap-3">
          <button className="btn-primary" onClick={() => setShowRaiseRequest(true)}>
            Raise Request
          </button>
          <button className="text-brand-600 font-medium hover:underline" onClick={() => setShowContact(true)}>
            Contact Us
          </button>
        </div>
      </div>

      {showRaiseRequest && <RaiseRequestModal onClose={() => setShowRaiseRequest(false)} />}
      {showContact && <ContactUsModal onClose={() => setShowContact(false)} />}
    </div>
  );
}

function UpgradeMenu({ busy, onUpgrade }) {
  const [open, setOpen] = useState(false);
  const plans = ["Standard", "Pro", "Enterprise"];

  return (
    <div className="relative">
      <button className="bg-brand-900 hover:bg-brand-700 text-white font-medium px-4 py-2 rounded-md" disabled={busy} onClick={() => setOpen((o) => !o)}>
        Upgrade Plan →
      </button>
      {open && (
        <div className="absolute mt-2 bg-white border border-gray-200 rounded-md shadow-lg overflow-hidden z-10 w-40">
          {plans.map((p) => (
            <button
              key={p}
              className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-50"
              onClick={() => {
                setOpen(false);
                onUpgrade(p);
              }}
            >
              {p}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function RaiseRequestModal({ onClose }) {
  const { notify } = useNotification();
  const [form, setForm] = useState({ subject: "", message: "" });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/support/requests", form);
      notify("Your request has been raised. We'll get back to you shortly.");
      onClose();
    } catch (err) {
      notify(apiErrorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Raise a Support Request" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
          <input required className="input-field" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Message</label>
          <textarea required rows={4} className="input-field" value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
        </div>
        <div className="flex justify-end gap-3">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? "Sending..." : "Submit"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { apiErrorMessage } from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";
import Modal from "../components/Modal.jsx";
import ContactUsModal from "../components/ContactUsModal.jsx";

const PLANS = [
  {
    id: "BASIC",
    planKey: "Basic",
    name: "BASIC",
    proCredits: "69.99 PRO-CREDITS",
    originalPrice: "8,749",
    planPrice: "6,999",
    discount: "1,750",
    billingCycle: "Yearly",
    isPopular: false,
    consumption: [
      "0.70 - Bank Statement Analyser via Files",
      "3.05 - GST Analyser via otp (Advanced)",
      "1.10 - GST Analyser via otp (Economy)",
      "0.15 - GST Analyser via Files",
      "0.15 - ITR Analyser via Files",
    ],
    features: [
      "Free Training",
      "24/7 Support",
      "Unlimited users",
      "Unlimited pages per pdf",
      "Unlimited web dashboard access",
      "Standard OCR & PDF extraction",
      "Multi-format Excel & PDF exports",
      "Bank Statement categorization",
      "GST Inward & Outward summary",
    ],
  },
  {
    id: "STANDARD",
    planKey: "Standard",
    name: "STANDARD",
    proCredits: "139.99 PRO-CREDITS",
    originalPrice: "17,499",
    planPrice: "13,999",
    discount: "3,500",
    billingCycle: "Yearly",
    isPopular: true,
    consumption: [
      "0.56 - Bank Statement Analyser via Files",
      "3.00 - GST Analyser via otp (Advanced)",
      "1.05 - GST Analyser via otp (Economy)",
      "0.15 - GST Analyser via Files",
      "0.15 - ITR Analyser via Files",
    ],
    features: [
      "Unlimited pages per pdf",
      "Unlimited web dashboard access",
      "27+ Pdf's per Account",
      "15+ Accounts per Report",
      "Free multi account aggregated report",
      "Free Training",
      "24/7 Support",
      "Unlimited users",
      "Priority automated parsing engine",
      "Automated balance reconciliation",
      "Detailed financial ratios & audit logs",
    ],
  },
  {
    id: "PREMIUM",
    planKey: "Premium",
    name: "PREMIUM",
    proCredits: "279.99 PRO-CREDITS",
    originalPrice: "34,999",
    planPrice: "27,999",
    discount: "7,000",
    billingCycle: "Yearly",
    isPopular: false,
    consumption: [
      "0.46 - Bank Statement Analyser via Files",
      "2.95 - GST Analyser via otp (Advanced)",
      "0.95 - GST Analyser via otp (Economy)",
      "0.14 - GST Analyser via Files",
      "0.14 - ITR Analyser via Files",
    ],
    features: [
      "Free Training",
      "24/7 Support",
      "Unlimited users",
      "Unlimited pages per pdf",
      "Unlimited web dashboard access",
      "50+ Pdf's per Account",
      "30+ Accounts per Report",
      "Fastest SLA processing & high-res OCR",
      "Multi-entity consolidated statements",
      "Dedicated account manager",
      "Custom analytics & API access",
    ],
  },
];

function formatDate(d) {
  if (!d) return "-";
  const date = new Date(d);
  if (isNaN(date.getTime())) return String(d);
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${day}-${month}-${year}`;
}

function formatPlanDisplayName(rawPlan) {
  if (!rawPlan) return "Basic";
  const p = String(rawPlan).toUpperCase();
  if (p === "BASIC") return "Basic";
  if (p === "STANDARD") return "Standard";
  if (p === "PREMIUM") return "Premium";
  if (p === "FREE_TRIAL") return "Free Trial";
  if (p === "PAID_TRIAL") return "Paid Trial";
  return rawPlan;
}

export default function Billing() {
  const navigate = useNavigate();
  const { notify } = useNotification();
  const [billing, setBilling] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showRaiseRequest, setShowRaiseRequest] = useState(false);
  const [showContact, setShowContact] = useState(false);
  const [selectedPlanForBreakdown, setSelectedPlanForBreakdown] = useState(null);
  const [upgrading, setUpgrading] = useState(false);
  const [pendingPlanId, setPendingPlanId] = useState(null);
  const [expandedCards, setExpandedCards] = useState({});

  const toggleExpand = (planId) => {
    setExpandedCards((prev) => ({
      ...prev,
      [planId]: !prev[planId],
    }));
  };

  const fetchBilling = async () => {
    setLoading(true);
    try {
      const res = await api.get("/billing");
      setBilling(res.data);
    } catch (err) {
      notify(apiErrorMessage(err, "Could not load billing details"), "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBilling();
  }, []);

  const handleSelectAndUpgrade = async (plan) => {
    if (!plan) return;
    setPendingPlanId(plan.id);
    setUpgrading(true);

    const displayName = plan.planKey || plan.name;
    const newExpiresAt = new Date();
    newExpiresAt.setFullYear(newExpiresAt.getFullYear() + 1);

    // Immediate optimistic update of Header Plan Card
    setBilling((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        subscription: {
          ...prev.subscription,
          plan: displayName,
          status: "Active",
          started_at: new Date().toISOString(),
          expires_at: newExpiresAt.toISOString(),
        },
      };
    });

    try {
      const res = await api.post("/billing/upgrade", null, {
        params: { plan: displayName },
      });
      setBilling((prev) => ({
        ...prev,
        subscription: res.data,
      }));
      notify(`Successfully upgraded to ${plan.name} plan! Header updated.`);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      notify(apiErrorMessage(err, "Could not upgrade plan"), "error");
      await fetchBilling();
    } finally {
      setUpgrading(false);
      setPendingPlanId(null);
      setSelectedPlanForBreakdown(null);
    }
  };

  const scrollToPlans = () => {
    document.getElementById("available-plans-section")?.scrollIntoView({ behavior: "smooth" });
  };

  if (loading || !billing) {
    return (
      <div className="min-h-screen bg-[#f3f4f6] flex items-center justify-center">
        <div className="flex items-center gap-3 text-gray-500 text-sm font-medium">
          <svg className="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          Loading billing details...
        </div>
      </div>
    );
  }

  const { subscription, transactions } = billing;
  const isExpired =
    subscription.status === "Expired" ||
    new Date(subscription.expires_at) < new Date();
  const currentPlanName = formatPlanDisplayName(subscription.plan);

  return (
    <div className="min-h-screen bg-[#f3f4f6] text-gray-800 flex flex-col">
      {/* Top Bar */}
      <header className="bg-[#2563eb] text-white shadow-md flex items-center justify-between px-6 py-3.5 sticky top-0 z-20">
        <button
          onClick={() => navigate("/dashboard")}
          className="bg-white hover:bg-gray-100 text-[#1e293b] text-xs font-bold px-5 py-2 rounded-lg shadow-sm transition-all"
        >
          Exit
        </button>

        <h1 className="text-base sm:text-lg font-bold text-white text-center flex-1 pr-14">
          Billings
        </h1>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Card 1: Main Plan Card (Header) */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          {/* Dark Navy Header Section with geometric line decoration */}
          <div className="bg-[#1a2b4c] text-white p-6 sm:p-7 relative overflow-hidden">
            {/* Geometric SVG Background Accent */}
            <div className="absolute right-0 top-0 bottom-0 w-1/2 pointer-events-none opacity-20">
              <svg
                className="w-full h-full object-cover"
                viewBox="0 0 400 200"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <polygon
                  points="250,20 320,60 320,140 250,180 180,140 180,60"
                  stroke="#60a5fa"
                  strokeWidth="1.5"
                />
                <polygon
                  points="320,60 390,100 390,180 320,220 250,180 250,100"
                  stroke="#93c5fd"
                  strokeWidth="1.5"
                />
                <polygon
                  points="180,60 250,100 250,180 180,220 110,180 110,100"
                  stroke="#3b82f6"
                  strokeWidth="1.5"
                />
                <line x1="250" y1="20" x2="390" y2="100" stroke="#60a5fa" strokeWidth="1" />
                <line x1="180" y1="60" x2="320" y2="140" stroke="#93c5fd" strokeWidth="1" />
              </svg>
            </div>

            <div className="relative z-10 flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                  <span>{currentPlanName}</span>
                </h2>
                <span className="inline-block mt-2 text-[11px] font-semibold bg-white/10 text-white/90 border border-white/15 rounded-full px-3 py-0.5 backdrop-blur-sm">
                  {currentPlanName.toLowerCase()}
                </span>
                <p
                  className={`text-sm font-semibold mt-3 ${
                    isExpired ? "text-[#f87171]" : "text-emerald-400"
                  }`}
                >
                  {isExpired ? `${currentPlanName} Expired` : `${currentPlanName} Active`}
                </p>
              </div>

              {/* Status Badge */}
              <div>
                <span
                  className={`inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1 rounded-full shadow-sm ${
                    isExpired
                      ? "bg-[#ef4444]/20 text-[#fca5a5] border border-[#ef4444]/40"
                      : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isExpired ? "bg-red-400" : "bg-emerald-400 animate-pulse"
                    }`}
                  />
                  {isExpired ? "Expired" : "Active"}
                </span>
              </div>
            </div>
          </div>

          {/* White Details Section */}
          <div className="p-6 sm:p-7 space-y-2 bg-white">
            <p className="text-xs text-gray-600 font-medium">
              Plan start: {formatDate(subscription.started_at)}
            </p>
            <p className="text-xs text-gray-600 font-medium">
              Plan end: {formatDate(subscription.expires_at)}
            </p>
            <div className="pt-3 flex items-center gap-3">
              <button
                onClick={scrollToPlans}
                className="bg-[#0f172a] hover:bg-[#1e293b] text-white text-xs font-bold px-5 py-2.5 rounded-lg inline-flex items-center gap-1.5 shadow-sm transition-colors"
              >
                Change Plan ↓
              </button>
            </div>
          </div>
        </div>

        {/* Card 2: 3 PLANS SECTION (DIRECTLY IN BILLINGS PAGE) */}
        <div id="available-plans-section" className="space-y-4 pt-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <span>⚡</span> Available Subscription Plans
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Click any plan to immediately switch and activate it in your header.
              </p>
            </div>
            <span className="text-xs font-semibold px-3 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100 self-start sm:self-auto">
              Annual Billing · 18% GST Included
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
            {PLANS.map((plan) => {
              const isExpanded = !!expandedCards[plan.id];
              const visibleFeatures = isExpanded ? plan.features : plan.features.slice(0, 5);
              const isCurrentPlan = currentPlanName.toUpperCase() === plan.id.toUpperCase() && !isExpired;
              const isPending = upgrading && pendingPlanId === plan.id;

              return (
                <div
                  key={plan.id}
                  onClick={() => {
                    if (!isCurrentPlan && !upgrading) handleSelectAndUpgrade(plan);
                  }}
                  className={`bg-white rounded-2xl shadow-sm hover:shadow-lg transition-all flex flex-col justify-between overflow-hidden cursor-pointer ${
                    isCurrentPlan
                      ? "border-2 border-emerald-500 ring-2 ring-emerald-500/20 relative md:-translate-y-1 shadow-md"
                      : plan.isPopular
                      ? "border-2 border-[#22c55e] relative shadow-md"
                      : "border border-gray-200 hover:border-blue-300"
                  }`}
                >
                  {/* Active or Most Popular Banner */}
                  {isCurrentPlan ? (
                    <div className="bg-emerald-600 text-white text-[11px] font-extrabold text-center py-1 tracking-widest uppercase shadow-inner flex items-center justify-center gap-1">
                      <span>✓</span> CURRENT ACTIVE PLAN
                    </div>
                  ) : plan.isPopular ? (
                    <div className="bg-[#22c55e] text-white text-[11px] font-extrabold text-center py-1 tracking-widest uppercase shadow-inner">
                      MOST POPULAR
                    </div>
                  ) : null}

                  <div className="p-6 flex flex-col flex-1">
                    {/* Title */}
                    <div className="flex items-center justify-center gap-2 mb-3">
                      <h3 className="text-base font-extrabold text-gray-900 tracking-wider uppercase">
                        {plan.name}
                      </h3>
                      {isCurrentPlan && (
                        <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-300">
                          Active
                        </span>
                      )}
                    </div>

                    {/* Pro Credits Pill */}
                    <div className="flex justify-center mb-4">
                      <span className="bg-[#eff6ff] text-[#2563eb] border border-blue-100 text-xs font-bold px-4 py-1 rounded-full shadow-2xs">
                        {plan.proCredits}
                      </span>
                    </div>

                    {/* Price Block */}
                    <div className="text-center my-2">
                      <div className="text-xs font-bold text-gray-400 line-through">
                        Rs. {plan.originalPrice} / {plan.billingCycle}
                      </div>
                      <div className="text-xl font-black text-gray-900 mt-0.5 flex items-baseline justify-center gap-1">
                        <span>Now Rs. {plan.planPrice}</span>
                        <span className="text-[11px] font-normal text-gray-500">(inc 18% GST)</span>
                      </div>
                      <div className="text-xs font-bold text-[#16a34a] mt-1">
                        You save Rs. {plan.discount}
                      </div>
                    </div>

                    {/* Credit Consumption Pale Yellow Box */}
                    <div className="bg-[#fffbeb] border border-[#fef3c7] rounded-xl p-3.5 my-4 text-[11px] text-gray-700 space-y-1 shadow-[inset_0_1px_1px_rgba(0,0,0,0.03)]">
                      <p className="font-extrabold text-[#78350f] text-[11px] mb-1.5">
                        Credit Consumption
                      </p>
                      {plan.consumption.map((line, idx) => (
                        <p key={idx} className="leading-tight text-gray-600 font-medium">
                          {line}
                        </p>
                      ))}
                    </div>

                    {/* Features List */}
                    <div className="space-y-2 mt-2 flex-1">
                      {visibleFeatures.map((feat, idx) => (
                        <div key={idx} className="flex items-start gap-2 text-xs text-gray-700">
                          <span className="text-gray-400 font-bold shrink-0">✓</span>
                          <span className="leading-tight">{feat}</span>
                        </div>
                      ))}
                      {plan.features.length > 5 && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleExpand(plan.id);
                          }}
                          className="text-[#2563eb] text-xs font-semibold hover:underline block pt-1.5"
                        >
                          {isExpanded ? "Show Less" : "Show More"}
                        </button>
                      )}
                    </div>

                    {/* Action Button & Breakdown Link */}
                    <div className="pt-6 mt-auto space-y-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectAndUpgrade(plan);
                        }}
                        disabled={upgrading}
                        className={`w-full text-white text-xs font-bold py-3 px-4 rounded-xl shadow-sm hover:shadow transition-all uppercase tracking-wider ${
                          isCurrentPlan
                            ? "bg-emerald-600 hover:bg-emerald-700 ring-2 ring-emerald-300"
                            : "bg-[#2563eb] hover:bg-[#1d4ed8]"
                        }`}
                      >
                        {isPending
                          ? "Activating..."
                          : isCurrentPlan
                          ? `✓ Active Plan (${plan.name})`
                          : `Choose ${plan.name}`}
                      </button>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedPlanForBreakdown(plan);
                        }}
                        className="text-[11px] text-gray-500 hover:text-blue-600 font-medium text-center block w-full hover:underline"
                      >
                        View Pricing Breakdown
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Card 3: Transactions */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-6 sm:p-7">
          <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
            <span>💳</span> Transactions
          </h3>
          {transactions.length === 0 ? (
            <p className="text-xs text-gray-400 mt-4 font-normal">No transactions found.</p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="text-gray-400 uppercase font-semibold text-[11px] border-b border-gray-100">
                  <tr>
                    <th className="text-left py-2.5">Date</th>
                    <th className="text-left py-2.5">Type</th>
                    <th className="text-left py-2.5">Description</th>
                    <th className="text-right py-2.5">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {transactions.map((t) => (
                    <tr key={t.id} className="hover:bg-gray-50/70">
                      <td className="py-3 text-gray-600">{formatDate(t.created_at)}</td>
                      <td className="py-3">
                        <span className="bg-blue-50 text-blue-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-blue-100">
                          {t.type}
                        </span>
                      </td>
                      <td className="py-3 font-medium text-gray-800">{t.description}</td>
                      <td className="py-3 text-right font-bold text-gray-900">
                        Rs. {Number(t.amount).toLocaleString("en-IN")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Card 4: Support Callout */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <p className="text-xs sm:text-sm font-medium text-gray-700">
            Any doubts? Please feel free to contact us or raise a support request.
          </p>
          <div className="flex items-center gap-4 shrink-0">
            <button
              onClick={() => setShowRaiseRequest(true)}
              className="bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-bold px-5 py-2.5 rounded-lg shadow-sm transition-all"
            >
              Raise Request
            </button>
            <button
              onClick={() => setShowContact(true)}
              className="text-[#2563eb] hover:text-[#1d4ed8] text-xs font-bold hover:underline transition-colors"
            >
              Contact Us
            </button>
          </div>
        </div>

        {/* Card 5: Upcoming Plan */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-6 sm:p-7">
          <h4 className="text-xs sm:text-sm font-bold text-gray-800">No upcoming plan</h4>
          <p className="text-xs text-gray-400 mt-1">
            You don't have any plan scheduled for activation.
          </p>
        </div>
      </main>

      {/* Upgrade Plan Confirmation / Breakdown Modal */}
      {selectedPlanForBreakdown && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-md p-6 relative">
            <h2 className="text-lg font-bold text-gray-900">
              {selectedPlanForBreakdown.name} Plan Details
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Annual subscription pricing breakdown.
            </p>

            {/* Price breakdown box */}
            <div className="bg-gray-50/70 border border-gray-100 rounded-xl p-4 mt-4 space-y-2 text-xs">
              <div className="flex justify-between items-center text-gray-500 font-medium">
                <span>Original Price</span>
                <span className="font-semibold text-gray-700">Rs. {selectedPlanForBreakdown.originalPrice}</span>
              </div>
              <div className="flex justify-between items-center text-[#16a34a] font-semibold">
                <span>Plan Discount</span>
                <span>-Rs. {selectedPlanForBreakdown.discount}</span>
              </div>
              <div className="flex justify-between items-center text-gray-700 font-semibold">
                <span>Plan Price</span>
                <span className="font-bold text-gray-900">Rs. {selectedPlanForBreakdown.planPrice}</span>
              </div>
              <div className="border-t border-gray-200 my-2" />
              <div className="flex justify-between items-baseline pt-1">
                <span className="text-sm font-bold text-gray-900">You Pay</span>
                <div className="text-right">
                  <span className="text-xl font-extrabold text-[#2563eb]">
                    Rs. {selectedPlanForBreakdown.planPrice}
                  </span>
                  <span className="text-[10px] text-gray-400 block -mt-1 font-normal">
                    (inc 18% GST)
                  </span>
                </div>
              </div>
            </div>

            {/* Trial Plans notice banner */}
            <div className="bg-[#eff6ff] border border-blue-100 rounded-xl p-3.5 mt-3.5 text-xs text-[#1e40af] leading-relaxed">
              <span className="font-bold italic">Credits Info:</span> Includes {selectedPlanForBreakdown.proCredits}. Unused trial credits carry forward.
            </div>

            <p className="text-[10px] text-gray-400 mt-2.5 italic">
              * Terms &amp; conditions apply to credit adjustments and carry-forwards.
            </p>

            {/* Modal actions */}
            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={() => setSelectedPlanForBreakdown(null)}
                disabled={upgrading}
                className="text-xs font-semibold text-gray-600 hover:text-gray-900 px-4 py-2.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => handleSelectAndUpgrade(selectedPlanForBreakdown)}
                disabled={upgrading}
                className="bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-bold px-6 py-2.5 rounded-xl shadow-sm transition-all disabled:opacity-50"
              >
                {upgrading ? "Activating..." : `Activate ${selectedPlanForBreakdown.name}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Raise Support Request Modal */}
      {showRaiseRequest && (
        <RaiseRequestModal onClose={() => setShowRaiseRequest(false)} />
      )}

      {/* Contact Us Modal */}
      {showContact && (
        <ContactUsModal onClose={() => setShowContact(false)} />
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
      notify(apiErrorMessage(err, "Could not submit request"), "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Raise a Support Request" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">Subject</label>
          <input
            required
            className="input-field text-xs"
            placeholder="e.g. Question about billing or plan upgrade"
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">Message</label>
          <textarea
            required
            rows={4}
            className="input-field text-xs"
            placeholder="Describe your issue or question in detail..."
            value={form.message}
            onChange={(e) => setForm({ ...form, message: e.target.value })}
          />
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <button type="button" className="btn-secondary text-xs" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-bold px-5 py-2 rounded-lg shadow-sm disabled:opacity-50"
          >
            {loading ? "Sending..." : "Submit"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

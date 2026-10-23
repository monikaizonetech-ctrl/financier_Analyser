import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { apiErrorMessage } from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";

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

export default function Pricing() {
  const navigate = useNavigate();
  const { notify } = useNotification();
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [upgrading, setUpgrading] = useState(false);
  const [expandedCards, setExpandedCards] = useState({});

  const toggleExpand = (planId) => {
    setExpandedCards((prev) => ({
      ...prev,
      [planId]: !prev[planId],
    }));
  };

  const handleConfirmUpgrade = async () => {
    if (!selectedPlan) return;
    setUpgrading(true);
    try {
      await api.post("/billing/upgrade", null, {
        params: { plan: selectedPlan.planKey },
      });
      notify(`Successfully upgraded to ${selectedPlan.name} plan!`);
      setSelectedPlan(null);
      navigate("/billing");
    } catch (err) {
      notify(apiErrorMessage(err, "Could not upgrade plan"), "error");
    } finally {
      setUpgrading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f3f4f6] text-gray-800 flex flex-col">
      {/* Top Bar matching screenshot */}
      <header className="bg-[#2563eb] text-white shadow-md flex items-center justify-between px-6 py-3.5 sticky top-0 z-20">
        <button
          onClick={() => navigate("/billing")}
          className="bg-white hover:bg-gray-100 text-[#1e293b] text-xs font-bold px-5 py-2 rounded-lg shadow-sm transition-all"
        >
          Exit
        </button>

        <h1 className="text-base sm:text-lg font-black tracking-widest text-white uppercase text-center flex-1 pr-14">
          PRICING
        </h1>
      </header>

      {/* Main Pricing Cards Grid */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
          {PLANS.map((plan) => {
            const isExpanded = !!expandedCards[plan.id];
            const visibleFeatures = isExpanded ? plan.features : plan.features.slice(0, 5);

            return (
              <div
                key={plan.id}
                className={`bg-white rounded-2xl shadow-sm hover:shadow-md transition-all flex flex-col justify-between overflow-hidden ${
                  plan.isPopular
                    ? "border-2 border-[#22c55e] relative md:-translate-y-1 shadow-md"
                    : "border border-gray-200"
                }`}
              >
                {/* Most Popular Banner */}
                {plan.isPopular && (
                  <div className="bg-[#22c55e] text-white text-[11px] font-extrabold text-center py-1 tracking-widest uppercase shadow-inner">
                    MOST POPULAR
                  </div>
                )}

                <div className="p-6 flex flex-col flex-1">
                  {/* Title */}
                  <h3 className="text-base font-extrabold text-gray-900 text-center tracking-wider uppercase mb-3">
                    {plan.name}
                  </h3>

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
                        onClick={() => toggleExpand(plan.id)}
                        className="text-[#2563eb] text-xs font-semibold hover:underline block pt-1.5"
                      >
                        {isExpanded ? "Show Less" : "Show More"}
                      </button>
                    )}
                  </div>

                  {/* Choose Plan Button */}
                  <div className="pt-6 mt-auto">
                    <button
                      onClick={() => setSelectedPlan(plan)}
                      className="w-full bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-bold py-3 px-4 rounded-xl shadow-sm hover:shadow transition-all uppercase tracking-wider"
                    >
                      Choose {plan.name}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </main>

      {/* Upgrade Plan Confirmation Modal (Screenshot 3) */}
      {selectedPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-md p-6 relative">
            <h2 className="text-lg font-bold text-gray-900">Upgrade Plan</h2>
            <p className="text-xs text-gray-500 mt-0.5">Upgrade will be applied immediately.</p>

            {/* Price breakdown box */}
            <div className="bg-gray-50/70 border border-gray-100 rounded-xl p-4 mt-4 space-y-2 text-xs">
              <div className="flex justify-between items-center text-gray-500 font-medium">
                <span>Original Price</span>
                <span className="font-semibold text-gray-700">Rs. {selectedPlan.originalPrice}</span>
              </div>
              <div className="flex justify-between items-center text-[#16a34a] font-semibold">
                <span>Plan Discount</span>
                <span>-Rs. {selectedPlan.discount}</span>
              </div>
              <div className="flex justify-between items-center text-gray-700 font-semibold">
                <span>Plan Price</span>
                <span className="font-bold text-gray-900">Rs. {selectedPlan.planPrice}</span>
              </div>
              <div className="border-t border-gray-200 my-2" />
              <div className="flex justify-between items-baseline pt-1">
                <span className="text-sm font-bold text-gray-900">You Pay</span>
                <div className="text-right">
                  <span className="text-xl font-extrabold text-[#2563eb]">
                    Rs. {selectedPlan.planPrice}
                  </span>
                  <span className="text-[10px] text-gray-400 block -mt-1 font-normal">
                    (inc 18% GST)
                  </span>
                </div>
              </div>
            </div>

            {/* Trial Plans notice banner */}
            <div className="bg-[#eff6ff] border border-blue-100 rounded-xl p-3.5 mt-3.5 text-xs text-[#1e40af] leading-relaxed">
              <span className="font-bold italic">Trial Plans:</span> Unused credits will be added
              additionally to your new plan.
            </div>

            <p className="text-[10px] text-gray-400 mt-2.5 italic">
              * Terms &amp; conditions apply to credit adjustments and carry-forwards.
            </p>

            {/* Modal actions */}
            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={() => setSelectedPlan(null)}
                disabled={upgrading}
                className="text-xs font-semibold text-gray-600 hover:text-gray-900 px-4 py-2.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmUpgrade}
                disabled={upgrading}
                className="bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-bold px-6 py-2.5 rounded-xl shadow-sm transition-all disabled:opacity-50"
              >
                {upgrading ? "Upgrading..." : "Continue"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

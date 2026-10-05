import { useState } from "react";
import api from "../api/axios.js";

export default function ContactUs() {
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    phone: "",
    subject: "",
    message: "",
  });

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await api.post("/support/contact-us", formData);
      if (response.data.error) {
        setError(response.data.message);
      } else {
        setSuccess(true);
        setFormData({
          fullName: "",
          email: "",
          phone: "",
          subject: "",
          message: "",
        });
      }
    } catch (err) {
      setError("Failed to send message. Please try again later.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      <div className="max-w-[1200px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* ======================================================== */}
        {/* LEFT COLUMN (Form + Office Locations) */}
        {/* ======================================================== */}
        <div className="lg:col-span-7 space-y-8">
          
          {/* Send Us a Message Form */}
          <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Send Us a Message</h2>

            {success && (
              <div className="mb-6 p-4 bg-green-50 text-green-700 rounded-lg font-medium">
                Your message has been sent successfully to our support team!
              </div>
            )}
            {error && (
              <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg font-medium">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                  <input
                    type="text"
                    name="fullName"
                    required
                    value={formData.fullName}
                    onChange={handleChange}
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
                    placeholder="Enter Your Name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
                  <input
                    type="email"
                    name="email"
                    required
                    value={formData.email}
                    onChange={handleChange}
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
                    placeholder="Enter Your Email"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
                  <input
                    type="tel"
                    name="phone"
                    required
                    minLength="10"
                    maxLength="10"
                    pattern="\d{10}"
                    title="Please enter exactly 10 digits"
                    value={formData.phone}
                    onChange={(e) => {
                      const value = e.target.value.replace(/\D/g, ''); // Remove non-digits
                      if (value.length <= 10) {
                        setFormData((prev) => ({ ...prev, phone: value }));
                      }
                    }}
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
                    placeholder="Enter 10-digit number"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
                  <input
                    type="text"
                    name="subject"
                    required
                    value={formData.subject}
                    onChange={handleChange}
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
                    placeholder="Project Inquiry"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Message</label>
                <textarea
                  name="message"
                  required
                  rows="5"
                  value={formData.message}
                  onChange={handleChange}
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors resize-none"
                  placeholder="Tell us about your project..."
                ></textarea>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#1e40af] hover:bg-[#1e3a8a] text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {loading ? "Sending..." : "Send Message ✈️"}
              </button>
            </form>
          </div>

          {/* Head Office Card */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-start gap-4">
            <div className="w-12 h-12 shrink-0 bg-blue-50 text-[#1e40af] rounded-xl flex items-center justify-center text-2xl">
              🏢
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">Head Office</h3>
              <p className="text-sm text-gray-600 leading-relaxed font-medium">
                No: 10/20, second Floor,<br />
                Annai Residency,<br />
                Amma Mandapam Road, Mambalasalai,<br />
                Srirangam, Tiruchirappalli-620006.
              </p>
            </div>
          </div>

          {/* Branch Office Card */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-start gap-4">
            <div className="w-12 h-12 shrink-0 bg-blue-50 text-[#1e40af] rounded-xl flex items-center justify-center text-2xl">
              🌐
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">Branch Office</h3>
              <ul className="text-sm text-gray-600 font-medium space-y-1.5 list-none">
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-[#1e40af] rounded-full inline-block"></span>Chennai</li>
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-[#1e40af] rounded-full inline-block"></span>Coimbatore</li>
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-[#1e40af] rounded-full inline-block"></span>Nagarkovil</li>
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-[#1e40af] rounded-full inline-block"></span>Thiruvananthapuram</li>
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-[#1e40af] rounded-full inline-block"></span>Salem</li>
              </ul>
            </div>
          </div>

        </div>

        {/* ======================================================== */}
        {/* RIGHT COLUMN (4 Cards + Socials + Map) */}
        {/* ======================================================== */}
        <div className="lg:col-span-5 flex flex-col gap-8">
          
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Contact Information</h2>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
                <div className="w-10 h-10 bg-red-50 text-red-500 rounded-xl flex items-center justify-center mb-4 text-xl">
                  📍
                </div>
                <h3 className="font-bold text-gray-900 mb-1">Visit Us</h3>
                <p className="text-xs text-gray-500 font-medium leading-relaxed">
                  5th Cross Thillainagar, Tiruchirappalli-620018.
                </p>
              </div>

              <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
                <div className="w-10 h-10 bg-purple-50 text-purple-500 rounded-xl flex items-center justify-center mb-4 text-xl">
                  ✉️
                </div>
                <h3 className="font-bold text-gray-900 mb-1">Email Us</h3>
                <a href="mailto:info@izonetech.in" className="text-xs text-gray-500 hover:text-[#1e40af] font-medium leading-relaxed transition-colors">
                  info@izonetech.in
                </a>
              </div>

              <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
                <div className="w-10 h-10 bg-green-50 text-green-500 rounded-xl flex items-center justify-center mb-4 text-xl">
                  📞
                </div>
                <h3 className="font-bold text-gray-900 mb-1">Call Us</h3>
                <p className="text-xs text-gray-500 font-medium leading-relaxed">
                  +91-9940048776
                </p>
              </div>

              <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
                <div className="w-10 h-10 bg-orange-50 text-orange-500 rounded-xl flex items-center justify-center mb-4 text-xl">
                  ⏰
                </div>
                <h3 className="font-bold text-gray-900 mb-1">Business Hours</h3>
                <p className="text-xs text-gray-500 font-medium leading-relaxed">
                  Mon-Sat: 10:00 AM - 6:30 PM<br />
                  Sun: Closed
                </p>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-base font-bold text-gray-900 mb-4">Follow Us</h3>
            <div className="flex gap-3">
              <a href="https://linkedin.com/company/izonetechnologies/posts/?feedView=all" target="_blank" rel="noopener noreferrer" className="w-10 h-10 rounded-xl bg-white border border-gray-200 text-[#1e40af] flex items-center justify-center hover:bg-blue-50 transition-colors shadow-sm">
                <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path><rect x="2" y="9" width="4" height="12"></rect><circle cx="4" cy="4" r="2"></circle></svg>
              </a>
              <a href="https://x.com/izonegroups" target="_blank" rel="noopener noreferrer" className="w-10 h-10 rounded-xl bg-white border border-gray-200 text-gray-800 flex items-center justify-center hover:bg-gray-50 transition-colors shadow-sm">
                <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"><path d="M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z"></path></svg>
              </a>
              <a href="https://facebook.com/izonetechnology" target="_blank" rel="noopener noreferrer" className="w-10 h-10 rounded-xl bg-white border border-gray-200 text-[#1e40af] flex items-center justify-center hover:bg-blue-50 transition-colors shadow-sm">
                <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"></path></svg>
              </a>
              <a href="https://instagram.com/izone_technologies/" target="_blank" rel="noopener noreferrer" className="w-10 h-10 rounded-xl bg-white border border-gray-200 text-pink-600 flex items-center justify-center hover:bg-pink-50 transition-colors shadow-sm">
                <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line></svg>
              </a>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-2 flex-1 min-h-[300px]">
            <div className="w-full h-full rounded-xl overflow-hidden relative">
              <iframe 
                src="https://maps.google.com/maps?q=iZone%20Technologies%20Tiruchirappalli&t=&z=15&ie=UTF8&iwloc=&output=embed" 
                width="100%" 
                height="100%" 
                style={{border: 0}} 
                allowFullScreen="" 
                loading="lazy" 
                referrerPolicy="no-referrer-when-downgrade"
                title="Google Maps"
              ></iframe>
              <a
                href="https://www.google.com/maps/place/iZone+Technologies/@10.8237987,78.6864102,855m"
                target="_blank"
                rel="noreferrer"
                className="absolute top-3 left-3 bg-white/95 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-gray-200 shadow-sm text-xs font-semibold text-gray-800 hover:text-[#1e40af] transition-colors flex items-center gap-1.5"
              >
                <span>📍</span> Open in Maps ↗
              </a>
            </div>
          </div>



        </div>
      </div>

    </div>
  );
}

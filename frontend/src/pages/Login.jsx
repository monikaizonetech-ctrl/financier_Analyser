import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useNotification } from "../context/NotificationContext.jsx";
import { apiErrorMessage } from "../api/axios.js";

export default function Login() {
  const { login } = useAuth();
  const { notify } = useNotification();
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(form.email, form.password);
      notify("Logged in successfully");
      navigate("/dashboard");
    } catch (err) {
      setError(apiErrorMessage(err, "Invalid email or password"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-900 to-brand-600 px-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-2xl p-8">
        <h1 className="text-3xl font-bold text-brand-900 text-center mb-1">ProAnalyser</h1>
        <p className="text-sm text-gray-500 text-center mb-8">Sign in to your workspace</p>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              required
              className="input-field"
              placeholder="you@company.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              required
              className="input-field"
              placeholder="••••••••"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
            {loading ? "Signing in..." : "Login"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          Don&apos;t have an account?{" "}
          <Link to="/register" className="text-brand-600 font-medium hover:underline">
            Create one
          </Link>
        </p>

        <div className="mt-6 pt-6 border-t border-gray-100 text-xs text-gray-400">
          <p className="font-semibold mb-1">Demo credentials (after seeding the DB):</p>
          <p>Admin: monika@proanalyser.in / Admin@123</p>
          <p>Manager: ravi.manager@proanalyser.in / Manager@123</p>
          <p>Member: ananya.member@proanalyser.in / Member@123</p>
        </div>
      </div>
    </div>
  );
}

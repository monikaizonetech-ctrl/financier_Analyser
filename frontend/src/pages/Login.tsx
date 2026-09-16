import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { User, Mail, Phone, Lock, ArrowRight, ShieldCheck, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import api from '../api/client';

export default function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  
  // Form fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');

  // UI state
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const response = await api.post(
        '/api/auth/login',
        new URLSearchParams({ username: email, password: password }),
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      );
      localStorage.setItem('token', response.data.access_token);
      navigate('/dashboard');
    } catch (error: any) {
      console.error('Login failed:', error);
      const detail = error.response?.data?.detail || 'Invalid email or password. Please try again.';
      setErrorMsg(detail);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    if (!name.trim()) {
      setErrorMsg('Please enter your full name');
      return;
    }
    if (!email.trim()) {
      setErrorMsg('Please enter a valid email address');
      return;
    }
    if (!phoneNumber.trim()) {
      setErrorMsg('Please enter your phone number');
      return;
    }
    if (password.length < 6) {
      setErrorMsg('Password must be at least 6 characters');
      return;
    }

    setLoading(true);

    try {
      const response = await api.post('/api/auth/register', {
        name: name.trim(),
        email: email.trim(),
        phone_number: phoneNumber.trim(),
        password: password
      });

      localStorage.setItem('token', response.data.access_token);
      setSuccessMsg('Account created successfully! Redirecting...');
      setTimeout(() => {
        navigate('/dashboard');
      }, 1000);
    } catch (error: any) {
      console.error('Registration failed:', error);
      const detail = error.response?.data?.detail || 'Registration failed. This email may already be in use.';
      setErrorMsg(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4 py-12 selection:bg-blue-500/30 relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl pointer-events-none"></div>

      <div className="max-w-md w-full relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <ShieldCheck size={22} className="text-white" />
            </div>
            <span className="text-2xl font-black text-white tracking-tight">
              FINANCIER <span className="text-blue-400">ANALYZER</span>
            </span>
          </Link>
          <p className="text-slate-400 text-sm">
            {mode === 'login' ? 'Sign in to access assessments & financial tools' : 'Register a new financier / underwriter account'}
          </p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 p-8">
          {/* Mode Switch Tabs */}
          <div className="flex bg-slate-100 p-1.5 rounded-2xl mb-6">
            <button
              type="button"
              onClick={() => {
                setMode('login');
                setErrorMsg(null);
                setSuccessMsg(null);
              }}
              className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all ${
                mode === 'login'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('register');
                setErrorMsg(null);
                setSuccessMsg(null);
              }}
              className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all ${
                mode === 'register'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Feedback Messages */}
          {errorMsg && (
            <div className="mb-5 p-3.5 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs font-medium flex items-center gap-2 animate-in fade-in">
              <AlertCircle size={16} className="shrink-0 text-red-500" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-5 p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-xs font-medium flex items-center gap-2 animate-in fade-in">
              <CheckCircle2 size={16} className="shrink-0 text-emerald-500" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Forms */}
          {mode === 'login' ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 rounded-xl text-sm transition-all outline-none"
                    placeholder="admin@financier.com"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 rounded-xl text-sm transition-all outline-none"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-lg shadow-blue-600/20 transition-all text-sm flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {loading ? <Loader2 size={18} className="animate-spin" /> : null}
                <span>{loading ? 'Signing In...' : 'Sign In'}</span>
                {!loading && <ArrowRight size={18} />}
              </button>

              <div className="pt-2 text-center">
                <p className="text-xs text-slate-500">
                  Don't have an account?{' '}
                  <button
                    type="button"
                    onClick={() => {
                      setMode('register');
                      setErrorMsg(null);
                    }}
                    className="font-bold text-blue-600 hover:underline"
                  >
                    Create User Account
                  </button>
                </p>
              </div>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-4">
              {/* User Name */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  User Name / Full Name *
                </label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 rounded-xl text-sm transition-all outline-none"
                    placeholder="e.g. Rahul Sharma"
                  />
                </div>
              </div>

              {/* Email Address */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Email Address *
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 rounded-xl text-sm transition-all outline-none"
                    placeholder="rahul@financier.com"
                  />
                </div>
              </div>

              {/* Phone Number */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Phone Number *
                </label>
                <div className="relative">
                  <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input
                    type="tel"
                    required
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 rounded-xl text-sm transition-all outline-none"
                    placeholder="+91 98765 43210"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Password *
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 rounded-xl text-sm transition-all outline-none"
                    placeholder="At least 6 characters"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-lg shadow-blue-600/20 transition-all text-sm flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {loading ? <Loader2 size={18} className="animate-spin" /> : null}
                <span>{loading ? 'Creating User Account...' : 'Register User Account'}</span>
                {!loading && <ArrowRight size={18} />}
              </button>

              <div className="pt-2 text-center">
                <p className="text-xs text-slate-500">
                  Already registered?{' '}
                  <button
                    type="button"
                    onClick={() => {
                      setMode('login');
                      setErrorMsg(null);
                    }}
                    className="font-bold text-blue-600 hover:underline"
                  >
                    Sign In
                  </button>
                </p>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

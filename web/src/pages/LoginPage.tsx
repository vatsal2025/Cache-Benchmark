import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../lib/store";
import { login, register } from "../lib/api";
import { ShieldCheck } from "lucide-react";
import { jwtDecode } from "jwt-decode";

function decodeOrgId(token: string): string {
  try {
    const d = jwtDecode<{ org_id: string }>(token);
    return d.org_id || "";
  } catch {
    return "";
  }
}

export default function LoginPage() {
  const navigate = useNavigate();
  const loginStore = useAuthStore((s) => s.login);
  const [tab, setTab] = useState<"login" | "register">("login");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [registered, setRegistered] = useState<{ client_id: string; client_secret: string } | null>(null);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await login(clientId, clientSecret);
      const token = res.data.access_token;
      const orgId = decodeOrgId(token);
      loginStore(token, orgId);
      navigate("/overview");
    } catch {
      setError("Invalid credentials. Please check your client ID and secret.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await register(name, email);
      setRegistered(res.data);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-700 to-brand-500 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="flex items-center gap-3 mb-8">
          <ShieldCheck className="text-brand-500" size={32} />
          <div>
            <h1 className="text-xl font-bold text-gray-900">CAPTCHA Benchmark</h1>
            <p className="text-sm text-gray-500">Robustness Evaluation Platform</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 bg-gray-100 p-1 rounded-lg">
          {(["login", "register"] as const).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setError(""); setRegistered(null); }}
              className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
                tab === t ? "bg-white shadow-sm text-gray-900" : "text-gray-500"
              }`}
            >
              {t === "login" ? "Sign In" : "Register"}
            </button>
          ))}
        </div>

        {tab === "login" && (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Client ID</label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={clientId} onChange={(e) => setClientId(e.target.value)} required
                placeholder="Your client_id"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Client Secret</label>
              <input
                type="password"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={clientSecret} onChange={(e) => setClientSecret(e.target.value)} required
                placeholder="Your client_secret"
              />
            </div>
            {error && <p className="text-red-600 text-sm">{error}</p>}
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>
        )}

        {tab === "register" && !registered && (
          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Organisation Name</label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={name} onChange={(e) => setName(e.target.value)} required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={email} onChange={(e) => setEmail(e.target.value)} required
              />
            </div>
            {error && <p className="text-red-600 text-sm">{error}</p>}
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? "Registering…" : "Create Account"}
            </button>
          </form>
        )}

        {registered && (
          <div className="space-y-3">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-green-800 font-medium mb-2">Account created! Save these credentials:</p>
              <div className="space-y-2 font-mono text-xs">
                <p><span className="text-gray-500">client_id:</span> <span className="select-all">{registered.client_id}</span></p>
                <p><span className="text-gray-500">client_secret:</span> <span className="select-all">{registered.client_secret}</span></p>
              </div>
            </div>
            <button onClick={() => { setTab("login"); setRegistered(null); setClientId(registered.client_id); setClientSecret(registered.client_secret); }} className="btn-primary w-full">
              Sign In Now
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

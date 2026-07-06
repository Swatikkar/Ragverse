import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar/Sidebar";
import ChatWindow from "@/components/Chat/ChatWindow";
import SourcePanel from "@/components/SourcePanel/SourcePanel";
import { getToken, loginUser, registerUser } from "@/lib/api";

function AuthCard({ mode, onAuthed, onSwitch }) {
  const isLogin = mode === "login";
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit() {
    setError("");
    setLoading(true);
    try {
      const data = isLogin
        ? await loginUser(form.email, form.password)
        : await registerUser(form.full_name, form.email, form.password);
      localStorage.setItem("ragverse_token", data.access_token);
      localStorage.setItem("ragverse_user", JSON.stringify(data.user));
      onAuthed();
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") handleSubmit();
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm bg-gray-900 rounded-2xl p-8 shadow-xl border border-gray-800">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Rag<span className="text-violet-500">verse</span>
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">Multimodal Research Assistant</p>
        </div>

        <p className="text-gray-300 font-medium mb-5">
          {isLogin ? "Sign in to your account" : "Create your account"}
        </p>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            {error}
          </div>
        )}

        <div className="flex flex-col gap-4" onKeyDown={handleKeyDown}>
          {!isLogin && (
            <div className="flex flex-col gap-1.5">
              <label className="text-gray-400 text-sm">Full name</label>
              <input
                name="full_name"
                value={form.full_name}
                onChange={handleChange}
                className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-violet-500 transition-colors"
              />
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            <label className="text-gray-400 text-sm">Email</label>
            <input
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-violet-500 transition-colors"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-gray-400 text-sm">Password</label>
            <div className="relative">
              <input
                name="password"
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={handleChange}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-4 pr-11 py-2.5 text-white text-sm focus:outline-none focus:border-violet-500 transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-gray-500 hover:text-violet-300 transition-colors"
                aria-label={showPassword ? "Hide password" : "Show password"}
                title={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M3 3l18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    <path d="M10.6 10.7a2 2 0 0 0 2.7 2.7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    <path d="M9.9 5.2A9.8 9.8 0 0 1 12 5c5 0 8.5 4.4 9.6 6a12.6 12.6 0 0 1-3.1 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M6.6 6.8A13.8 13.8 0 0 0 2.4 11c1.1 1.6 4.6 6 9.6 6 1.3 0 2.4-.3 3.5-.8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M2.4 12s3.6-6 9.6-6 9.6 6 9.6 6-3.6 6-9.6 6-9.6-6-9.6-6Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" stroke="currentColor" strokeWidth="2" />
                  </svg>
                )}
              </button>
            </div>
          </div>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="mt-1 w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-2.5 rounded-lg text-sm transition-colors"
          >
            {loading ? "Please wait..." : isLogin ? "Sign in" : "Create account"}
          </button>
        </div>

        <button
          onClick={onSwitch}
          className="mt-6 w-full text-center text-violet-400 hover:text-violet-300 text-sm transition-colors"
        >
          {isLogin ? "Create an account" : "Sign in instead"}
        </button>
      </div>
    </div>
  );
}

function Home() {
  const [activeSources, setActiveSources] = useState([]);

  return (
    <div className="flex h-screen overflow-hidden">
      <div className="w-72 border-r border-gray-800 shrink-0">
        <Sidebar />
      </div>
      <div className="flex-1 flex flex-col overflow-hidden">
        <ChatWindow onSourcesUpdate={setActiveSources} />
      </div>
      <div className="w-80 border-l border-gray-800 shrink-0">
        <SourcePanel sources={activeSources} />
      </div>
    </div>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(false);
  const [mode, setMode] = useState("login");

  useEffect(() => {
    setAuthed(Boolean(getToken()));
  }, []);

  if (!authed) {
    return (
      <AuthCard
        mode={mode}
        onAuthed={() => setAuthed(true)}
        onSwitch={() => setMode((prev) => (prev === "login" ? "register" : "login"))}
      />
    );
  }

  return <Home />;
}

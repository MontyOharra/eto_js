import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { setAuthenticated } from "../helpers/auth";

export const Route = createFileRoute("/login")({
  component: Login,
});

function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [autoAuthenticating, setAutoAuthenticating] = useState(false);

  // Auto-authenticate in development mode
  useEffect(() => {
    const isDevelopment = process.env.NODE_ENV === 'development' || import.meta.env.DEV;
    if (isDevelopment) {
      setAutoAuthenticating(true);

      const autoAuth = async () => {
        setSubmitting(true);
        try {
          // Simulate the same authentication flow
          await new Promise((r) => setTimeout(r, 100)); // Shorter delay for dev
          setAuthenticated(true);
          navigate({ to: "/dashboard", replace: true });
        } catch (error) {
          console.error('Auto-authentication failed:', error);
          setSubmitting(false);
          setAutoAuthenticating(false);
        }
      };

      // Small delay to show the login page briefly, then auto-authenticate
      const timer = setTimeout(autoAuth, 500);
      return () => clearTimeout(timer);
    }
  }, [navigate]);

  async function fakeAuthenticate(_u: string, _p: string): Promise<boolean> {
    // Simulate latency
    await new Promise((r) => setTimeout(r, 250));
    return true;
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      const ok = await fakeAuthenticate(username, password);
      if (ok) {
        setAuthenticated(true);
        navigate({ to: "/dashboard", replace: true });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-100 flex flex-col items-center p-8">
      <div className="mt-12 text-3xl font-semibold text-gray-900">
        Welcome to HTC ETO
      </div>

      {autoAuthenticating && (
        <div className="mt-6 flex items-center space-x-2 text-blue-600">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span className="text-sm">Auto-authenticating for development...</span>
        </div>
      )}

      <form
        onSubmit={onSubmit}
        className="mt-8 w-full max-w-sm bg-white rounded-lg shadow p-6 space-y-4 border"
      >
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Username
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="mt-1 w-full rounded border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            autoComplete="username"
            disabled={autoAuthenticating}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            autoComplete="current-password"
            disabled={autoAuthenticating}
            required
          />
        </div>
        <button
          type="submit"
          disabled={submitting || autoAuthenticating}
          className="w-full py-2 rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-400"
        >
          {autoAuthenticating ? "Auto-authenticating..." : submitting ? "Signing in…" : "Login"}
        </button>
      </form>
    </main>
  );
}

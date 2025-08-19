import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

export const Route = createFileRoute("/login")({
  component: Login,
});

function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

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
            required
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2 rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-400"
        >
          {submitting ? "Signing in…" : "Login"}
        </button>
      </form>
    </main>
  );
}

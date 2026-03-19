"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

export default function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSignIn() {
    setError(null);
    setLoading(true);
    const supabase = createClient();

    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (authError) {
      setError(authError.message);
      setLoading(false);
      return;
    }

    router.push("/dashboard/overview");
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="w-full max-w-sm space-y-6">
        {/* Logo */}
        <div className="text-center">
          <span className="font-mono text-2xl font-semibold text-primary">
            Ennesso
          </span>
          <p className="font-sans text-sm text-muted mt-1">
            Energy Governance Platform
          </p>
        </div>

        {/* Card */}
        <div className="bg-surface border border-border rounded-lg p-6 space-y-4">
          <div className="space-y-1.5">
            <label className="font-sans text-xs text-muted">
              Email address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void handleSignIn()}
              placeholder="you@institution.ec"
              className={cn(
                "w-full bg-background border border-border rounded px-3 py-2.5",
                "font-sans text-sm text-foreground placeholder:text-muted",
                "focus:outline-none focus:border-primary"
              )}
            />
          </div>

          <div className="space-y-1.5">
            <label className="font-sans text-xs text-muted">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void handleSignIn()}
              className={cn(
                "w-full bg-background border border-border rounded px-3 py-2.5",
                "font-sans text-sm text-foreground",
                "focus:outline-none focus:border-primary"
              )}
            />
          </div>

          {error && (
            <p className="font-mono text-xs text-red-400">{error}</p>
          )}

          <button
            onClick={() => void handleSignIn()}
            disabled={loading || !email || !password}
            className={cn(
              "w-full py-2.5 rounded bg-primary text-background",
              "font-sans text-sm font-medium",
              "hover:opacity-90 transition-opacity",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "flex items-center justify-center gap-2"
            )}
          >
            {loading && <Loader2 size={14} className="animate-spin" />}
            Sign in
          </button>
        </div>

        <p className="font-sans text-xs text-muted text-center">
          Access is restricted to authorized personnel.
        </p>
      </div>
    </div>
  );
}

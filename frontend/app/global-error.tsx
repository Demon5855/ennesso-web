"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import Link from "next/link";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[GlobalError]", error);
  }, [error]);

  return (
    <html lang="es" className="dark">
      <body className="bg-[#0F1117] text-[#E8EAF0]">
        <div className="min-h-screen flex flex-col items-center justify-center gap-6 p-8">
          <div className="flex items-center gap-3 text-[#E05C2A]">
            <AlertTriangle size={24} />
            <span className="font-mono text-lg font-semibold">
              Application Error
            </span>
          </div>

          <p className="font-sans text-sm text-[#6B7280] text-center max-w-md">
            {error.message || "An unexpected error occurred."}
            {error.digest && (
              <span className="block font-mono text-xs mt-2">
                Digest: {error.digest}
              </span>
            )}
          </p>

          <div className="flex items-center gap-3">
            <button
              onClick={reset}
              className="flex items-center gap-2 px-4 py-2 bg-[#00C2A8] text-[#0F1117] rounded font-sans text-sm font-medium hover:opacity-90 transition-opacity"
            >
              <RefreshCw size={14} />
              Try again
            </button>
            <Link
              href="/"
              className="flex items-center gap-2 px-4 py-2 border border-[#2A2D3A] text-[#6B7280] rounded font-sans text-sm hover:text-[#E8EAF0] hover:border-[#6B7280] transition-colors"
            >
              <Home size={14} />
              Home
            </Link>
          </div>
        </div>
      </body>
    </html>
  );
}

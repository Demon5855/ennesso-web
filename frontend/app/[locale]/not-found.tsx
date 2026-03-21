import Link from "next/link";
import { Home } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-6 p-8">
      <div className="text-center space-y-2">
        <p className="font-mono text-6xl font-semibold text-primary">404</p>
        <p className="font-mono text-sm text-muted">Page not found</p>
      </div>

      <p className="font-sans text-sm text-muted text-center max-w-sm">
        The page you are looking for does not exist or has been moved.
      </p>

      <Link
        href="/dashboard/overview"
        className="flex items-center gap-2 px-5 py-2.5 bg-primary text-background rounded font-sans text-sm font-medium hover:opacity-90 transition-opacity"
      >
        <Home size={14} />
        Back to dashboard
      </Link>

      <span className="font-mono text-xs text-muted">ennesso · Ecuador SNI</span>
    </div>
  );
}

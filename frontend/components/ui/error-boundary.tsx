"use client";

import { Component, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error) {
    console.error("[ErrorBoundary]", error);
  }

  override render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex flex-col items-center justify-center h-full min-h-64 gap-4 p-8">
          <div className="flex items-center gap-3 text-[#F5A623]">
            <AlertTriangle size={20} />
            <span className="font-mono text-sm">Something went wrong</span>
          </div>
          <p className="font-sans text-xs text-muted text-center max-w-sm">
            {this.state.error?.message ?? "An unexpected error occurred loading this section."}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="flex items-center gap-2 px-4 py-2 border border-border rounded font-sans text-xs text-muted hover:text-foreground hover:border-primary/50 transition-colors"
          >
            <RefreshCw size={12} />
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

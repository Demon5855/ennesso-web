import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Core backgrounds
        background: "#0F1117",
        surface: "#1A1D27",
        // Brand
        primary: {
          DEFAULT: "#00C2A8",
          foreground: "#0F1117",
        },
        // Energy source semantics
        thermal: {
          DEFAULT: "#E05C2A",
          muted: "#E05C2A33",
        },
        hydraulic: {
          DEFAULT: "#2A7BE4",
          muted: "#2A7BE433",
        },
        // Text
        foreground: "#E8EAF0",
        muted: {
          DEFAULT: "#6B7280",
          foreground: "#6B7280",
        },
        // Border
        border: "#2A2D3A",
        // shadcn/ui compatibility
        card: {
          DEFAULT: "#1A1D27",
          foreground: "#E8EAF0",
        },
        popover: {
          DEFAULT: "#1A1D27",
          foreground: "#E8EAF0",
        },
        secondary: {
          DEFAULT: "#2A2D3A",
          foreground: "#E8EAF0",
        },
        destructive: {
          DEFAULT: "#EF4444",
          foreground: "#E8EAF0",
        },
        accent: {
          DEFAULT: "#2A2D3A",
          foreground: "#E8EAF0",
        },
        input: "#2A2D3A",
        ring: "#00C2A8",
      },
      fontFamily: {
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
        sans: ["IBM Plex Sans", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        lg: "0.5rem",
        md: "0.375rem",
        sm: "0.25rem",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 4px 0 #00C2A866" },
          "50%": { boxShadow: "0 0 12px 2px #00C2A8AA" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;

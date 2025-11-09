import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: {
        "2xl": "1280px",
      },
    },
    extend: {
      colors: {
        background: "hsl(222, 24%, 6%)",
        surface: "hsl(222, 24%, 10%)",
        border: "hsl(222, 14%, 22%)",
        primary: {
          DEFAULT: "#2563EB",
          foreground: "#FFFFFF",
        },
        positive: {
          DEFAULT: "#10B981",
          foreground: "#062e24",
        },
        warning: {
          DEFAULT: "#F59E0B",
          foreground: "#291b05",
        },
        danger: {
          DEFAULT: "#EF4444",
          foreground: "#2b0e0e",
        },
        text: {
          DEFAULT: "#E5E7EB",
          subtle: "#9CA3AF",
          strong: "#F9FAFB",
        },
      },
      borderRadius: {
        lg: "12px",
        md: "10px",
        sm: "8px",
      },
      boxShadow: {
        card: "0 6px 20px rgba(0,0,0,.25)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;

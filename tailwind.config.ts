import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#6D28D9",
          light: "#8B5CF6"
        },
        canvas: "#F8FAFC",
        success: "#22C55E",
        danger: "#EF4444",
        warning: "#F59E0B"
      },
      boxShadow: {
        soft: "0 18px 45px rgba(15, 23, 42, 0.08)",
        panel: "0 1px 0 rgba(15, 23, 42, 0.04), 0 14px 35px rgba(15, 23, 42, 0.06)"
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;

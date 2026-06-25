import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Navy editorial accent (replaces the old blue "primary")
        primary: {
          50: "#F0F3F8",
          100: "#DCE3EE",
          200: "#B9C7DD",
          300: "#8FA3C2",
          400: "#5E7CA0",
          500: "#3D5980",
          600: "#2A4166",
          700: "#1B2A4A",
          800: "#131F38",
          900: "#0B1525",
        },
        cream: {
          50: "#FFFDF9",
          100: "#FAF7F0",
          200: "#F2EDE0",
          300: "#E8E0CC",
        },
        ink: {
          DEFAULT: "#1A1A1A",
          muted: "#5A5650",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;

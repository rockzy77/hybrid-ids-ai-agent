/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        void: "#0A0E12",
        panel: "#12181F",
        "panel-raised": "#1A222B",
        hairline: "#232D38",
        "text-primary": "#DCE4EC",
        "text-secondary": "#8A99A8",
        signal: {
          benign: "#4ADE80",
          reasoning: "#38BDF8",
          truepositive: "#F14668",
          falsepositive: "#FACC15",
          neutral: "#64748B",
        },
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      keyframes: {
        scan: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        "slide-in": {
          "0%": { transform: "translateY(-8px)", opacity: 0 },
          "100%": { transform: "translateY(0)", opacity: 1 },
        },
        "fade-out": {
          "0%": { opacity: 1 },
          "80%": { opacity: 1 },
          "100%": { opacity: 0 },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.35 },
        },
      },
      animation: {
        scan: "scan 1.4s linear infinite",
        "slide-in": "slide-in 0.25s ease-out",
        "fade-out": "fade-out 4s ease-in forwards",
        "pulse-dot": "pulse-dot 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

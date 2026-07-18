/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        char: {
          950: "#100F0D",
          900: "#17150F",
          surface: "#1B1815",
          border: "#2C2822",
        },
        ink: {
          DEFAULT: "#EDE9E2",
          muted: "#8C867A",
          faint: "#5C574C",
        },
        ember: {
          DEFAULT: "#E8542C",
          bright: "#FF7A47",
          dim: "#7A2E18",
        },
        risk: {
          low: "#5B8C5B",
          moderate: "#C9A227",
          high: "#D97B29",
          veryhigh: "#C24A1F",
          extreme: "#A61C1C",
        },
      },
      fontFamily: {
        display: ["'Big Shoulders Display'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      backgroundImage: {
        contour: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Cg fill='none' stroke='%232C2822' stroke-width='1'%3E%3Ccircle cx='100' cy='100' r='30'/%3E%3Ccircle cx='100' cy='100' r='60'/%3E%3Ccircle cx='100' cy='100' r='90'/%3E%3Ccircle cx='100' cy='100' r='120'/%3E%3C/g%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
};

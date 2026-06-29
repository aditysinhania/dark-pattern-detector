/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Brand colors consistent with the dark pattern theme
        brand: {
          50:  "#f0f4ff",
          100: "#e0e9ff",
          500: "#4f6ef7",
          600: "#3d5ce8",
          700: "#2d4ad4",
          900: "#1a2f8f",
        },
        risk: {
          low:      "#22c55e",
          medium:   "#f59e0b",
          high:     "#ef4444",
          critical: "#7c3aed",
        },
      },
    },
  },
  plugins: [],
}
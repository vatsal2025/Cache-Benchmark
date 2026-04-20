/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { 50: "#eff6ff", 500: "#1a56db", 600: "#1e40af", 700: "#1e3a8a" },
      },
    },
  },
  plugins: [],
};

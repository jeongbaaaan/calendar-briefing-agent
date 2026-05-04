/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f2937",
        calm: "#6b7280",
        line: "#e7edf3",
        cream: "#fbfaf7",
        mint: "#62c7a7",
        coral: "#ff806d",
      },
      boxShadow: {
        soft: "0 18px 45px rgba(31, 41, 55, 0.08)",
      },
    },
  },
  plugins: [],
};

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#4F8EF7",
        secondary: "#6FCF97",
        accent: "#9B8AFB",
      },
    },
  },
  plugins: [],
};

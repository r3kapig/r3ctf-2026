export default {
  content: ["./index.html", "./src/**/*.{js,css}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"]
      },
      boxShadow: {
        stage: "0 24px 64px rgba(50, 69, 132, .18)"
      }
    }
  },
  plugins: []
};

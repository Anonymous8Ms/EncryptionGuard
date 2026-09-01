/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cream: '#E3E2DE',
        cobalt: '#1351AA',
        jet: '#141414',
        deep: '#444343',
        muted: '#7A7A7A',
        border: '#C7C7C7',
      },
      fontFamily: {
        sans: ['"General Sans"', '"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace'],
      },
      borderRadius: {
        none: '0px',
      },
      letterSpacing: {
        tight: '-0.04em',
        tighter: '-0.03em',
        widest: '0.2em',
      },
      lineHeight: {
        compressed: '0.85',
        tight: '0.9',
      },
    },
  },
  plugins: [],
};

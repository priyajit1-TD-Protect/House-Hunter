import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        td: {
          premiumGreen: "#002B1A",
          digitalGreen:  "#008A00",
          gold:          "#CFBD91",
          grey:          "#EFEDEE",
          greenGrey:     "#708573",
          darkGrey:      "#515B52",
          nearBlack:     "#1C1C1C",
          insightBg:     "#F0F7F0",
          lightGreen:    "#C8E6C9",
          lightRed:      "#FFEBEE",
        },
      },
      fontFamily: {
        display: ["Arial Black", "Arial", "sans-serif"],
        body:    ["Arial", "Calibri", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};

export default config;
